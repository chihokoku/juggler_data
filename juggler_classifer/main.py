# %%
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom
from sklearn.linear_model import LogisticRegression

# インタラクティブウィンドウでは __file__ が無い場合があるので、作業フォルダを使う
BASE_DIR = Path(__file__).parent if "__file__" in globals() else Path.cwd()
CSV_DIR = BASE_DIR / "train_csv"
LAYOUT_CSV = BASE_DIR / "layout_data" / "layout.csv"

# 機種ごとの設定1〜6のBB・RB確率の分母（"1/273.1" → 273.1）
# 要確認：記憶をもとに入力した値。メーカー公表値と照合してから使うこと
SETTING_TABLE = {
    "ネオアイムジャグラーEX": {
        "BB": [273.1, 269.7, 269.7, 259.0, 259.0, 255.0],
        "RB": [439.8, 399.6, 331.0, 315.1, 255.0, 255.0],
    },
    "ゴーゴージャグラー３": {
        "BB": [259.0, 258.0, 257.0, 254.0, 247.3, 234.9],
        "RB": [354.2, 332.7, 306.2, 268.6, 247.3, 234.9],
    },
    "マイジャグラーV": {
        "BB": [273.1, 270.8, 266.4, 254.0, 240.9, 229.1],
        "RB": [409.6, 385.5, 336.1, 290.0, 268.6, 229.1],
    },
    "ジャグラーガールズSS": {
        "BB": [273.1, 270.8, 260.1, 250.1, 243.6, 226.0],
        "RB": [381.0, 350.5, 316.6, 281.3, 270.8, 252.1],
    },
    "ファンキージャグラー２ＫＴ": {
        "BB": [266.4, 259.0, 256.0, 249.2, 240.9, 219.9],
        "RB": [439.8, 407.1, 366.1, 322.8, 299.3, 262.1],
    },
    "ハッピージャグラーＶＩＩＩ": {
        "BB": [273.1, 270.8, 263.2, 254.0, 239.2, 226.0],
        "RB": [397.2, 362.1, 332.7, 300.6, 273.1, 256.0],
    },
    "ミスタージャグラー": {
        "BB": [268.6, 267.5, 260.1, 249.2, 240.9, 237.4],
        "RB": [374.5, 354.2, 331.0, 291.3, 257.0, 237.4],
    },
}
SETTINGS = [1, 2, 3, 4, 5, 6]

##########################################
# step0：csvsデータをDataFrame内に格納して扱いやすいようにする
##########################################
def load_csv(csv_dir: Path = CSV_DIR) -> pd.DataFrame:
    """csv_dir 内の全CSVを読み込み、1つの DataFrame にまとめる。"""
    frames = [
        pd.read_csv(path, encoding="utf-8-sig", thousands=",")  # "8,047" → 8047
        for path in sorted(csv_dir.glob("*.csv"))
    ]
    df = pd.concat(frames, ignore_index=True)

    # "1/237" → 237.0（確率の分母）。"-" などデータなしは NaN にする
    for col in ["BB確率", "RB確率", "合成確率"]:
        df[col] = pd.to_numeric(df[col].str.split("/").str[1], errors="coerce")

    # "100%" → 100.0。"-" は NaN にする
    df["出率"] = pd.to_numeric(df["出率"].str.rstrip("%"), errors="coerce")

    # 10月分だけ "10/17" 形式なので年を補ってから日付型にする
    no_year = df["日付"].str.count("/") == 1
    df.loc[no_year, "日付"] = "2026/" + df.loc[no_year, "日付"]
    df["日付"] = pd.to_datetime(df["日付"], format="%Y/%m/%d")

    return df


def load_layout(path: Path = LAYOUT_CSV) -> pd.DataFrame:
    """座席表を読み込み、説明変数に使う列だけ返す。

    角台は「メイン通路側の角」か「反対側の角」と同じ情報、末尾は台番号から作れるので使わない。
    """
    layout = pd.read_csv(path, encoding="utf-8-sig")
    return layout[["台番号", "島", "列", "端からの距離", "メイン通路側の角", "反対側の角", "ゾロ目"]]


##########################################
# step1~3：二項分布により設定を確率的に判別、事前分布の設定、ベイズ推定で高設定ぽさを数値化
##########################################
def estimate_setting(df: pd.DataFrame, prior: np.ndarray | None = None) -> pd.DataFrame:
    """1行（1台・1日）ごとに、設定1〜6である確率をベイズの定理で求める。

    回転数を試行回数として、BB回数・RB回数がそれぞれ二項分布に従うとみなし、
    2つの確率をかけ算したものを尤度とする。
    戻り値は列 "設定1"〜"設定6" と "高設定"（設定5・6の合計）を df に足したもの。
    """
    if prior is None:
        prior = np.full(len(SETTINGS), 1 / len(SETTINGS))  # 事前分布：全設定 1/6

    # 行ごとの設定1〜6の当選確率。形は (行数, 6)
    bb_p = 1 / np.array([SETTING_TABLE[name]["BB"] for name in df["機種名"]])
    rb_p = 1 / np.array([SETTING_TABLE[name]["RB"] for name in df["機種名"]])

    n = df["回転数"].to_numpy()[:, None]
    bb = df["BB回数"].to_numpy()[:, None]
    rb = df["RB回数"].to_numpy()[:, None]

    # 確率をそのままかけると小さすぎて 0 になるので、対数にして足し算する
    log_post = binom.logpmf(bb, n, bb_p) + binom.logpmf(rb, n, rb_p) + np.log(prior)

    # 合計が1になるように割り直す（ベイズの定理の分母）
    post = np.exp(log_post - log_post.max(axis=1, keepdims=True))
    post /= post.sum(axis=1, keepdims=True)

    result = df.copy()
    for i, s in enumerate(SETTINGS):
        result[f"設定{s}"] = post[:, i]
    result["高設定"] = result["設定5"] + result["設定6"]
    return result

