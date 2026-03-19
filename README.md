# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査・実行レイヤ向けスキーマ等を含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データプラットフォーム向けに設計された Python パッケージです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新付き）
- DuckDB を用いた冪等な生データ保存・スキーマ管理
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用途のファクター計算・特徴量生成（Zスコア正規化等）
- 戦略側のシグナル生成（ファクター統合・AIスコア統合・エグジット判定）
- ニュース収集（RSS、SSRF対策、トラッキングパラメータ除去）と銘柄紐付け
- 監査ログ（signal → order → execution のトレース可能なテーブル）
- 実行・監視レイヤの骨組み（スキーマ・信号テーブル等）

パッケージは内部で次のサブパッケージを公開します:
kabusys.data, kabusys.research, kabusys.strategy, kabusys.execution, kabusys.monitoring（必要に応じて拡張）

---

## 機能一覧

主な機能（抜粋）:

- data/jquants_client.py
  - J-Quants API クライアント（ページネーション対応、レートリミット管理、リトライ、トークン自動更新）
  - 日足・財務・市場カレンダー取得および DuckDB への保存関数（冪等）

- data/schema.py
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution の各レイヤ）
  - テーブル・インデックスの作成を一括実行する init_schema()

- data/pipeline.py
  - 日次 ETL（市場カレンダー → 株価差分 → 財務差分 → 品質チェック）
  - 差分更新・バックフィル対応・ETL 結果の ETLResult 出力

- data/news_collector.py
  - RSS 収集（SSRF対策・gzip制限・XML安全パーサ）
  - 記事の正規化、ID生成（URL正規化→SHA256）、raw_news 保存、銘柄抽出と紐付け

- data/calendar_management.py
  - market_calendar を基にした営業日判定 / next/prev_trading_day / get_trading_days
  - カレンダーの差分更新ジョブ

- data/audit.py
  - signal_events / order_requests / executions 等の監査用テーブル定義と初期化（トレーサビリティ）

- research/*.py
  - ファクター計算（momentum / volatility / value）
  - 研究用ユーティリティ（将来リターン計算、IC 計測、統計サマリー、Zスコア正規化）

- strategy/feature_engineering.py
  - research 側の raw factor を取り込みユニバースフィルタ→正規化→features テーブルへ保存（冪等）

- strategy/signal_generator.py
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL のルール適用、signals テーブルへの書き込み（冪等）

その他、統計ユーティリティ（zscore_normalize）や ETL 品質チェック（quality モジュール想定）も含みます。

---

## セットアップ手順

必要条件
- Python 3.10 以上（PEP 604 の型表記などを使用）
- DuckDB, defusedxml 等の依存パッケージ

推奨手順（UNIX 系）:

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （プロジェクトがパッケージ化されていれば）pip install -e .

   > 参考: requirements.txt / pyproject.toml がある場合はそれらからインストールしてください。

4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を配置できます（自動ロードあり）。  
     自動ロードは env/config.py により .env（→ .env.local）の順で読み込みます。  
     無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須の環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（execution 関連で使用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（監視/通知用）
   - SLACK_CHANNEL_ID: Slack チャネル ID

   任意（デフォルト有り）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C1234567890
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - Python REPL またはワンライナーで実行:
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（例）

以下は代表的な操作例です。実行前に環境変数と依存関係を整えてください。

1) DuckDB スキーマの作成
- Python で:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL を実行（J-Quants から差分取得して保存）
- 例（当日分を実行）:
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl
  import datetime
  conn = init_schema("data/kabusys.duckdb")
  res = run_daily_etl(conn, datetime.date.today())
  print(res.to_dict())

3) 特徴量（features）を構築
- 例:
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from datetime import date
  conn = get_connection("data/kabusys.duckdb")
  build_features(conn, date(2025, 1, 15))

4) シグナルの生成
- 例:
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from datetime import date
  conn = get_connection("data/kabusys.duckdb")
  generate_signals(conn, date(2025, 1, 15), threshold=0.6)

5) ニュース収集ジョブ（RSS）
- 例:
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

6) J-Quants から日足取得（低レベル利用）
- 例:
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=datetime.date(2025,1,1), date_to=datetime.date(2025,1,15))
  save_daily_quotes(conn, records)

注意点:
- ほとんどの DB 書き込み関数は「日付単位の置換」や ON CONFLICT を使い冪等性を保っています。
- run_daily_etl 等は内部で例外を捕捉し、可能な部分は継続して実行する設計です。戻り値（ETLResult）で状態を確認してください。

---

## ディレクトリ構成（抜粋）

プロジェクトは src 配下にパッケージ化されています。主な構成は以下の通りです。

- src/
  - kabusys/
    - __init__.py            # パッケージ公開（data, strategy, execution, monitoring）
    - config.py              # 環境変数読み込み・設定管理
    - data/
      - __init__.py
      - jquants_client.py    # API クライアント（取得・保存・リトライ・レート制御）
      - news_collector.py    # RSS 収集・前処理・保存・銘柄抽出
      - schema.py            # DuckDB スキーマ定義・init_schema
      - pipeline.py          # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py
      - features.py
      - stats.py             # zscore_normalize 等の統計ユーティリティ
      - audit.py             # 監査ログ用テーブル定義
    - research/
      - __init__.py
      - factor_research.py   # モメンタム/ボラティリティ/バリュー計算
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/              # 発注・約定管理（拡張点）
    - monitoring/             # 監視・通知（拡張点）

---

## 実運用上の注意事項

- 環境: production（live）運用時は KABUSYS_ENV=live を設定してください。paper_trading 用のモードも想定されています。
- 認証: J-Quants トークンはセキュアに保管してください。config.Settings は必要変数が未設定の場合 ValueError を投げます。
- レート制御: J-Quants API の制限（120 req/min）に従う実装が組み込まれていますが、運用時は API 利用ポリシーを確認してください。
- セキュリティ: news_collector は SSRF・XML ベース攻撃・巨大レスポンス等への対策を実装していますが、外部フィードの扱いには注意してください。
- テスト: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で .env の自動ロードを無効化でき、テストの際に便利です。

---

## 拡張ポイント / TODO（設計に記載の未実装点）

- strategy のいくつかのエグジット条件（トレーリングストップ、時間決済）は positions テーブルの拡張が必要です。
- execution 層（証券会社との送受信）および監視/アラートの具体実装は別途実装が必要です。
- 品質チェックモジュール（quality）はインターフェースを呼んでいますが、詳細実装／ポリシーの調整が必要です。

---

質問や README に追記してほしい運用例・コードスニペットがあれば教えてください。必要に応じて実行コマンドやサンプル .env.example を追記します。