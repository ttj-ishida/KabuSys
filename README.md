# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリです。市場データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等を一貫して扱えるよう設計されています。DuckDB をデータストアに用い、研究（research）モジュールと運用（strategy / execution / data）モジュールを分離しているため、ルックアヘッドバイアスを避けつつ再現性の高いパイプラインを構築できます。

主な特徴:
- J-Quants API 対応（レートリミッタ・リトライ・トークン自動刷新）
- DuckDB ベースの冪等なデータ保存（ON CONFLICT / トランザクション）
- ETL（差分更新・バックフィル・品質チェック）機能
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と Z スコア正規化
- シグナル生成（最終スコア計算、Buy / Sell 判定、Bear レジーム対応）
- ニュース収集（RSS、SSRF対策、トラッキングパラメータ除去、記事→銘柄マッピング）
- マーケットカレンダー管理（営業日判定、前後営業日取得）
- 監査ログ層（signal → order → execution へのトレーサビリティ）

以下で導入・利用方法、ディレクトリ構成を説明します。

---

## 機能一覧（モジュール別サマリ）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定のラッパー（settings オブジェクト）
  - 環境モード: `development`, `paper_trading`, `live`
- kabusys.data
  - jquants_client: J-Quants API クライアント、保存ユーティリティ（raw_prices, raw_financials, market_calendar）
  - schema: DuckDB スキーマ定義と初期化（init_schema / get_connection）
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定、next/prev/get_trading_days、calendar_update_job
  - stats: zscore_normalize 等の統計ユーティリティ
  - features: zscore_normalize の再エクスポート
  - audit: 監査ログ用テーブルの DDL（signal_events / order_requests / executions など）
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value（研究用ファクター計算）
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: raw factors を正規化して features テーブルへ保存
  - signal_generator.generate_signals: features + ai_scores を統合して signals テーブルを作成
- kabusys.execution / kabusys.monitoring
  - 実行・監視層用のプレースホルダ（コードベースによる実装拡張を想定）

---

## 必要要件（例）

- Python 3.9+（typing の一部表記を参照しているため 3.9 以上推奨）
- パッケージ (主なもの)
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS 取得時）

必要パッケージはプロジェクトに合わせて requirements.txt を用意してください。最低限は次のようにインストールできます:

pip install duckdb defusedxml

（プロジェクトで配布される setup/pyproject がある場合はそれを利用してください）

---

## 環境変数（主なもの）

kabusys.config.Settings で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード（発注連携がある場合）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

.env ファイル:
- プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` / `.env.local` を置くと自動でロードされます。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリへ移動

   git clone <repo-url>
   cd <repo-dir>

2. Python 仮想環境の作成（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .\.venv\Scripts\activate   # Windows

3. 必要パッケージをインストール

   pip install -U pip
   pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

4. 環境変数を設定（.env をプロジェクトルートに配置するのが便利）

   例: .env
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. DuckDB スキーマ初期化（サンプル）

   以下の Python スクリプトで DB を初期化します（初回のみ）:

   python -c "from kabusys.config import settings; from kabusys.data.schema import init_schema; init_schema(settings.duckdb_path)"

   もしくはアプリ内で init_schema() を呼び出してください。

---

## 使い方（簡単なコード例）

以下は主要なワークフローの例です。実際にはエラーハンドリングやログ管理、スケジューリング（cron / Airflow 等）を追加してください。

- DuckDB 初期化 & 接続

from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection

# 初回: スキーマ作成
conn = init_schema(settings.duckdb_path)

# 既存 DB に接続するだけなら
# conn = get_connection(settings.duckdb_path)

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得）

from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- 特徴量生成（features テーブル作成）

from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, date.today())
print(f"features upserted: {count}")

- シグナル生成（signals テーブル作成）

from kabusys.strategy import generate_signals
from datetime import date

n = generate_signals(conn, date.today(), threshold=0.60)
print(f"signals written: {n}")

- ニュース収集ジョブ実行（RSS 取得・保存・銘柄紐付け）

from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセットを渡すと紐付け可能
results = run_news_collection(conn, known_codes=known_codes)
print(results)

- カレンダー更新バッチ

from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar rows saved: {saved}")

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス対策:
  - 戦略・特徴量・シグナルは target_date 時点までに“観測可能”な情報だけを使うよう設計されています（research 関数・strategy 関数の docstring を参照）。
- 冪等性:
  - jquants_client.save_*、news_collector.save_raw_news などは重複挿入を避けるため ON CONFLICT や INSERT ... RETURNING を使用しています。
- レート制限とリトライ:
  - J-Quants 呼び出しは内部で固定間隔レートリミット（120 req/min）とリトライ（指数バックオフ）を備えています。
- セキュリティ:
  - RSS 取得は SSRF 対策（リダイレクト・プライベートIP禁止）、XML の defusedxml を使用した安全なパースを行っています。
- 環境:
  - KABUSYS_ENV によって本番（live）・ペーパートレード（paper_trading）・開発（development）を切り替えられます。`settings.is_live/is_paper/is_dev` を参照して処理を分岐可能です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成（抜粋）です:

src/
  kabusys/
    __init__.py
    config.py                        # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py              # J-Quants API クライアント + 保存
      schema.py                      # DuckDB スキーマ定義・初期化
      pipeline.py                    # ETL パイプライン
      news_collector.py              # RSS 収集・保存・銘柄抽出
      calendar_management.py         # マーケットカレンダー管理
      stats.py                       # zscore_normalize 等
      features.py                    # 公開インターフェース
      audit.py                       # 監査ログ DDL
    research/
      __init__.py
      factor_research.py             # calc_momentum / calc_volatility / calc_value
      feature_exploration.py         # forward returns / IC / summary
    strategy/
      __init__.py
      feature_engineering.py         # build_features
      signal_generator.py            # generate_signals
    execution/                        # 発注/実行に関するレイヤ（プレースホルダ）
      __init__.py
    monitoring/                       # 監視用コード（プレースホルダ）

各モジュールはドキュメント文字列（docstring）で設計方針・入出力を明記しています。実装とドキュメントを参照してワークフローを組み立ててください。

---

## 開発・運用のヒント

- テスト時に .env 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- DuckDB をインメモリで試すには init_schema(":memory:") を使用してください。
- 研究/実運用の分離: research の関数は DuckDB 内の履歴データのみを参照し、発注 API にはアクセスしないように設計されています。戦略ロジックを検証するときはこの点を活用してください。

---

README に記載の無い実装詳細や機能追加・運用方法については、該当モジュール（各 .py の docstring）を参照してください。必要に応じて利用例や CLI ラッパー、スケジューラ統合のサンプルを提供できます。