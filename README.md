KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。本リポジトリには以下の主要機能が含まれます。

- データ取得（J-Quants API）と DuckDB への保存
- ファクター計算・特徴量構築（research / strategy の前処理）
- シグナル生成（strategy）
- ポートフォリオ構築（候補選定・配分・サイジング・リスク制御）
- バックテストフレームワーク（擬似約定シミュレータ・評価指標）
- ニュース収集（RSS → raw_news / news_symbols）

この README では、セットアップ手順、主要な使い方例、環境変数、ディレクトリ構成をまとめます。

主な機能一覧
-------------
- data
  - J-Quants API クライアント（レート制御・自動トークンリフレッシュ・ページネーション・DuckDB 保存）
  - ニュース収集（RSS パーシング・前処理・SSRF 対策・DB 保存）
- research
  - ファクター計算（momentum / volatility / value）
  - 研究用ユーティリティ（forward returns, IC, summary）
- strategy
  - 特徴量エンジニアリング（features テーブルへの UPSERT）
  - シグナル生成（final_score 計算・BUY/SELL 判定・signals テーブルへ保存）
- portfolio
  - 候補選定、重み計算、ポジションサイジング、セクター制約、レジーム乗数
- backtest
  - バックテストエンジン（データのインメモリコピー、日次ループ、擬似約定、ポートフォリオ履歴）
  - 評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- その他
  - コンフィグ管理（環境変数・.env 自動ロード）
  - データスキーマ / カレンダー管理 等（data パッケージに想定された周辺機能と連携）

動作要件（推奨）
----------------
- Python 3.10+
- 必須ライブラリ（一例）
  - duckdb
  - defusedxml
- 追加（用途により）
  - requests 等（このコードベースでは標準 urllib を使用）
- DuckDB を利用するため、pip で duckdb をインストールしてください。

セットアップ手順
----------------

1. リポジトリを取得
   - git clone ... （任意の場所にクローン）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください:
    pip install -r requirements.txt）

4. 開発インストール（任意）
   - プロジェクトルートで: pip install -e .

環境変数 / .env
----------------
config.py により、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して以下の順で .env を読み込みます:
OS 環境変数 > .env.local > .env
（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

重要な環境変数（例）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabu API のパスワード（必須）
- KABU_API_BASE_URL     : kabu API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（モニタリング DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 環境（development | paper_trading | live）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

サンプル .env
--------------
以下は参考例（値は置き換えてください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

主要な使い方（例）
-----------------

1) バックテスト（CLI）
- 前提: DuckDB ファイルが prices_daily, features, ai_scores, market_regime, market_calendar 等で必要データが準備済みであること。
- 実行例:

python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-29 \
  --cash 10000000 \
  --db path/to/kabusys.duckdb \
  --allocation-method risk_based \
  --lot-size 100

- 出力: バックテストのメトリクス（CAGR 等）を標準出力に表示します。

2) プログラムから各機能を呼ぶ（簡単なサンプル）
- DuckDB コネクションを初期化（本実装では kabusys.data.schema.init_schema を想定）

from kabusys.data.schema import init_schema
from kabusys.strategy import build_features, generate_signals
import duckdb
from datetime import date

conn = init_schema("path/to/kabusys.duckdb")
target = date(2024, 1, 4)
# 特徴量計算
count = build_features(conn, target)
# シグナル生成
signals = generate_signals(conn, target)
conn.close()

3) J-Quants データ取得 & 保存
- fetch / save 関数を使って日足や財務データを取得・保存できます（settings に JQUANTS_REFRESH_TOKEN の設定が必要）。

from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.jquants_client import get_id_token
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
token = get_id_token()
recs = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,12,31))
save_daily_quotes(conn, recs)
conn.close()

4) ニュース収集ジョブ
- RSS を収集して raw_news / news_symbols に保存するユーティリティ run_news_collection が提供されています。

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203","6758",...}  # stocks テーブル等から取得する
res = run_news_collection(conn, known_codes=known_codes)
conn.close()

注意点 / 動作ポリシー
--------------------
- Look-ahead bias（ルックアヘッドバイアス）対策が設計に組み込まれています。各処理は target_date 時点で利用可能なデータのみを参照することを意図しています。
- J-Quants クライアントは API レート制限を守るため内部でレートリミッタとリトライを実装しています。401 受信時は自動的にトークンリフレッシュを試みます。
- ニュース収集は SSRF 対策（ホスト検査・リダイレクト検証）や XML 安全処理（defusedxml）を行います。
- .env の自動ロードはプロジェクトルートを .git / pyproject.toml で検出して行われます。CI / テスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                — パッケージ初期化、バージョン
- config.py                  — 環境変数 / .env の読み込みと Settings クラス

src/kabusys/data/
- jquants_client.py          — J-Quants API クライアント + DuckDB 保存
- news_collector.py         — RSS 収集・前処理・DB 保存
- (schema, calendar_management 等が想定される別モジュールと連携)

src/kabusys/research/
- factor_research.py         — momentum/volatility/value の計算
- feature_exploration.py     — forward returns / IC / summary
- __init__.py

src/kabusys/strategy/
- feature_engineering.py     — features テーブル構築
- signal_generator.py        — final_score 計算と signals テーブルへの書き込み
- __init__.py

src/kabusys/portfolio/
- portfolio_builder.py       — 候補選定、重み計算
- position_sizing.py         — 株数計算、aggregate cap
- risk_adjustment.py         — セクターキャップ、レジーム乗数
- __init__.py

src/kabusys/backtest/
- engine.py                  — バックテストループ（run_backtest）
- simulator.py               — 擬似約定・ポートフォリオ状態管理
- metrics.py                 — バックテスト評価指標計算
- run.py                     — CLI (python -m kabusys.backtest.run)
- clock.py                   — （将来用）模擬時計
- __init__.py

src/kabusys/portfolio, strategy, research, backtest などは相互に独立した pure function を意識して実装されています（DB 参照を最小化、テスト容易性を重視）。

開発 / 貢献
------------
- コードはユニットテストが書きやすい設計（副作用を抑えた純関数群）です。pull request / issue を歓迎します。
- 変更を加える際は既存の挙動（特にバックテストの再現性）に注意してください。

ライセンス
----------
- 本リポジトリにライセンスファイルが含まれていなければ、利用・再配布に関しては注意してください（社内プロジェクト等での利用を想定）。

補足
----
- 実運用（kabu ステーション経由の発注や Slack 通知など）を行う場合、KABU API 設定や Slack トークンの管理に特に注意してください。
- DuckDB のスキーマ初期化・テーブル定義や外部 ETL（prices_daily の事前投入等）は別途スクリプト / ドキュメントを参照してください（data.schema を想定）。

問題や不明点があれば、どの機能について詳しく知りたいか教えてください。セットアップ、実行方法、あるいは個別モジュールの使い方（例: calc_position_sizes のパラメータ説明）など、具体的な要望に合わせて README を拡張します。