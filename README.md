# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集、品質チェック、ファクター計算など、戦略開発から実運用に必要な基盤機能を提供します。

---

## 主な特徴（機能一覧）

- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（必要に応じて無効化可能）
  - 必須設定取得時に未設定でエラーを出すユーティリティ

- データ取得（J-Quants API）
  - 日足（OHLCV）、財務データ、JPX カレンダーを取得
  - レート制限（120 req/min）を守る RateLimiter、リトライ・トークン自動リフレッシュ対応
  - 取得データを DuckDB に冪等保存する save_* 関数

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化用 `init_schema()`、接続取得用 `get_connection()`

- ETL パイプライン
  - 差分取得（最終取得日に基づく差分更新 + バックフィル）
  - カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次ETL をまとめて実行する `run_daily_etl()`（ETLResult を返す）

- ニュース収集
  - RSS フィードの安全な取得（SSRF/リダイレクト対策、gzip 上限、XML 攻撃対策）
  - 記事正規化・トラッキング除去・SHA256 ベースの冪等 ID 生成
  - raw_news / news_symbols への冪等保存と銘柄抽出

- データ品質チェック
  - 欠損・スパイク（前日比閾値）・重複・日付不整合の検出
  - チェック結果は QualityIssue 型のリストで返却

- 研究用ファクター計算
  - Momentum / Volatility / Value のファクター計算（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z-score 正規化

- 監査ログ（Audit）
  - シグナル → 発注 → 約定 に至るトレーサビリティ用スキーマを提供
  - 監査用 DB 初期化関数（UTC 固定、トランザクション対応）

---

## 要件・依存パッケージ

- Python 3.10 以上（型注釈の union 演算子 (|) 等を使用）
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml

（セットアップで pip によるインストール手順を示します）

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリへ配置

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements ファイルがあればそれを使ってください）

4. 環境変数の設定
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成します。
   - 利用される主な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
     - SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 開発/ペーパー/本番（development / paper_trading / live）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   - .env の例:
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

   - 自動 env ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベースの初期化
   - DuckDB スキーマを作成:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログ用 DB を別途初期化する場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡易サンプル）

- DuckDB スキーマの初期化（1回実行）

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants から差分取得して保存・品質チェックまで）

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  # conn は init_schema の戻り値
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース収集ジョブ（RSS から収集して保存、既知銘柄と紐付け）

  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードの set（例: {"7203", "6758"}）
  summary = run_news_collection(conn, known_codes=known_codes)
  print(summary)

- 研究用ファクター計算例

  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary
  from datetime import date
  momentum = calc_momentum(conn, target_date=date(2024, 1, 31))
  forward = calc_forward_returns(conn, target_date=date(2024, 1, 31))
  ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
  summary = factor_summary(momentum, ["mom_1m", "mom_3m", "ma200_dev"])

- データ品質チェックの単体実行

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)

- J-Quants API の直接利用（低レベル）

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)

---

## 重要な設計上の注意点 / 運用メモ

- 自動で .env を読み込む際、OS 環境変数が優先されます。テストで自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しは内部でレート制御とリトライを行いますが、過度の同時並列呼び出しは避けてください。
- DuckDB に対する DDL は一部トランザクション内で実行されますが、関数によってはトランザクション管理の違いがあるため、アプリケーション側で適切にトランザクション境界を管理してください。
- news_collector は外部 RSS を取得します。SSRF や大容量レスポンス対策が組み込まれていますが、運用時のソース管理（信頼できる RSS の指定）は重要です。
- audit スキーマは UTC タイムスタンプを前提としています。タイムゾーン取り扱いに注意してください。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン情報
  - config.py — 環境変数 / 設定管理（自動 .env ロード / 必須設定チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・ページネーション・保存）
    - news_collector.py — RSS ニュース取得・前処理・DB 保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema()
    - pipeline.py — ETL パイプライン（差分取得 / 保存 / 品質チェック / run_daily_etl）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 統計ユーティリティ（zscore_normalize など）
    - features.py — 公開インターフェース（zscore_normalize の再エクスポート）
    - calendar_management.py — 市場カレンダー管理（営業日判定、calendar_update_job）
    - audit.py — 監査ログ用スキーマ初期化（signal_events / order_requests / executions）
    - etl.py — ETLResult 型の再エクスポート
    - pipeline.py — ETL 実装（上記）
  - research/
    - __init__.py — 研究用 API のエクスポート
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
    - factor_research.py — Momentum / Volatility / Value ファクター計算
  - strategy/ — 戦略層（パッケージ化済み、詳細は実装側で追加）
  - execution/ — 発注・執行周り（パッケージ化済み、詳細は実装側で追加）
  - monitoring/ — 監視・メトリクス（パッケージ化済み、詳細は実装側で追加）

---

## 開発・拡張のヒント

- research モジュールは DuckDB の prices_daily / raw_financials を参照することを前提に設計されています。新しいファクターを追加する場合は同様に DuckDB 接続を引数に取り、(date, code) 単位の dict リストを返す形に統一すると他モジュールと連携しやすくなります。
- jquants_client の _request は標準 urllib を使用しています。必要であればタイムアウトやプロキシの指定、メトリクス収集のフックを追加してください。
- ETL の品質チェックは Fail-Fast ではなく問題を収集して返却する設計です。運用では結果（ETLResult）を監視してアラートを上げる仕組みを導入してください。

---

もし README に追加したい実行例、CI / Docker の設定例、あるいは特定機能の詳細説明（例: audit の使い方、news_collector の既知問題・制約など）があれば教えてください。必要に応じてサンプルコード・運用手順を追記します。