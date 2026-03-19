# KabuSys

日本株向け自動売買 / データ基盤ライブラリ KabuSys の README。

このリポジトリは、データ取得（J-Quants）、DuckDB によるデータ格納・スキーマ管理、ETL パイプライン、ニュース収集、研究用ファクター計算、監査ログなどを含む日本株向けのシステム基盤コンポーネント群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と記事 → 銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用のファクター計算（モメンタム / ボラティリティ / バリュー等）と特徴量正規化
- 監査用スキーマ（シグナル → 発注 → 約定のトレーサビリティ）
- 設定管理（.env 自動ロード、環境別設定）

設計上のポイント：
- DuckDB を主要な永続層として使用（軽量で高速な列指向 DB）
- API レート制限・リトライ・トークンリフレッシュ等を考慮した J-Quants クライアント
- 外部ライブラリに頼らない純 Python 実装（ただし DuckDB・defusedxml 等の最小依存あり）
- 冪等性（ON CONFLICT / INSERT ... DO UPDATE / RETURNING を活用）

---

## 主な機能一覧

- 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得（例: JQUANTS_REFRESH_TOKEN）
  - 環境（development / paper_trading / live）・ログレベル検証

- データ取得 / 保存（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) による初期化

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの取得）、backfill、カレンダー先読み
  - run_daily_etl で統合 ETL（品質チェックオプション付き）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得 / 前処理（URL 除去・正規化） / DuckDB へ冪等保存
  - 銘柄コード抽出（4桁コード）と news_symbols への紐付け
  - SSRF 対策・受信サイズ制限・XML デコード上の安全対策（defusedxml）

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付整合性チェック
  - QualityIssue オブジェクトで結果を返却

- 研究用ファクター計算（kabusys.research）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）でクロスセクション正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ

---

## セットアップ手順

前提
- Python 3.10+（typing の一部で | 型注釈を使用）
- DuckDB を利用するため、該当ライブラリをインストールする

1. 仮想環境を作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. パッケージのインストール（必要最小限）
   - 必須: duckdb, defusedxml
   - 開発: logging 等は標準ライブラリ

   例:
   ```bash
   pip install duckdb defusedxml
   ```

   （プロジェクトに setup.cfg / pyproject.toml があれば editable install を利用）
   ```bash
   pip install -e .
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（kabusys.config）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な環境変数（主要）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: 通知対象チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマの初期化
   - Python REPL やスクリプトから実行します。

   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

   監査ログ専用 DB を作成する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方 / 主要な操作例

以下は代表的な利用例です。実運用ではこれらをラッパースクリプト（cron / Airflow / job runner）から呼び出します。

- ETL（日次）を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 初回のみ実行
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を渡すとテキストから銘柄抽出して news_symbols に紐付ける
  known_codes = {"7203", "6758", "9984"}
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: saved_count, ...}
  ```

- 研究用ファクター計算を行う
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2024, 2, 28)
  mom = calc_momentum(conn, t)
  vol = calc_volatility(conn, t)
  val = calc_value(conn, t)

  fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
  # 例: factor_records を作って IC を計算する
  # ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- データ品質チェックを実行する
  ```python
  from kabusys.data.quality import run_all_checks
  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

- J-Quants から直接データをフェッチして保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  print("saved:", saved)
  ```

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリの主要モジュールとファイル一覧（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - execution/ (発注関連の骨組み)
  - strategy/ (戦略関連の骨組み)
  - monitoring/ (モニタリング関連の骨組み)

- src/kabusys/data/
  - __init__.py
  - jquants_client.py        -- J-Quants API クライアント（取得・保存）
  - news_collector.py       -- RSS ニュース収集と保存
  - schema.py               -- DuckDB スキーマ定義・初期化
  - stats.py                -- zscore_normalize 等の統計ユーティリティ
  - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
  - features.py             -- features の公開インターフェース
  - calendar_management.py  -- market_calendar 管理ユーティリティ
  - audit.py                -- 監査ログスキーマと初期化
  - etl.py                  -- ETL 結果クラスの公開
  - quality.py              -- データ品質チェック

- src/kabusys/research/
  - __init__.py
  - feature_exploration.py  -- forward returns / IC / summary
  - factor_research.py      -- momentum / volatility / value の計算

---

## 注意事項 / トラブルシューティング

- 環境変数が不足していると Settings プロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。`.env.example` を参考に `.env` を作成してください。
- DuckDB ファイルパスの親ディレクトリが存在しない場合 init_schema が自動作成しますが、書き込み権限を確認してください。
- J-Quants API のレート制限を遵守する設計ですが、API キーや接続情報は適切に管理してください。
- RSS フィード取得では SSRF 対策・受信サイズ制限を実装しています。非標準フィードや大容量フィードは取得されない場合があります。
- unit test 用に環境自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 貢献 / 開発メモ

- すべての ETL / DB 操作は冪等性を念頭に設計しています（ON CONFLICT 等）。
- 研究用関数は DuckDB の prices_daily / raw_financials テーブルのみを参照します。本番の発注 API にはアクセスしません。
- 将来的な拡張点：戦略モジュール（strategy）や発注実行（execution）の具象実装、Slack 通知 / モニタリング連携、バックテストフレームワーク統合など。

---

必要であれば README を用途別（開発者向け / 運用向け / API リファレンス）に分割して詳細化できます。追加で含めたい例や CI / テスト手順があれば教えてください。