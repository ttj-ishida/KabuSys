KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ群（調査・データ基盤・特徴量生成・
シグナル生成・ETL・監査など）。DuckDB を中核 DB として、J-Quants API や RSS ニュースを取
り込み、戦略用特徴量（features）・AI スコア（ai_scores）・シグナル（signals）を生成・保
存します。

主な目的
- 市場データ（OHLCV / 財務 / カレンダー）を差分取得して DuckDB に蓄積
- 研究で作成した生ファクターを正規化して features を構築
- features と AI スコアを統合して売買シグナルを生成（BUY/SELL）
- RSS からニュースを収集・記事と銘柄紐付けを行う
- 発注／約定／ポジション管理のためのスキーマと監査ログを提供

機能一覧
- 環境変数・設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で設定を取得
- データ取得・保存（J-Quants クライアント）
  - 日足（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション対応）
  - レート制限、リトライ、トークン自動リフレッシュ、取得時刻（fetched_at）の記録
  - DuckDB への冪等保存（ON CONFLICT / upsert）
- ETL パイプライン
  - 差分取得／バックフィル／品質チェックを含む日次 ETL run_daily_etl
  - calendar / prices / financials 個別ジョブ
- データスキーマ初期化
  - DuckDB スキーマを一括作成（Raw / Processed / Feature / Execution 層）
  - init_schema(), get_connection()
- 研究用ファクター計算
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - 研究用の前処理・探索ユーティリティ（forward returns / IC / summary）
- 特徴量エンジニアリング
  - build_features: 生ファクターをマージ → ユニバースフィルタ → Z スコア正規化 → features へ UPSERT
- シグナル生成
  - generate_signals: features + ai_scores を統合して final_score を算出し BUY/SELL を生成、signals テーブルへ保存
  - Bear レジーム抑制、エグジット（stop loss / score drop）判定
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 制限、XML 脆弱性対策）
  - raw_news / news_symbols への冪等保存、銘柄抽出（4桁コード）
- 統計ユーティリティ
  - zscore_normalize、rank、IC、factor_summary など
- 監査ログ
  - signal_events / order_requests / executions 等の監査テーブル定義（トレーサビリティ）

セットアップ手順（開発環境）
- 前提
  - Python 3.9+（typing の一部を利用）
  - DuckDB（Python パッケージ duckdb）
  - defusedxml（RSS パース保護）
  - その他標準ライブラリのみで多くの処理を実装

1) リポジトリをクローンしてパッケージをインストール
   git clone <repo>
   cd <repo>
   pip install -e .  # setuptools / poetry 等のプロジェクト設定に合わせてください

2) 必要パッケージをインストール（例）
   pip install duckdb defusedxml

3) 環境変数を設定
   プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に .env または .env.local を置くと自動読み込みされます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数（必須）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション等の API パスワード（発注関連）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot token
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用途の SQLite パス（デフォルト data/monitoring.db）

   .env の例（.env.example として保存）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

使い方（簡易サンプル）
- スキーマ初期化（DuckDB ファイル作成）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  # またはインメモリ:
  # conn = init_schema(":memory:")

- 日次 ETL を実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 特徴量のビルド（target_date は datetime.date）
  from datetime import date
  from kabusys.strategy import build_features
  n = build_features(conn, date(2026, 1, 10))
  print(f"features upserted: {n}")

- シグナル生成
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, date(2026, 1, 10))
  print(f"signals generated: {total}")

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 有効な銘柄コードセット（抽出に使用）
  results = run_news_collection(conn, known_codes={"7203","6758"})
  print(results)

- DuckDB 接続取得（既存 DB）
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")

- 設定参照
  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)

注意点／運用メモ
- 自動 .env ロードはプロジェクトルート（.git や pyproject.toml）を基準に行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- J-Quants API はレート制限を遵守しています（デフォルト 120 req/min）。大量の取得は時間を要します。
- DuckDB スキーマは init_schema() で一括作成されます。既存テーブルは上書きされずスキップされるため冪等です。
- features / signals などは「date 単位」で古いデータを削除してから挿入する方式（置換）を採用し、日次処理の冪等性を担保しています。
- ニュース収集は SS RF や XML 攻撃、巨大レスポンスに対する防御を組み込んでいますが、外部フィードの信頼性は運用次第です。
- 本ライブラリは発注 API（kabu ステーションなど）への実際の送信ロジックを execution 層へ持たない設計になっています。発注は別モジュール（execution 層）で実装・統合してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     - 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            - J-Quants API クライアント（取得/保存）
    - news_collector.py            - RSS ニュース収集・保存・紐付け
    - pipeline.py                  - ETL パイプライン（run_daily_etl 等）
    - schema.py                    - DuckDB スキーマ定義・初期化
    - stats.py                     - 統計ユーティリティ（zscore_normalize）
    - features.py                  - features 用公開ラッパー
    - calendar_management.py       - 市場カレンダー管理
    - audit.py                     - 監査ログ用スキーマ
  - research/
    - __init__.py
    - factor_research.py           - momentum/volatility/value 計算
    - feature_exploration.py       - forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       - build_features
    - signal_generator.py          - generate_signals
  - execution/                      - （発注実装のためのプレースホルダ）
  - monitoring/                     - 監視用 DB / ロジック（別途実装想定）

テスト / 開発
- 単体機能は DuckDB のインメモリ DB（":memory:"）でテスト可能です。
- jquants_client のネットワーク呼び出しは、テスト時に _request や _urlopen をモックして検証してください。
- news_collector._urlopen を差し替えれば HTTP 実装をモックできます。

ライセンス / 貢献
- この README はコードベースから自動生成的に作成しています。実運用に使う場合は README にプロジェクト固有のライセンス、貢献ガイドを追記してください。

以上。必要であれば、README に具体的なコマンド例（systemd / cron ジョブ例、Slack 通知の例、テーブルスキーマの ER 図など）を追記します。どの情報が欲しいか教えてください。