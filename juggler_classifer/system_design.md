# インストール済みライブラリ（.venv / Python 3.14.4）

## インストールしたもの

| ライブラリ   | バージョン |
| ------------ | ---------- |
| pandas       | 3.1.0      |
| matplotlib   | 3.11.2     |
| scikit-learn | 1.9.1      |
| ipykernel    | 7.4.0      |
| pip          | 26.0.1     |
| numpy        | 3.1.0      |
| scipy        | 3.1.0      |
| pandas       | 3.1.0      |

## 依存関係で入ったもの

asttokens 3.0.2 / cloudpickle 3.1.2 / colorama 0.4.6 / comm 0.2.3 / contourpy 1.4.0 / cycler 0.12.1 / debugpy 1.8.22 / executing 2.3.0 / fonttools 4.68.0 / ipython 9.17.1 / ipython_pygments_lexers 1.1.1 / jedi 0.20.1 / joblib 1.6.0 / jupyter_client 8.10.0 / jupyter_core 5.9.1 / kiwisolver 1.5.1 / matplotlib-inline 0.2.2 / narwhals 2.28.0 / nest-asyncio2 1.7.4 / numpy 2.5.4 / packaging 26.3 / parso 0.8.7 / pillow 13.0.0 / platformdirs 4.14.0 / prompt_toolkit 3.0.53 / psutil 7.2.2 / pure_eval 0.2.4 / Pygments 2.21.0 / pyparsing 3.3.3 / python-dateutil 3.0.0 / pyzmq 27.2.0 / scipy 1.18.1 / six 1.17.0 / stack-data 0.6.3 / threadpoolctl 3.7.0 / tornado 6.6 / traitlets 5.16.1 / typing_extensions 4.16.0 / tzdata 2026.6 / wcwidth 0.9.4

# 仕様書

1. csvデータを読み込む
   csvデータをDataframに入れることで、オブジェクトみたいに使用できる
2. 回転数、rb回数、bb回数から二項分布により1~6設定の起こりやすさを推定（どの設定である確率が高いかを推定）
3. 事前分布を決める
4. 二項分布と事前分布からベイズの定理を使う

6ファイルを読み込んで1つの表にする
機種ごとの「設定別BB・RB確率表」を作る（7機種分。公表値を自分で調べて入力します）
1行（1台・1日）ごとに、設定1〜6それぞれで二項分布の確率を計算する（BBとRBの確率をかけ算）
事前分布（最初は全設定 1/6）をかけて、ベイズの定理で割り直す
設定5・6の確率を足して「高設定っぽさ」とし、CSVに保存する

各設定の定義は？？
二項分布って？？
ベイズ推定って？？
事前分布ってどうきめる？？
