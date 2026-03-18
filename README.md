# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータ層に用い、J-Quants API などからデータを収集・整形し、特徴量算出、品質チェック、ニュース収集、監査ログなどを備えた設計になっています。

---

## 主な特徴（overview / 機能一覧）

- データ収集（ETL）
  - J-Quants API から株価日足、財務データ、マーケットカレンダーを差分取得（ページネーション対応）
  - レート制限遵守・リトライ・トークン自動リフレッシュ実装
- データ保存（DuckDB）
  - Raw / Processed / Feature / Execution の多層スキーマを提供（冪等保存を考慮した INSERT ... ON CONFLICT）
  - 監査ログ（signal / order_request / execution）用スキーマを別途初期化可能
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などのチェックを実行
- ニュース収集
  - RSS フィード収集、前処理、ID 生成、記事 → 銘柄紐付け（安全対策：SSRF対策・サイズ制限・defusedxml）
- 研究用ユーティリティ（Research）
  - Momentum / Volatility / Value といったファクター算出
  - 将来リターン計算、IC（Spearman）算出、統計要約、Z-score 正規化
- その他ユーティリティ
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - ETL の統合実行（run_daily_etl）と結果オブジェクト（ETLResult）

---

## 要件（Dependencies）

主なランタイム依存（例）:
- Python 3.9+
- duckdb
- defusedxml

プロジェクトのインストール方法に合わせて requirements を用意してください。開発ルールや追加パッケージ（例えば requests 等）は用途に応じて導入します。

---

## 環境変数 / 設定

自動でプロジェクトルートの .env と .env.local を読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須は値取得時にエラーになります）:

- J-Quants / データ系
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- 発注 / kabuステーション
  - KABU_API_PASSWORD — kabu API のパスワード（必須）
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- Slack（通知用）
  - SLACK_BOT_TOKEN — Slack Bot トークン（必須）
  - SLACK_CHANNEL_ID — 通知先チャンネル ID（必須）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視データ用 SQLite パス（デフォルト: data/monitoring.db）
- 実行モード / ログ
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

設定値取得は kabusys.config.settings を通じて行います（例: settings.jquants_refresh_token）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate など

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて他パッケージを追加）

3. .env を準備
   - プロジェクトルートに .env（または .env.local）を置く
   - 最低限必要なキーを設定（例）:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     - from kabusys.data.schema import init_schema
     - from kabusys.config import settings
     - conn = init_schema(settings.duckdb_path)

5. 監査ログ用 DB（任意）
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要 API 簡易サンプル）

以下は代表的な利用例です。実際の運用ではログ出力や例外ハンドリングを適切に行ってください。

- DuckDB スキーマ初期化（上記と同様）:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行:
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # デフォルトで today を対象に ETL を実行
  - print(result.to_dict())

- 個別 ETL（株価のみ差分取得）:
  - from kabusys.data.pipeline import run_prices_etl
  - fetched, saved = run_prices_etl(conn, target_date=date(2026, 1, 1))

- J-Quants からデータ取得（低レベル）:
  - from kabusys.data.jquants_client import fetch_daily_quotes
  - records = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))

- ニュース収集ジョブ実行:
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})

- 研究・特徴量計算（Research）:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  - momentum = calc_momentum(conn, target_date=date(2026, 1, 1))
  - vol = calc_volatility(conn, target_date=date(2026, 1, 1))
  - value = calc_value(conn, target_date=date(2026, 1, 1))
  - fwd = calc_forward_returns(conn, target_date=date(2026, 1, 1))
  - ic = calc_ic(factor_records=momentum, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
  - summary = factor_summary(momentum, ["mom_1m","ma200_dev"])
  - normalized = zscore_normalize(momentum, ["mom_1m","mom_3m","mom_6m"])

- カレンダー関連ユーティリティ:
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  - is_open = is_trading_day(conn, date(2026,1,1))

---

## 注意事項・設計上のポイント

- 環境変数自動読み込み
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml の位置）から自動的に読み込みます。
  - テストなどで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- J-Quants クライアント
  - レート制限（120 req/min）に合わせた RateLimiter を備えています。
  - 408/429/5xx に対するリトライ（最大3回）、401 受信時は ID トークンを自動リフレッシュして再試行します。
  - データ取得時に fetched_at を UTC で記録し、Look-ahead バイアスの検出に備えます。

- News Collector（RSS）
  - SSRF 対策（リダイレクト検証、プライベートIP拒否）、Content-Length/受信サイズ制限、gzip 上限検査など安全性に配慮した実装です。
  - 記事IDは正規化 URL の SHA-256 の先頭 32 文字で生成し IDempotency を確保します。

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution を分離した多層アーキテクチャ。
  - ON CONFLICT DO UPDATE / DO NOTHING を活用して冪等性を保っています。
  - 監査テーブル（signal_events / order_requests / executions）を別途初期化可能です。

- 品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合を SQLベースで検出し、QualityIssue のリストで返します。
  - ETL は Fail-Fast ではなく、すべてのチェックを実行して問題の一覧を返す設計です。呼び出し側で対応を判断してください。

---

## ディレクトリ構成（プロジェクト内の主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
- config.py — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存）
  - news_collector.py — RSS 収集 / 保存 / 銘柄抽出
  - schema.py — DuckDB スキーマ初期化 / 接続
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL 結果型の再エクスポート
  - features.py — 特徴量ユーティリティの公開インターフェース
  - stats.py — Z-score 正規化等の統計ユーティリティ
  - calendar_management.py — マーケットカレンダー管理・判定
  - audit.py — 監査ログスキーマ初期化
  - quality.py — データ品質チェック
- research/
  - __init__.py — 研究用関数のエクスポート（calc_momentum 等）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - factor_research.py — Momentum / Volatility / Value の計算
- strategy/ — 戦略層（未実装ファイル群のため拡張箇所）
- execution/ — 発注実装領域（未実装のため拡張箇所）
- monitoring/ — 監視系（未実装のため拡張箇所）

---

## 開発メモ / 拡張ポイント

- 発注（execution）・戦略（strategy）層は抽象化されており、実際のブローカー接続やアルゴリズム実装はここから拡張する想定です。
- research モジュールは標準ライブラリベースで書かれており、Pandas などに依存させていないため小規模環境でも動きますが、大量データ分析時は外部ライブラリ導入を検討してください。
- 監査ログは別 DB として分離可能（init_audit_db）。運用での追跡性を重視する場合は必ず有効にしてください。

---

必要があれば、README に含める具体的な .env.example、docker-compose による DuckDB/周辺サービス構成、または具体的な CLI / systemd / Airflow ジョブ例なども追記できます。どの情報を優先して追加しますか？