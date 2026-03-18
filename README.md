# KabuSys

日本株向け自動売買/データプラットフォーム用ライブラリセット（モジュール群）
このリポジトリは、J-Quants 等の外部データソースから市場データ・財務データ・ニュースを収集し、
DuckDB に保存、品質チェック・特徴量算出・戦略評価（リサーチ）・発注関連の基盤機能を提供します。

主な設計方針
- DuckDB を中心としたローカルデータレイク（Raw / Processed / Feature / Execution の多層スキーマ）
- J-Quants API のレート制限・リトライ・トークン自動リフレッシュ対応
- RSS ベースのニュース収集時に SSRF / Gzip bomb / XML 攻撃対策を実施
- ETL は差分更新 / バックフィルをサポートし、品質チェックを実行
- 本番口座・発注 API への直接アクセスを Research / Data モジュールでは行わない（安全設計）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env ファイルをプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）
  - 必須環境変数チェック（Settings）

- データ取得・保存（J-Quants クライアント）
  - 日次株価（OHLCV）取得（ページネーション対応、レート制御、リトライ、トークン自動更新）
  - 財務データ（四半期 BS/PL）取得
  - 市場カレンダー取得（JPX）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化（init_schema, init_audit_schema）
  - 冪等な INSERT（ON CONFLICT DO UPDATE/DO NOTHING）でデータの追記・更新

- ETL パイプライン
  - 差分 ETL（価格 / 財務 / カレンダー）
  - バックフィルにより API の後出し修正に対応
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集（RSS）
  - RSS フィード取得、記事正規化、ID 生成（URL 正規化→SHA256）、DuckDB への冪等保存
  - 銘柄コード抽出（本文から 4桁コード抽出と known_codes フィルタ）

- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー系ファクター算出（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン（forward returns）計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（Audit）
  - signal → order_request → executions のトレース用スキーマ、監査初期化ユーティリティ

- その他
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - 各所での堅牢なエラーハンドリングとログ出力

---

## 動作環境 / 前提

- Python 3.10 以上（型表記で | を使用）
- 必要なライブラリ（主なもの）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）
- J-Quants API の refresh token 等の環境変数設定

（環境ごとに requirements.txt を用意することを推奨します。最低限 pip install duckdb defusedxml を実行してください）

---

## セットアップ手順

1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトが pip 配布可能な場合は `pip install -e .` の想定も可）

3. .env を作成
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを抑止したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   最低限設定が必要な環境変数（README 用サンプル）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id

   任意/デフォルトあり:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live; default=development)
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL; default=INFO)

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから以下を実行:

     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログ専用 DB を初期化する場合:

     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主な例）

以下は Python スクリプト/REPL での基本的な利用例です。

- settings の参照（環境変数から）
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)

- DuckDB スキーマの初期化（1回）
  from kabusys.data.schema import init_schema
  conn = init_schema(settings.duckdb_path)

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 個別 ETL（価格のみ等）
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  fetched, saved = run_prices_etl(conn, date.today())

- ニュース収集ジョブの実行
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（例）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)

- J-Quants からのデータ取得（直接）
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って取得
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

- リサーチ / ファクター計算
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  from datetime import date
  momentum = calc_momentum(conn, date.today())
  volatility = calc_volatility(conn, date.today())
  value = calc_value(conn, date.today())

  fwd = calc_forward_returns(conn, date.today())
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")

- Zスコア正規化
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(momentum, columns=["mom_1m", "ma200_dev"])

注意点
- run_daily_etl などは内部で複数の処理を呼び出します。各処理は独立して例外処理され、失敗しても他処理は継続しますが、戻り値の ETLResult.errors を確認してください。
- J-Quants クライアントはレート制限（120 req/min）や再試行、401 トークンリフレッシュを実装しています。多量のページネーションがある場合は十分な待ち時間を許容してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネルID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル（DEBUG/INFO/...）

自動読み込み無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化します（テスト時に便利）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境設定管理（.env 読み込み、Settings）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント、取得・保存ユーティリティ
  - news_collector.py — RSS ニュース収集・正規化・保存
  - schema.py — DuckDB スキーマ定義・初期化
  - stats.py — 統計ユーティリティ（zscore_normalize など）
  - pipeline.py — ETL パイプライン（差分取得・品質チェック）
  - features.py — features 用公開インターフェース（zscore export）
  - calendar_management.py — market_calendar 管理（営業日判定等）
  - audit.py — 監査ログスキーマ初期化
  - etl.py — ETL 型エクスポート（ETLResult）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
- research/
  - __init__.py — research 用 API エクスポート
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - factor_research.py — モメンタム / ボラティリティ / バリュー算出
- strategy/
  - __init__.py — 戦略モジュール置き場（実装は各戦略で）
- execution/
  - __init__.py — 発注／実行管理のエントリ（実装は別）
- monitoring/
  - __init__.py — 監視・メトリクス（プレースホルダ）

README に掲載されているコード群は、DataPlatform.md / StrategyModel.md 等の設計ドキュメントに沿って実装されています（リファレンス実装）。

---

## 開発上の注意 / セキュリティ

- RSS 取得では defusedxml を使用し XML Bomb を回避し、レスポンスサイズ上限を設けています。外部 URL のリダイレクト検査・プライベートIPブロックも実装済みです。
- J-Quants クライアントはレート制御と再試行ロジックを備えており、401 時に refresh token から id_token を自動的に更新します。
- DuckDB に対する INSERT は冪等性（ON CONFLICT）を重視しています。外部から DB を直接編集するケースではスキーマ制約に注意してください。
- 本番口座（実際の発注）を行う場合は監査ログ (audit) を必ず初期化し、order_request_id 等の冪等キー運用を行ってください。

---

## 今後の拡張案（参考）

- strategy / execution 層の具体的実装（kabu 発注ラッパ、リスク管理、ポジション管理）
- Slack / 通知ワークフローの統合（モニタリング）
- CI 用のテストスイート（DuckDB のインメモリ利用でユニットテスト化）
- より豊富な RSS ソースと NLP による記事分類 / sentiment スコア

---

ライセンス、貢献ルール、詳細な設計書（DataPlatform.md、StrategyModel.md など）が存在する場合はそちらも参照してください。必要であれば README の追加セクション（例: CLI、Docker、具体的な .env.example）を追記します。