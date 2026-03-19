# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームを想定したPythonパッケージです。  
J-Quants API から市場データ・財務データ・カレンダー・ニュースを収集し、DuckDB 上で ETL／特徴量作成／シグナル生成を行い、発注監査やニュース紐付けまでをサポートするモジュール群を含みます。

概要
- データ取得（J-Quants API 経由）
- DuckDB を用いたデータ格納（Raw / Processed / Feature / Execution 層）
- ファクター計算（Momentum / Volatility / Value など）
- 特徴量正規化（Z スコア）および features テーブルへの保存
- シグナル生成（final_score 計算・BUY/SELL 判定）
- ニュース収集（RSS）と銘柄紐付け
- マーケットカレンダー管理（営業日の判定、先読み更新）
- ETL パイプライン（差分更新・品質チェック）
- 発注・監査用スキーマ（監査ログ/注文/約定など）

主な機能一覧
- kabusys.data.jquants_client: J-Quants API クライアント（ページネーション・リトライ・トークン自動更新）
- kabusys.data.schema: DuckDB のスキーマ定義と初期化（init_schema）
- kabusys.data.pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- kabusys.data.news_collector: RSS 収集と raw_news/news_symbols 保存
- kabusys.data.calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
- kabusys.research: ファクター計算・IC/統計サマリー（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary 等）
- kabusys.strategy: 特徴量構築（build_features）とシグナル生成（generate_signals）
- kabusys.config: 環境変数管理（.env 自動ロード、settings オブジェクト）

必要条件
- Python >= 3.10（型アノテーションに | を使用）
- 必須パッケージ（主要なもの）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）
- J-Quants のリフレッシュトークン等の環境変数

セットアップ手順（例）
1. リポジトリをクローン
   - git clone <your-repo-url>
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージのインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクト配布に requirements.txt があれば）pip install -r requirements.txt
4. 環境変数の設定
   - プロジェクトルートに `.env` を作成すると自動で読み込まれます（ただしテスト等で無効化可能）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL     : kabu API ベースURL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネルID（必須）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : 実行環境（development / paper_trading / live）（デフォルト: development）
     - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. データベース初期化
   - Python から DuckDB スキーマを作成します（初回のみ）。
     例:
     ```bash
     python - <<'PY'
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     print("schema init done")
     PY
     ```

基本的な使い方（例）
- DuckDB 接続を得る方法
  - init_schema() で初期化済み DB を取得、または get_connection() で接続のみ取得できます。
    ```python
    from kabusys.data.schema import init_schema, get_connection
    conn = init_schema("data/kabusys.duckdb")  # 必要ならテーブル作成も行う
    # または既存DBへ接続:
    # conn = get_connection("data/kabusys.duckdb")
    ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())
  ```

- 特徴量（features）作成
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  cnt = build_features(conn, target_date=date(2025, 1, 1))
  print("features upserted:", cnt)
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date(2025, 1, 1))
  print("signals generated:", total)
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  counts = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(counts)
  ```

- カレンダー更新ジョブ（夜間バッチ想定）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("calendar saved:", saved)
  ```

開発・デバッグのヒント
- 環境変数は .env / .env.local → OS 環境変数 の順で読み込まれます。パッケージ内の kabusys.config.settings から値を参照できます。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用）。
- ログレベルは LOG_LEVEL 環境変数で制御します（DEBUG/INFO/...）。
- J-Quants API は rate limit（120 req/min）を守るため内部でスロットリング・リトライを行います。大量取得の際は注意してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込みと settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（fetch/save 関数付き）
    - news_collector.py : RSS 取得・正規化・DB 保存
    - schema.py         : DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py          : zscore_normalize 等の統計ユーティリティ
    - pipeline.py       : ETL パイプライン（run_daily_etl 等）
    - calendar_management.py : カレンダー管理・営業日判定・calendar_update_job
    - audit.py          : 発注/約定の監査ログ用 DDL
    - features.py       : data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py : calc_momentum / calc_volatility / calc_value
    - feature_exploration.py : calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py : build_features（Zスコア正規化・ユニバースフィルタ）
    - signal_generator.py    : generate_signals（final_score 計算・BUY/SELL 生成）
  - execution/
    - （発注・実行層用の名前空間。発注クライアント等はここに追加想定）
  - monitoring/
    - （監視・アラート用のモジュールを配置想定）
- 諸注意: README には収まらない詳細設計（StrategyModel.md, DataPlatform.md 等）を参照する想定の箇所がコード内にコメントとして残されています。

設計上の考慮点（重要）
- ルックアヘッドバイアス対策:
  - ファクター・シグナル生成は target_date 時点の入手可能なデータのみを使用するよう設計されています。
  - 外部データの fetched_at を UTC ベースで記録します（いつシステムがデータを知ったかのトレース用）。
- 冪等性:
  - API から取得した生データは ON CONFLICT 系句で冪等に保存されます（重複挿入の回避）。
  - features / signals 等は日付単位で削除→再挿入の置換を行い、繰り返しの実行で一貫した結果を得られます。
- エラーハンドリング:
  - ETL の各ステップは独立して例外処理され、1 ステップ失敗でも他は継続する設計です（結果は ETLResult に集約されます）。

ライセンス・貢献
- 本 README 内ではライセンス情報を明示していません。配布時には LICENSE ファイルと貢献ガイド（CONTRIBUTING.md）を追加してください。

最後に
- ここに示した使用例はライブラリ API の一例です。運用環境（特に本番発注や live 環境）では十分なテストと安全策（ドライラン、ペーパートレードモード、閾値設定、手動監査）を必ず行ってください。