##########################################
# step4：ロジスティック回帰に読み込ませるためのデータ処理
#        7日間の高設定確率データを平均したものを1ブロックとしてブロックを算出
##########################################
def make_features(result: pd.DataFrame, layout: pd.DataFrame) -> pd.DataFrame:
    """estimate_setting の結果と座席表から、ロジスティック回帰の説明変数を作る。

    当日の回転数・BB回数・RB回数は予想する時点では分からないので使わない。
    """
    df = result.sort_values(["台番号", "日付"])

    # 台番号で座席表をつなぐ。merge すると index が振り直されるので元に戻す
    seat = df[["台番号"]].merge(layout, on="台番号", how="left", validate="many_to_one")
    seat.index = df.index

    # 前回（データのある前日）の高設定っぽさ。最初の日は事前分布の値（設定5・6で 2/6）で埋める
    prev = df.groupby("台番号")["高設定"].shift(1)
    prev_mean7 = prev.groupby(df["台番号"]).transform(lambda s: s.rolling(7, min_periods=1).mean())

    X = pd.DataFrame(index=df.index)
    X["前日の高設定"] = prev.fillna(2 / 6)
    X["過去7日の高設定平均"] = prev_mean7.fillna(2 / 6)
    X["末尾一致"] = (df["台番号"] % 10 == df["日付"].dt.day % 10).astype(int)  # 7のつく日に末尾7 など

    # 座席。端からの距離0は角台と同じなので、1〜2台目だけ列にする（3台目以降が基準）
    X["メイン通路側の角"] = seat["メイン通路側の角"]
    X["反対側の角"] = seat["反対側の角"]
    X["端から1〜2台目"] = seat["端からの距離"].between(1, 2).astype(int)
    X["ゾロ目"] = seat["ゾロ目"]

    # カテゴリはダミー変数（0/1 の列）にする
    categories = pd.DataFrame({
        "曜日": df["日付"].dt.dayofweek.map(dict(enumerate("月火水木金土日"))),
        "日付末尾": (df["日付"].dt.day % 10).astype(str),
        "台番号末尾": (df["台番号"] % 10).astype(str),
        "機種名": df["機種名"],
        "島": seat["島"],
        "列": seat["列"],
    })
    X = pd.concat([X, pd.get_dummies(categories, dtype=int)], axis=1)
    return X.sort_index()


##########################################
# step5：step4で求めたブロックをロジスティック回帰に入力
##########################################
def fit_logistic(result: pd.DataFrame, layout: pd.DataFrame) -> tuple[LogisticRegression, pd.DataFrame]:
    """「高設定」の確率を重みにして、ロジスティック回帰を学習する。

    1行を「ラベル1・重み p」と「ラベル0・重み 1-p」の2行に分けて学習させる。
    戻り値は学習済みモデルと、学習に使った説明変数。
    """
    X = make_features(result, layout)
    p = result.loc[X.index, "高設定"].to_numpy()

    X2 = pd.concat([X, X])
    y = np.r_[np.ones(len(X)), np.zeros(len(X))]
    w = np.r_[p, 1 - p]

    model = LogisticRegression(max_iter=1000)
    model.fit(X2, y, sample_weight=w)
    return model, X


# %%
##### step0を実行する関数 #####
if __name__ == "__main__":
    df = load_csv()
    print(df.head())
    print(df[["回転数", "BB確率", "RB確率"]].head())

# %%
##### step1~3を実行する関数 #####
if __name__ == "__main__":
    result = estimate_setting(df)
    prob_cols = [f"設定{s}" for s in SETTINGS] + ["高設定"]
    result[prob_cols] = result[prob_cols].round(3)
    cols = ["日付", "台番号", "機種名", "回転数", "BB回数", "RB回数"]
    print(result[cols + prob_cols].head())
    result.round(3).to_clipboard()

# %%
##### step4~5を実行する関数 #####
if __name__ == "__main__":
    # 上のセルは表示用に丸めているので、丸める前の値で学習する
    layout = load_layout()
    model, X = fit_logistic(estimate_setting(df), layout)

    # 条件ごとの重み（係数）。プラスほど高設定が入りやすい条件
    coef = pd.Series(model.coef_[0], index=X.columns).sort_values(ascending=False)
    print(coef.round(3).to_string())
    coef.round(3).to_clipboard()


# %%
