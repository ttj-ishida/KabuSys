# KabuSys — 日本株自動売買システム

短い説明:
KabuSys は日本株向けのデータプラットフォームと自動売買戦略基盤を提供する Python パッケージです。J-Quants API からのデータ取得・DuckDB での永続化・特徴量作成・シグナル生成・ニュース収集などの主要機能を備え、研究 （research）→ 戦略（strategy）→ 実行（execution） のワークフローをサポートします。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（パッケージ起点でプロジェクトルート探索）
  - 必須設定の検証

- データ取得 / ETL
  - J-Quants API クライアント（ページネーション、トークン自動リフレッシュ、レート制限、再試行）
  - 差分取得・バックフィル可能な日次 ETL パイプライン
  - DuckDB スキーマ初期化・接続ユーティリティ（冪等）

- データ処理 / 特徴量
  - factor 計算（momentum / volatility / value）
  - Z スコア正規化ユーティリティ
  - features テーブルへの安全な日付単位アップサート

- 戦略 / シグナル生成
  - features + ai_scores を統合して final_score を計算
  - Bear レジーム判定、BUY/SELL シグナル生成
  - signals テーブルへの日付単位置換（冪等）

- ニュース収集
  - RSS フェッチ、前処理、raw_news への保存（SSRF/大容量/XML攻撃対策）
  - 記事と銘柄コードの紐付け（news_symbols）

- カレンダー管理（JPX）
  - market_calendar の差分更新、営業日判定、次/前営業日取得、期間内営業日列挙

- 実行層スキーマ（監査・オーダー・約定・ポジション管理）
  - 監査ログ、注文要求・約定のトレーサビリティ設計

設計上のポイント:
- ルックアヘッドバイアス対策（target_date 時点のみを参照）
- 冪等性（ON CONFLICT / トランザクション）
- 本番発注層（execution）への直接依存を持たないモジュール分離
- 外部依存を最小化（可能な限り標準ライブラリ＋最低限のライブラリ）

---

## 必要要件（依存パッケージ）

最低限必要な外部パッケージ例（環境により追加が必要です）:
- Python 3.10+
- duckdb
- defusedxml

インストール例:
- pip install -e . あるいは pip install duckdb defusedxml

（実プロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリを取得して仮想環境を用意
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージと依存をインストール
   - pip install -e .
   - または最低限: pip install duckdb defusedxml

3. 環境変数を設定（.env をプロジェクトルートに配置）
   - 自動ロードは .env → .env.local（OS 環境変数が優先）
   - 自動ロードを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

4. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - ":memory:" を渡すとインメモリ DB を使用します（テスト用途）

---

## 使い方（クイックスタート）

以下は主要な操作の例です。実際はアプリケーション側でラッパーやジョブスケジューラから呼び出します。

- DB 初期化
  - from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL を実行（市場カレンダー・株価・財務データを取得）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を指定可能
    print(result.to_dict())

- 特徴量（features）作成
  - from kabusys.strategy import build_features
    build_count = build_features(conn, target_date)  # date オブジェクトを渡す

- シグナル生成
  - from kabusys.strategy import generate_signals
    total_signals = generate_signals(conn, target_date, threshold=0.60, weights=None)

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, sources=None, known_codes=set_of_codes)

- カレンダー更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)

- J-Quants からの直接フェッチ（例: 日足）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    recs = fetch_daily_quotes(date_from=..., date_to=...)
    save_daily_quotes(conn, recs)

注意:
- 多くの関数は duckdb.DuckDBPyConnection を直接受け取り、テスト時は ":memory:" 接続を使って検証できます。
- run_daily_etl 等は内部で例外を捕捉して処理継続するため、戻り値の ETLResult でエラーや品質問題を確認してください。

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必要な場合）
- SLACK_BOT_TOKEN — Slack 通知に使用する bot token
- SLACK_CHANNEL_ID — Slack 送信先チャンネルID

任意／デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値が設定されていれば無効化）

---

## 注意点・設計上の考慮

- ルックアヘッドバイアスを防ぐため、特徴量・シグナル生成は target_date 時点のデータのみを使用します。
- 各保存処理は冪等（ON CONFLICT / トランザクション）を前提に実装されています。再実行しても重複しません。
- ニュース収集は SSRF・XML Bomb・大容量レスポンス等に対する防御ロジックを備えています（defusedxml・受信制限・ホスト検査など）。
- J-Quants API はレート制限（120 req/min）を尊重する実装です。長時間のバッチ実行や多数の銘柄取得時は注意してください。
- execution（ブローカー発注）層は本コードベースで直接発注する箇所は限定されており、実際のブローカー連携は別モジュールやアダプタで行う想定です。

---

## ディレクトリ構成（主要ファイル）

src/
  kabusys/
    __init__.py
    config.py                       # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py             # J-Quants API クライアント + 保存関数
      news_collector.py             # RSS ニュース収集・保存
      schema.py                     # DuckDB スキーマ定義・初期化
      stats.py                      # Zスコア等統計ユーティリティ
      pipeline.py                   # ETL パイプライン（run_daily_etl 等）
      features.py                   # data.stats の再エクスポート
      calendar_management.py        # market_calendar 管理・営業日判定
      audit.py                      # 監査ログスキーマ
      (その他 data モジュール...)
    research/
      __init__.py
      factor_research.py            # モメンタム/ボラ/バリュー計算
      feature_exploration.py        # IC/forward returns/summary
    strategy/
      __init__.py
      feature_engineering.py        # features の構築（build_features）
      signal_generator.py           # generate_signals（BUY/SELL）
    execution/                       # 実行層（発注関連。現状空の __init__）
    monitoring/                      # 監視・モニタリング用（別途実装想定）

（上記は主要ファイルを抜粋した構造です）

---

## 開発・テスト時のヒント

- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます。
- DuckDB の ":memory:" を使えばファイルを作らずに高速な単体テストが可能です。
- jquants_client の HTTP 呼び出しや news_collector のネットワーク I/O はモックして単体テストを行ってください（モジュール内でトークンキャッシュや _urlopen を差し替え可能）。

---

## ライセンス・貢献

（ここにライセンス・貢献方法を追記してください）

---

ご要望があれば、README に「実運用の推奨設定」「cron / Airflow のサンプル」「詳しい .env.example」や「CI 用のテスト例」などを追加できます。必要な内容を教えてください。