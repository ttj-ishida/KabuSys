# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群

このリポジトリは、J-Quants などの外部データソースから市場データを収集・保存し、
DuckDB 上で前処理・特徴量計算・監査ログ・ETL パイプラインを提供する Python モジュール群です。
設計は本番運用（本番/ペーパー取引）を想定し、冪等性・レート制御・品質チェック・SSRF 対策などを重視しています。

バージョン: 0.1.0

---

## 主な機能

- データ収集（J-Quants API クライアント）
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得（ページネーション・リトライ対応）
  - レート制限（120 req/min）・ID トークン自動更新・指数バックオフ対応

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化（init_schema, init_audit_schema）
  - インデックス定義・テーブル作成順序の考慮

- ETL パイプライン
  - 差分更新・バックフィル制御・品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）でカレンダー→株価→財務→品質チェックを実行

- ニュース収集
  - RSS フィード取得（gzip 対応・XML パース防御）・URL 正規化・トラッキングパラメータ除去・記事ID生成（SHA-256）
  - raw_news / news_symbols への冪等保存、銘柄コード抽出

- 研究用ユーティリティ
  - ファクター計算（モメンタム・ボラティリティ・バリュー）と特徴量探索（将来リターン計算・IC・統計サマリー）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）

- 監査ログ（Audit）
  - signal_events / order_requests / executions など、監査に必要なテーブル群と初期化機能
  - UUID ベースのトレーサビリティ設計

---

## 必要な環境変数

主に以下の環境変数を参照します（settings から取得）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注系利用時）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知を使う場合）

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境 ("development", "paper_trading", "live")。デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO","...")。デフォルト "INFO"
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると自動で .env ロードを無効化
- KABUSYS_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）から `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 依存パッケージ（主要）

最低限必要なパッケージ（例）:
- duckdb
- defusedxml

インストール例:
- pip install duckdb defusedxml

（プロジェクトに requirements.txt や pyproject.toml があればそちらを使用してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （その他のユーティリティが必要な場合は追加でインストールしてください）

4. 環境変数を用意
   - プロジェクトルートに `.env` を作成し、必要な変数を設定
     例:
       JQUANTS_REFRESH_TOKEN=...
       KABU_API_PASSWORD=...
       SLACK_BOT_TOKEN=...
       SLACK_CHANNEL_ID=...
       DUCKDB_PATH=data/kabusys.duckdb

   - 自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自前で環境変数をセットしてください。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - 監査ログ専用 DB を初期化する場合:
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（主要な例）

- DuckDB スキーマ初期化
  - init_schema(db_path) を呼んでテーブルを作成し接続を取得します。

- 日次 ETL 実行例
  - from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl

    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

- ニュース収集（RSS）ジョブの実行例
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    from kabusys.data.schema import init_schema

    conn = init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コード集合
    stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
    print(stats)

- 研究用ファクター計算（例）
  - from datetime import date
    import duckdb
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

    conn = duckdb.connect("data/kabusys.duckdb")
    t = date(2025, 1, 31)
    mom = calc_momentum(conn, t)
    vol = calc_volatility(conn, t)
    val = calc_value(conn, t)
    fwd = calc_forward_returns(conn, t)
    ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
    summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])

- J-Quants API からの取得（低レベル）
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    data = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))

注意: J-Quants 呼び出しはレート制限や認証 (JQUANTS_REFRESH_TOKEN) に依存します。

---

## 重要な挙動・設計上の注意

- 冪等性
  - 多くの save_* 関数は ON CONFLICT DO UPDATE / DO NOTHING を使い、同一データの再挿入で破壊的更新を避けるように設計されています。

- レート制限と再試行
  - J-Quants クライアントは 120 req/min のレート制限に従い、固定間隔スロットリングと指数バックオフを実装。401 受信時はトークンを自動更新して一度リトライします。

- セキュリティ対策
  - RSS 取得は defusedxml を使用し XML BOM 等を防御、リダイレクト先のスキーム/プライベートアドレスを検査して SSRF を緩和します。
  - URL 正規化とトラッキングパラメータ除去により記事の冪等性を確保します。

- DuckDB 日付/タイムゾーン
  - 監査ログ初期化 (init_audit_schema) は接続に対して TimeZone を UTC に設定します。TIMESTAMP は運用方針に従って UTC で取り扱うことを推奨します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数のロード・Settings クラス（settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS 取得・前処理・DB 保存
    - schema.py — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - features.py — 特徴量ユーティリティの公開インターフェース
    - calendar_management.py — market_calendar 管理・営業日判定・calendar_update_job
    - audit.py — 監査ログテーブル定義と初期化
    - etl.py — ETLResult 再エクスポート
    - quality.py — 品質チェック（欠損・重複・スパイク・日付不整合）
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン・IC・factor_summary 等
    - factor_research.py — モメンタム・ボラティリティ・バリュー計算
  - strategy/
    - __init__.py
    - （戦略関連モジュールを配置）
  - execution/
    - __init__.py
    - （発注/実行関連モジュールを配置）
  - monitoring/
    - __init__.py
    - （外部監視/アラート関連）

---

## テスト・開発メモ

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索して `.env` と `.env.local` を読み込みます。
  - テスト中に自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB の in-memory モードを使うことで、テスト時にファイルを作成せず高速に schema を初期化できます。
  - init_schema(":memory:")

- ネットワーク呼び出し（J-Quants / RSS 等）は外部に依存するため、単体テストでは該当関数をモックすることを推奨します（例: news_collector._urlopen や jquants_client._request のモック）。

---

## 貢献

バグ報告、改善提案、プルリクエストを歓迎します。変更を加える際は、該当するモジュールの設計方針（冪等性・トレーサビリティ・UTC タイムスタンプなど）を尊重してください。

---

以上。ご不明点や README に追加したい利用例（CLI スクリプト・具体的な環境構築手順など）があれば教えてください。