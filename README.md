# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
DuckDB をデータレイクとして利用し、J-Quants API からのデータ取得、ETL パイプライン、データ品質チェック、ファクター計算、ニュース収集、監査ログなどを提供します。

注意: 本リポジトリは「取引ロジックの基盤・データ基盤」を提供することを主目的としており、実際の発注処理（ブローカー接続）や本番運用は慎重なレビューと安全対策が必要です。

主な特徴
- DuckDB ベースのスキーマ定義と初期化（冪等）
- J-Quants API クライアント（レート制限、リトライ、トークン自動リフレッシュ対応）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集器：安全対策（SSRF、XML BOM、サイズ制限）を実装
- 研究用モジュール：モメンタム・ボラティリティ・バリュー等のファクター計算、IC/統計サマリ
- 監査ログスキーマ：シグナル→発注→約定のトレースを想定したテーブル群
- 軽量な統計ユーティリティ（Zスコア正規化など）

---

目次
- 機能一覧
- 要求環境 / 依存関係
- セットアップ手順
- 簡単な使い方（初期化 / ETL / ニュース収集 / 研究用関数）
- 環境変数一覧
- ディレクトリ構成

---

機能一覧
- data
  - jquants_client: J-Quants API から日足・財務・市場カレンダー取得、DuckDB への冪等保存
  - schema: DuckDB のテーブル定義と init_schema()
  - pipeline / etl: 差分 ETL（run_daily_etl）、個別 ETL ジョブ（prices/financials/calendar）
  - news_collector: RSS 取得・前処理・DB 保存（SSRF 対策・サイズ制限）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査用テーブルの初期化（signal / order_request / executions）
  - stats: zscore_normalize 等の統計ユーティリティ
- research
  - factor_research: momentum / volatility / value 計算
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、summary
- strategy / execution / monitoring
  - 戦略・発注・監視レイヤー向けの空のパッケージ境界（実装を置く想定）

---

要求環境 / 依存関係
- Python 3.10+
  - 注: ソースで PEP 604 (A | B) 型ヒントや型付き辞書を使用しているため Python 3.10 以上を推奨します
- 主要依存（最低限）
  - duckdb
  - defusedxml
- その他: 標準ライブラリ（urllib, logging, datetime 等）

依存パッケージはプロジェクトに requirements.txt がある場合はそちらを使用してください。無い場合は最低限次をインストールしてください:
pip install duckdb defusedxml

---

セットアップ手順（開発ローカル向け）
1. リポジトリをクローンし、Python 仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクトの setup.cfg / pyproject.toml / requirements.txt がある場合はそれに従ってください）
   開発インストール:
   - pip install -e .

3. 環境変数を設定
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）
   - 必須項目の例は後述の「環境変数一覧」を参照

4. DuckDB スキーマ初期化
   Python REPL やスクリプトから:
   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

   これにより data 以下のテーブルが冪等的に作成されます。

---

簡単な使い方

1) DuckDB 初期化（例: スクリプト init_db.py）
from kabusys.data.schema import init_schema
from kabusys.config import settings
conn = init_schema(settings.duckdb_path)
print("DB initialized at", settings.duckdb_path)

2) 日次 ETL 実行（run_daily_etl）
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 引数で target_date / id_token / run_quality_checks 等を指定可能
print(result.to_dict())

3) ニュース収集（RSS）
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄コードセットを用意
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)

4) 研究モジュールの利用例（ファクター計算）
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
from kabusys.data.schema import get_connection
import duckdb
conn = get_connection(settings.duckdb_path)
from datetime import date
target = date(2025, 1, 31)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
# Zスコア正規化例
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

5) J-Quants からのデータ取得を直接使う（テスト用）
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# 取得後は save_* を使って DuckDB に保存できます

注意点
- run_daily_etl / jquants_client は J-Quants の API レート制限（120 req/min）や認証を考慮しています。環境変数 JQUANTS_REFRESH_TOKEN を設定してください。
- 実際の発注を行うモジュールや、本番環境での動作は KABUSYS_ENV を "live" に設定して制御できます。paper_trading / development オプションもありますが、実運用前に十分なテストを行ってください。

---

環境変数一覧（主要なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token で使用）
  - KABU_API_PASSWORD     : kabuステーション等の API パスワード（発注周りで使用）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（通知フローが実装される場合）
  - SLACK_CHANNEL_ID      : Slack チャンネル ID
- オプション / デフォルトあり
  - KABUSYS_ENV           : 動作環境 ("development"（デフォルト） | "paper_trading" | "live")
  - LOG_LEVEL             : ログレベル（"DEBUG" | "INFO"（デフォルト） | "WARNING" | "ERROR" | "CRITICAL"）
  - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用の SQLite パス（デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" をセットすると自動で .env を読み込む処理を無効化

.env の例（.env.example を参考に作成してください）
JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
KABU_API_PASSWORD=<your_kabu_password>
SLACK_BOT_TOKEN=<your_slack_bot_token>
SLACK_CHANNEL_ID=<your_slack_channel_id>
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO

---

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                 - 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py       - J-Quants API クライアント・保存ロジック
      - news_collector.py       - RSS 収集・前処理・保存
      - schema.py               - DuckDB スキーマ定義と init_schema()
      - stats.py                - 統計ユーティリティ（zscore_normalize 等）
      - pipeline.py             - ETL パイプライン（run_daily_etl 等）
      - quality.py              - データ品質チェック
      - calendar_management.py  - カレンダー管理・バッチ更新ジョブ
      - audit.py                - 監査ログスキーマ初期化
      - features.py             - 特徴量ユーティリティ（再エクスポート）
      - etl.py                  - ETL 関連の公開 API（ETLResult 等）
    - research/
      - __init__.py
      - factor_research.py      - モメンタム/ボラティリティ/バリューの計算
      - feature_exploration.py  - 将来リターン / IC / summary 等
    - strategy/
      - __init__.py             - 戦略層（実装を置く場所）
    - execution/
      - __init__.py             - 発注 / 約定処理（実装を置く場所）
    - monitoring/
      - __init__.py             - 監視系（未実装/拡張ポイント）

---

開発上の注意 / ベストプラクティス
- DuckDB の初期化は init_schema() を必ず一度行ってください。既存テーブルはスキップされるため冪等です。
- ETL は差分取得を行いますが、backfill_days パラメータ等で API の後出し修正に対応できます。
- ニュース収集は外部 RSS に依存します。SSRF 対策・サイズ上限等を導入していますが、外部 URL を取り扱う際は注意してください。
- 本番発注ロジック（kabu 等）と接続する際は sandbox / paper_trading 環境で徹底的に検証し、監査ログ（audit テーブル）を有効にしてください。
- テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って .env 自動読み込みを無効にできます。

---

貢献 / 拡張ポイント
- strategy / execution / monitoring の具体的な実装（アルゴリズム、ブローカー接続、リスク管理）
- Slack 等の通知ハンドラの追加
- AI スコアリング・モデルの統合（ai_scores テーブル）
- メトリクス収集・Prometheus exporter 等の監視統合

---

問い合わせ / ライセンス
- 本 README はリポジトリ内のコード構成と docstring をもとに作成しています。実運用前に各モジュールの詳細をレビューしてください。
- ライセンス情報はリポジトリ内の LICENSE ファイルを参照してください（無い場合はプロジェクト方針に従って追加してください）。

以上。必要があれば README のサンプル .env.example、サンプルスクリプト（init_db.py、run_etl.py）を追加で生成します。どの形式が良いか教えてください。