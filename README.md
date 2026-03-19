KabuSys
=======

日本株向けの自動売買・データプラットフォームライブラリ（ミニマム実装）。
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、
および DuckDB ベースのスキーマを備え、研究／運用ワークフローを想定したモジュール群を提供します。

主な特徴
--------
- データ取得
  - J-Quants API クライアント（株価日足・財務データ・市場カレンダー取得、ページネーション・リトライ・レート制御対応）
- データ基盤（DuckDB）
  - Raw / Processed / Feature / Execution 層を想定したスキーマ定義と初期化（init_schema）
- ETL パイプライン
  - 差分取得、自動バックフィル、品質チェックフレームワーク（run_daily_etl など）
- 研究支援
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）、将来リターン/IC/統計サマリ
- 特徴量・シグナル生成
  - cross-sectional Z スコア正規化、スコア統合、BUY/SELL シグナルの生成（冪等）
- ニュース収集
  - RSS 収集、記事正規化、銘柄抽出、DB 保存（SSRF/サイズ/XML 攻撃対策）
- マーケットカレンダー管理
  - 営業日判定 / next/prev_trading_day / calendar update job
- 設定管理
  - .env/.env.local から自動読み込み（プロジェクトルート判定）、必須環境変数チェック

サポート Python バージョン
---------------------------
- Python 3.10 以上（型ヒントに Python 3.10 の構文を使用）

必須依存ライブラリ（抜粋）
--------------------------
- duckdb
- defusedxml

（プロジェクトで pyproject.toml / requirements.txt を用意している想定です。開発環境では pip install -e . を利用してください。）

セットアップ手順
----------------

1. リポジトリをクローン
   - 例: git clone <repo-url> && cd <repo-dir>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install duckdb defusedxml
   - （プロジェクトがパッケージ化されている場合）pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）に .env を置くと自動読み込みされます。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN  # J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD      # kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL      # （任意、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN        # Slack 通知用（必須）
   - SLACK_CHANNEL_ID       # Slack チャンネル ID（必須）
   - DUCKDB_PATH            # DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH            # 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV            # 実行環境: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL              # ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   .env の最小例 (.env.example を参考に作成してください)
   - JQUANTS_REFRESH_TOKEN=xxxxx
   - KABU_API_PASSWORD=xxxxx
   - SLACK_BOT_TOKEN=xoxb-...
   - SLACK_CHANNEL_ID=C01234567
   - DUCKDB_PATH=data/kabusys.duckdb

初期化（DuckDB スキーマ）
------------------------
例: Python REPL またはスクリプトから

from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # DB ファイルを作成しスキーマを初期化します

基本的な使い方（抜粋）
----------------------

1) 日次 ETL を実行（市場カレンダー取得 → 株価/財務差分取得 → 品質チェック）
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) 特徴量構築（features テーブルへの書き込み）
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")

3) シグナル生成（signals テーブルへの書き込み）
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
n = generate_signals(conn, target_date=date.today())
print(f"signals generated: {n}")

4) ニュース収集ジョブ
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使う有効なコードの集合（任意）
res = run_news_collection(conn, known_codes=set(["7203","6758"]))
print(res)

5) カレンダー更新ジョブ（夜間バッチ想定）
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

注意点（運用上のポイント）
------------------------
- 環境（KABUSYS_ENV）は "development", "paper_trading", "live" のいずれかであること。
  is_live/is_paper/is_dev プロパティで状態判定できます。
- J-Quants API のレート制限（120 req/min）とリトライ挙動は jquants_client モジュールが扱います。
- ニュース取得では SSRF / XML Bomb / 大容量レスポンス対策が組み込まれています。
- DuckDB への書き込みは冪等（ON CONFLICT / トランザクション）を意識した実装です。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml）を基準に探索します。テスト中などで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要モジュール一覧（概要）
------------------------
- kabusys.config
  - Settings（環境変数ラッパー）、自動 .env ロード、必須変数チェック
- kabusys.data
  - jquants_client.py: J-Quants API クライアント + 保存関数（save_*）
  - schema.py: DuckDB スキーマ定義と init_schema
  - pipeline.py: ETL 実行ロジック（run_daily_etl など）
  - news_collector.py: RSS 収集 / 保存 / 銘柄抽出
  - calendar_management.py: カレンダー管理、営業日判定、calendar_update_job
  - stats.py: zscore_normalize などの統計ユーティリティ
  - features.py: zscore_normalize の再エクスポート
- kabusys.research
  - factor_research.py: calc_momentum / calc_volatility / calc_value
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - feature_engineering.py: build_features
  - signal_generator.py: generate_signals
- kabusys.data.audit: 監査ログ用テーブル定義（signal_events / order_requests / executions など）
- kabusys.data.schema: DB スキーマ定義（Raw/Processed/Feature/Execution 層）

推奨ディレクトリ構成（このリポジトリの主要ファイル）
-------------------------------------------------
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      pipeline.py
      schema.py
      stats.py
      features.py
      calendar_management.py
      audit.py
      ...
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
      ...
    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py
    execution/
      __init__.py
    monitoring/
      ...

貢献・拡張ポイント
-----------------
- Slack 通知連携・リスク管理フィルタの実装（config でトークン管理済み）
- execution 層のブローカー接続ラッパー（kabuステーション等）
- AI スコアの生成パイプライン（ai_scores テーブルの値を生成する外部プロセス）
- テスト（unit/integration）: KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境の注入を行うと便利

ライセンス / コントリビューション
--------------------------------
- （ここにライセンス情報を記載してください。例: MIT / Apache-2.0 等）
- プルリクエスト・Issue は歓迎します。ブランチ戦略・コミットルール等は CONTRIBUTING.md を参照してください（存在する場合）。

最後に
------
この README はコードベース（src/kabusys 以下）から抽出した設計意図と使用方法の概要です。詳細は各モジュールの docstring を参照してください（例: kabusys/data/jquants_client.py のヘッダコメントなど）。不明点があれば具体的な利用ケースを教えてください。README を補足していきます。