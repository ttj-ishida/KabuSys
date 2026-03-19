# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ群です。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ・監査ロギング等の機能を備えます。

---

## プロジェクト概要

KabuSys は以下のレイヤーで構成された日本株自動売買基盤向けのツール群です。

- データ取得（J-Quants API）と生データ保存（raw layer）
- ETL による整形・集計（processed / feature layer）
- 研究用ファクター計算および特徴量エンジニアリング
- 戦略に基づくシグナル生成（BUY / SELL）
- ニュース収集と銘柄紐付け
- DuckDB を用いたローカルデータベーススキーマと監査ログ
- マーケットカレンダー管理（JPX）

設計上のポイント:
- ルックアヘッドバイアス回避（target_date 時点のデータのみ参照）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで安全）
- 外部依存を最小限に（標準ライブラリ + 必須ライブラリ）
- テストしやすい設計（トークン注入など）

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API から日足・財務・カレンダーを取得（ページネーション対応）
  - レート制限／リトライ／トークン自動リフレッシュ対応
  - DuckDB へ冪等保存（raw_prices, raw_financials, market_calendar など）
- data/pipeline
  - 差分 ETL（run_daily_etl）: カレンダー・日足・財務の差分取得と品質チェック
- data/schema
  - DuckDB スキーマ定義と初期化（init_schema）
- data/news_collector
  - RSS フィードからニュース収集、前処理、raw_news / news_symbols 保存
  - SSRF・XML Bomb 等の安全策を導入
- data/calendar_management
  - 営業日判定・next/prev_trading_day・カレンダー更新ジョブ
- research
  - ファクター計算（momentum / volatility / value）と解析ユーティリティ（IC, forward returns 等）
- strategy
  - feature_engineering.build_features: ファクター正規化・フィルタ適用・features テーブル更新
  - signal_generator.generate_signals: features + ai_scores を統合して最終スコアを計算、signals テーブルへ出力
- config
  - .env / 環境変数の自動ロード（プロジェクトルート検出）と型・必須チェック（Settings）

---

## 必要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（execution 層使用時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — environment: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: `data/monitoring.db`）

注:
- プロジェクトルートに `.env` / `.env.local` がある場合、自動で読み込まれます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル）

1. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 必須: duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトがパッケージ化されていれば）pip install -e . を推奨

3. 環境変数設定
   - プロジェクトルートに `.env` を作成して必須キーを設定するか、OS 環境変数として設定してください。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 使い方（主要な操作）

以下は典型的な日次バッチワークフロー例です。

1. DuckDB 初期化（最初のみ）
   - from kabusys.data.schema import init_schema
     conn = init_schema(settings.duckdb_path)

2. 日次 ETL 実行（市場カレンダー・日足・財務を差分取得）
   - from kabusys.data.pipeline import run_daily_etl
     result = run_daily_etl(conn)  # target_date を指定することも可能
     print(result.to_dict())

3. 特徴量構築（戦略用 features テーブルの更新）
   - from kabusys.strategy import build_features
     build_count = build_features(conn, target_date)  # target_date は date オブジェクト

4. シグナル生成（signals テーブルへ書き込み）
   - from kabusys.strategy import generate_signals
     total_signals = generate_signals(conn, target_date, threshold=0.6)

5. ニュース収集（RSS を取得して raw_news / news_symbols を保存）
   - from kabusys.data.news_collector import run_news_collection
     results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))

6. カレンダー更新（夜間ジョブ）
   - from kabusys.data.calendar_management import calendar_update_job
     saved = calendar_update_job(conn)

7. その他ユーティリティ
   - research モジュール（calc_ic / calc_forward_returns / factor_summary 等）
   - data.jquants_client の fetch_*/save_* を直接使った柔軟な処理

注意点:
- ほとんどの関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。
- target_date はルックアヘッドを避けるため明示的に date 型で与えてください。
- generate_signals / build_features は DB の features / ai_scores / positions / prices_daily 等を参照します。事前に ETL と features の構築が必要です。

---

## 代表的な API（抜粋）

- init_schema(db_path) -> DuckDB 接続
- run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True) -> ETLResult
- build_features(conn, target_date: date) -> int  (upsert した銘柄数)
- generate_signals(conn, target_date: date, threshold: float = 0.6, weights: dict|None = None) -> int
- run_news_collection(conn, sources: dict|None = None, known_codes: set|None = None) -> dict
- calendar_update_job(conn, lookahead_days: int = 90) -> int

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント / 保存ロジック
    - news_collector.py               — RSS ニュース収集 / 前処理 / 保存
    - schema.py                       — DuckDB スキーマ定義と init_schema
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py          — マーケットカレンダー管理
    - stats.py                        — zscore_normalize 等
    - features.py                     — features 公開ラッパー
    - audit.py                         — 監査ログテーブル定義
  - research/
    - __init__.py
    - factor_research.py              — momentum / volatility / value の計算
    - feature_exploration.py          — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py          — build_features
    - signal_generator.py             — generate_signals
  - execution/                         — 発注 / execution 層（空の __init__ 等）

---

## 動作確認・トラブルシューティング

- 環境変数の未設定で ValueError が出る場合、settings (kabusys.config.Settings) が必須キーを検査しています。`.env` を作成するか環境変数を設定してください。
- DuckDB のファイルパスに対して親ディレクトリが無い場合、init_schema が自動で作成します。
- J-Quants API 呼び出しで 401 が返る場合、jquants_client がリフレッシュトークンから自動で id token を取得します。リフレッシュトークンが無効な場合は失敗します。
- RSS 収集時にリダイレクトで内部アドレスに到達する場合は安全のためブロックされます（SSRF 防止）。
- ロギングレベルは環境変数 LOG_LEVEL で調整できます。

---

## 貢献・拡張のヒント

- execution 層の broker 接続／注文送信ロジックはプロジェクトのニーズに合わせて実装してください。現在はデータ層と戦略層を切り離す設計になっています。
- AI スコア（ai_scores）を生成するモジュールを追加して、signal_generator に組み込むことができます（ai_scores テーブル仕様は schema.py を参照）。
- 品質チェック（quality モジュール）は pipeline.run_daily_etl から呼ばれます。新しいチェックを追加してデータ品質を向上させてください。

---

必要であれば README に「実行例スクリプト」や「.env.example」のテンプレート、CI/CD 用のジョブ定義（cron / GitHub Actions）などを追記できます。どの点を詳細化したいか教えてください。