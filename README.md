# KabuSys — 日本株自動売買システム（README）

バージョン: 0.1.0

概要
----
KabuSys は日本株を対象としたデータプラットフォームと自動売買の基盤ライブラリです。  
主に以下の責務を持ちます。

- J-Quants などの外部 API からマーケットデータ・財務データ・市場カレンダー・ニュースを取得して DuckDB に保存する ETL パイプライン
- 研究（research）で算出した生ファクターを正規化・合成して strategy 層の特徴量を作成する機能
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成する機能
- ニュース収集・銘柄抽出・データ品質チェックなど、DataPlatform に即した補助機能

主な機能一覧
--------------
- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ、DuckDB への冪等保存）
  - pipeline: 日次 ETL 実行（差分取得・バックフィル・品質チェックの一括実行）
  - news_collector: RSS からニュース収集 → raw_news / news_symbols への保存
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤ）
  - stats: Z スコア正規化等の統計ユーティリティ
  - calendar_management: JPX カレンダー管理と営業日判定
  - audit: 発注〜約定の監査用テーブル定義（監査ログ）
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリーなど
- strategy/
  - feature_engineering: 研究で算出した生ファクターを正規化・合成して features テーブルへ保存
  - signal_generator: features・ai_scores・positions を元に BUY/SELL シグナルを生成して signals テーブルへ保存
- execution/: 発注・約定・ポジション管理など execution 層のプレースホルダ（将来的な実装）
- monitoring: 監視・アラート等のプレースホルダ（将来）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の PEP 604 記法や型ヒントを利用）
- DuckDB を使います（pip パッケージ duckdb）
- defusedxml（RSS パース用）など一部外部ライブラリ

1) リポジトリをクローン
   git clone <repo-url>
   cd <repo-directory>

2) 仮想環境を作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3) 必要パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに setup/requirements があれば pip install -e . を推奨）

4) 環境変数の設定
   プロジェクトルートに .env / .env.local を配置すると自動ロードされます（優先順位: OS 環境変数 > .env.local > .env）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN     … J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD         … kabuステーション API のパスワード（execution 層を使う場合）
   - SLACK_BOT_TOKEN           … Slack 通知用（必要に応じて）
   - SLACK_CHANNEL_ID         … Slack チャンネル ID

   オプション:
   - KABUSYS_ENV               … development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL                 … DEBUG/INFO/...
   - DUCKDB_PATH               … デフォルト data/kabusys.duckdb
   - SQLITE_PATH               … デフォルト data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5) DuckDB スキーマ初期化
   Python REPL やスクリプトで schema.init_schema を呼んで DB を初期化します（親ディレクトリ自動作成）。

   例:
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")
   # または: conn = get_connection("data/kabusys.duckdb")  # 既存 DB に接続する場合
   ```

使い方（主要な API と実行例）
----------------------------

- 日次 ETL 実行（市場カレンダー・株価・財務データの差分取得、品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量構築（strategy.feature_engineering.build_features）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date.today())
  print(f"features updated: {n}")
  ```

- シグナル生成（strategy.signal_generator.generate_signals）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は有効な銘柄コード集合（抽出のため）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"market calendar saved: {saved}")
  ```

補足
- auto env load: パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動で読み込みます。テスト等で無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- データベースファイルの既定値は DUCKDB_PATH= data/kabusys.duckdb です。大容量データ想定のため適切なストレージを確保してください。
- J-Quants API のリクエストはレート制限（120 req/min）を守るよう実装されています。

ディレクトリ構成
----------------

簡易ツリー（主要ファイルのみ）。実際は src/kabusys 以下にモジュールが配置されています。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - (monitoring)  # 今後の追加予定（__init__ ではエクスポート対象に含まれています）

各モジュールの要点
- config.py: .env 自動読み込み、必須環境変数チェック、settings オブジェクト。KABUSYS_ENV / LOG_LEVEL 等のバリデーションを提供。
- data/schema.py: DuckDB のテーブル定義（Raw / Processed / Feature / Execution）と初期化 API（init_schema）。
- data/jquants_client.py: J-Quants との通信（トークン取得、ページネーション、保存用ユーティリティ）。
- data/pipeline.py: 差分 ETL / 日次 ETL 実行 / quality チェックの統合（run_daily_etl）。
- data/news_collector.py: RSS の安全な取得（SSRF 対策、gzip 上限、XML 脆弱性対策）と raw_news への冪等保存、銘柄抽出。
- research/*: ファクター計算と探索用ツール（forward returns / IC / summary）。
- strategy/*: features の構築（Zスコア正規化・ユニバースフィルタ適用）とシグナル生成（final_score の計算、Bear レジーム抑制、BUY/SELL 判定、signals テーブルへの保存）。

ライセンス・貢献
----------------
（プロジェクトに LICENSE ファイルがあればそこを参照してください。コントリビュートの流れやコード規約は別途 CONTRIBUTING.md を用意することを推奨します。）

最後に
------
この README はコードベースの主要機能と使い方をまとめた簡易ガイドです。実運用や本番導入時は必ずテスト環境で動作確認を行い、API キー・トークンの取り扱い、発注処理の冪等性・監査ログの管理、リスク管理ポリシーを整備してください。追加でドキュメント（StrategyModel.md / DataPlatform.md / 等）がある場合はそちらも併せて参照してください。