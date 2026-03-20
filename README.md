KabuSys
=======

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。データ取得（J-Quants）、ETL、特徴量エンジニアリング、シグナル生成、ニュース収集、DuckDB スキーマ管理、監査ログなどを含むモジュール群を備え、研究 → バックテスト → 実運用へと移行しやすい設計になっています。

主な設計方針
- ルックアヘッドバイアス（将来情報の漏洩）を避ける設計
- DuckDB を用いたローカルデータレイヤ（Raw / Processed / Feature / Execution）
- 冪等性（ON CONFLICT / idempotent 保存）
- シンプルな外部依存（標準ライブラリ中心、必要に応じて duckdb / defusedxml など）

機能一覧
- データ取得（J-Quants API クライアント）
  - 日足（OHLCV）・財務データ・マーケットカレンダーの取得（ページネーション対応、リトライ、レート制御）
- DuckDB スキーマ定義・初期化（init_schema）
- ETL パイプライン（日次差分取得、バックフィル、品質チェック呼び出し）
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ）
- シグナル生成（コンポーネントスコア集約、Bear レジーム抑制、BUY/SELL 判定）
- ニュース収集（RSS フィード取得、前処理、記事保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定、翌営業日/前営業日取得）
- 監査ログ（signal → order → execution トレーサビリティ）

セットアップ手順（開発環境）
- 前提
  - Python 3.10+（型注釈の一部で union 型記法を使用）
  - pip
- 仮想環境作成（推奨）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 依存パッケージ（例）
  - duckdb
  - defusedxml
  - （その他の依存はプロジェクトの requirements.txt / pyproject.toml を参照してください）
- インストール例
  - pip install duckdb defusedxml
  - pip install -e .  （パッケージ配布用設定がある場合）

環境変数（主な必須／推奨設定）
- 必須（実行機能に応じて）
  - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
  - SLACK_BOT_TOKEN — Slack 通知に使用する場合
  - SLACK_CHANNEL_ID — Slack チャネル ID
  - KABU_API_PASSWORD — kabuステーション（発注）パスワード
- オプション / デフォルトあり
  - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動読み込みを無効化
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

サンプル .env（プロジェクトルートに配置）
  JQUANTS_REFRESH_TOKEN=xxx
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  KABU_API_PASSWORD=your_kabu_password
  KABUSYS_ENV=development
  LOG_LEVEL=INFO
  DUCKDB_PATH=data/kabusys.duckdb

注意: パッケージは起点ファイルの親ディレクトリで .git または pyproject.toml を探して自動的に .env を読み込みます（無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

基本的な使い方（コード例）
- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  conn = init_schema(settings.duckdb_path)

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())

- 特徴量作成（features テーブルへ書き込み）
  from kabusys.strategy import build_features
  n = build_features(conn, date.today())
  print(f"features upserted: {n}")

- シグナル生成（signals テーブルへ書き込み）
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, date.today())
  print(f"signals written: {total}")

- ニュース収集ジョブ実行（既知銘柄セットを渡す）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

- マーケットカレンダー更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

主要 API・関数（ピックアップ）
- kabusys.config.settings — アプリケーション設定アクセサ
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ作成
- kabusys.data.pipeline.run_daily_etl(conn, target_date) — 日次 ETL のメイン
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes — データ取得と保存
- kabusys.research.calc_momentum / calc_volatility / calc_value — ファクター計算
- kabusys.strategy.build_features — features の作成
- kabusys.strategy.generate_signals — signals の生成
- kabusys.data.news_collector.run_news_collection — RSS 収集 + 保存

フォールバック・安全設計メモ
- RSS 収集は SSRF 対策・レスポンスサイズ制限・XML パースのハードニングを行っています
- J-Quants クライアントはレート制御、リトライ、401 時のトークンリフレッシュを実装
- DuckDB 保存は多くの場所で ON CONFLICT を使い冪等性を担保
- 市場カレンダーが未取得のときは曜日ベースのフォールバックで営業日判定を行います

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - news_collector.py  — RSS ニュース収集・保存
    - schema.py  — DuckDB スキーマ定義・init_schema
    - stats.py  — 汎用統計ユーティリティ（zscore_normalize）
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理
    - features.py — data.stats の再エクスポート
    - audit.py — 監査ログ用スキーマ
    - (その他 data/*.py...)
  - research/
    - __init__.py
    - factor_research.py  — momentum / volatility / value の計算
    - feature_exploration.py — IC / forward returns / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成ロジック
    - signal_generator.py — シグナル生成ロジック
  - execution/  — 発注/ブローカー連携用（プレースホルダ）
  - monitoring/ — 監視用（プレースホルダ）

運用・デプロイのヒント
- 本番では KABUSYS_ENV=live を設定し、ログレベルや外部サービスのエンドポイントを適切に構成してください。
- DuckDB ファイルは定期的にバックアップしてください（データの一元管理）。
- ETL はスケジューラ（cron / Airflow / systemd timer 等）で夜間や営業日朝に実行するのが一般的です。
- 発注周り（kabu API など）はリスク制御と冪等キー周りを厳格に実装してから有効化してください。

貢献とコードスタイル
- 機能追加・バグ修正は Pull Request を歓迎します。自動テスト・型チェックを追加するとマージがスムーズになります。
- ドキュメント（README / DataPlatform.md / StrategyModel.md 等）に合わせて実装を整合させてください。

ライセンス
- プロジェクトルートの LICENSE を参照してください（存在する場合）。

――――――――――――
不明点や README に追記してほしい具体的な例（CI 設定、Docker イメージ例、詳細な .env.example など）があれば教えてください。必要に応じてサンプルスクリプトも作成します。