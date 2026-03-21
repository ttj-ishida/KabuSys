KabuSys — 日本株自動売買プラットフォーム (README)
概要
- KabuSys は日本株向けのデータプラットフォーム／戦略エンジン／実行基盤を想定したライブラリ群です。
- 主な目的は J‑Quants 等から市場データ・財務データ・ニュースを収集し、DuckDB に保存、ファクター計算→特徴量生成→シグナル生成→（発注 / 監視）へとつなぐ一連の処理を提供することです。
- コードはデータ取得（data/）、リサーチ（research/）、戦略（strategy/）、実行（execution/）などモジュール化されています。

主な機能一覧
- データ取得・保存
  - J‑Quants API クライアント（レート制御／リトライ／トークン自動更新）
  - 株価（日足）・四半期財務・JPX カレンダー取得
  - RSS ベースのニュース収集（正規化・SSRF対策・記事ID生成・銘柄抽出）
  - DuckDB への冪等保存（ON CONFLICT 処理）
- ETL パイプライン
  - 日次 ETL（市場カレンダー/価格/財務の差分取得と保存）
  - 品質チェックフレームワーク連携（quality モジュール想定）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン、IC（Spearman）やファクター統計サマリー
  - Z スコア正規化ユーティリティ
- 戦略
  - 特徴量作成（feature_engineering.build_features）
  - シグナル生成（signal_generator.generate_signals） — コンポーネントスコア統合、Bear レジーム抑制、エグジット判定
- カレンダー管理／監査／実行レイヤーのスキーマ定義
  - DuckDB スキーマ初期化（data.schema.init_schema）
  - 監査ログ（signal_events / order_requests / executions 等）の DDL

前提条件 / 必要なもの
- Python 3.10+（typing の union 型表記等を使用）
- DuckDB（Python パッケージ duckdb）
- ネットワークアクセス（J‑Quants API, RSS）
- （ニュースパーシング）defusedxml 等の安全な XML パーサ（推奨）
- 環境変数に API トークン等を設定（下記参照）

環境変数（主要）
- 必須
  - JQUANTS_REFRESH_TOKEN — J‑Quants の refresh token（fetch に使用）
  - KABU_API_PASSWORD — kabu ステーション API 用パスワード（execution 層で使用）
  - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（monitoring/通知）
  - SLACK_CHANNEL_ID — Slack チャンネル ID
- 任意 / デフォルトあり
  - KABUSYS_ENV — 動作モード: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- 備考
  - パッケージはプロジェクトルートの .env / .env.local を自動で読み込む（CWD ではなくパッケージ位置を基準）
  - .env.example を参考に .env を作成してください（機密情報はリポジトリにコミットしないでください）

セットアップ手順（ローカル開発用）
1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （開発中は pip install -e . を使ってローカルパッケージとしてインストール可能）

4. 環境変数設定
   - プロジェクトルートに .env を作成して必須キーを設定（例）
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - KABU_API_PASSWORD=xxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
   - or OS 環境変数としてエクスポートしても可

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
   - これにより必要なテーブルとインデックスが作成されます

基本的な使い方（例）
- DB 初期化
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)

- 日次 ETL 実行（市場カレンダー・株価・財務を差分取得）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を渡すことも可
  - print(result.to_dict())

- 特徴量のビルド（戦略用 features テーブルの作成）
  - from datetime import date
  - from kabusys.strategy import build_features
  - count = build_features(conn, date(2025, 1, 31))

- シグナル生成
  - from kabusys.strategy import generate_signals
  - n = generate_signals(conn, date(2025, 1, 31))

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - known_codes = {"7203", "6758", ...}  # 有効銘柄コードセット
  - stats = run_news_collection(conn, known_codes=known_codes)
  - print(stats)

- カレンダー更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- J‑Quants からの直接データ取得（例: 日足フェッチ）
  - from kabusys.data.jquants_client import fetch_daily_quotes
  - records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))

運用上の注意
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を基準）を探索します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- J‑Quants API はレート制限があります（120 req/min）。jquants_client は内部で固定間隔スロットリングとリトライを実装していますが、外部からの多重並列呼び出しは注意してください。
- DuckDB への書き込みはモジュール内でトランザクションを使用して原子性を確保していますが、運用スクリプトでも適切な例外処理を行ってください。
- ニュース収集は外部 RSS を解析します。fetch_rss は SSRF 対策（ホストチェック / リダイレクト検査）や XML の脆弱性対策（defusedxml）を実装していますが、運用先のネットワークポリシーに合わせて監視してください。
- 本リポジトリには実際の発注（ブローカー）接続実装は含まれていないか限定的です。live 環境での発注は十分な安全検証を行ってください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J‑Quants API クライアント + 保存関数
    - news_collector.py           — RSS ニュース収集・保存
    - schema.py                   — DuckDB スキーマ定義・初期化
    - stats.py                    — zscore_normalize 等統計ユーティリティ
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      — カレンダー管理 / 更新ジョブ
    - features.py                 — features API 再エクスポート
    - audit.py                    — 監査ログ DDL（signal/order/execution トレース）
    - ...（その他 data 関連モジュール）
  - research/
    - __init__.py
    - factor_research.py          — Momentum/Volatility/Value 等の計算
    - feature_exploration.py      — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py      — features テーブル生成（正規化・フィルタ）
    - signal_generator.py         — final_score 計算・BUY/SELL 生成
  - execution/                     — 発注／execution 層（パッケージ用意）
  - monitoring/                    — 監視/通知（Slack 等）用（想定）

開発者向け補足
- 単体モジュールは duckdb コネクションを引数で受け取り、副作用を最小化しています（テスト時に in‑memory DB を渡せます）。
- Z スコア正規化やランク計算は外部依存を避け、標準ライブラリのみで実装されています（テストしやすい設計）。
- 設定管理は自動で .env を読み込みますが、ユニットテスト等で環境汚染を避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

よくある運用フロー（参考）
1. スキーマ初期化（init_schema）
2. 夜間／朝のバッチで run_daily_etl を実行 → データ更新
3. build_features で features を作成
4. generate_signals でシグナル生成 → signals テーブルに出力
5. execution 層で signals を読み、実際の発注処理（外部ブローカー API）へ送信
6. trades / positions / audit テーブルで追跡・監査

問い合わせ / 貢献
- バグや機能提案は Issue を立ててください。プルリクエスト歓迎です。
- 機密情報（API トークン等）は絶対にコミットしないでください。

以上です。README の内容をプロジェクトに合わせて調整（依存関係の明示的な requirements.txt 追加、実行スクリプトの提供など）すると初期導入がよりスムーズになります。必要であればサンプルスクリプトや具体的な .env.example を作成して差し上げます。