# KabuSys

日本株向け自動売買・データプラットフォームライブラリ KabuSys (v0.1.0)

軽量な DuckDB ベースのデータプラットフォームと、J‑Quants API / RSS ニュース収集、研究用ファクター計算、ETL パイプライン、監査ログスキーマなどを提供するモジュール群です。プロダクションの発注処理を含む設計を想定しつつ、本番 API へ直接アクセスしない研究用関数も多数用意されています。

---

## 主な機能

- 環境変数 / 設定管理
  - .env/.env.local の自動読み込み（パッケージルート検出）と必須設定取得ユーティリティ
  - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ取得・保存（J-Quants 経由）
  - J‑Quants API クライアント（認証, ページネーション, レート制限, リトライ）
  - 株価日足、財務データ、JPX カレンダー取得関数
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL / データパイプライン
  - 差分取得（最終取得日からの差分）、バックフィル、カレンダー先読みなどを含む日次 ETL
  - 品質チェック（欠損・スパイク・重複・日付不整合検出）

- データスキーマ & 初期化
  - Raw / Processed / Feature / Execution / Audit 層を備えた DuckDB スキーマ定義
  - スキーマ初期化 utilities（init_schema, init_audit_db）

- ニュース収集
  - RSS フィード取り込み（SSRF / XML Bomb 対策、URL 正規化、記事ID生成）
  - raw_news / news_symbols への保存（冪等、チャンク挿入）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を引数に取る）
  - 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等、発注から約定までのトレーサビリティ用テーブル群
  - UTC タイムゾーン固定、冪等・監査要件を考慮した設計

---

## 必要環境

- Python 3.10 以上（型記法で | を使用）
- 必要主要ライブラリ（最低限）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt がある場合はそちらを利用してください。上記は本リポジトリコードから推定した最小依存です。）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます。
     - 自動ロードを無効にする場合:
       ```bash
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
       ```
   - 必須環境変数（Settings により _require_ されるもの）
     - JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — 通知先 Slack チャネル ID
   - 任意 / 既定値
     - KABUSYS_ENV — development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
     - KABU_API_BASE_URL — kabu ステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH / SQLITE_PATH — データベースファイルパス（デフォルトは data/ 以下）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB 可
     conn.close()
     ```

5. 監査用 DB 初期化（必要であれば）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   audit_conn.close()
   ```

---

## 使い方（代表例）

- 日次 ETL を実行する（J‑Quants から差分取得し DuckDB に保存）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（ファイルが既にあればスキップして接続を返す）
  conn = init_schema("data/kabusys.duckdb")

  # 日次 ETL（target_date を省略すると今日）
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- J‑Quants から日足を取得して保存する（個別）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- RSS ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使う有効な銘柄コードのセット（例: {"7203","6758",...}）
  res = run_news_collection(conn, known_codes={"7203","6758"})
  print(res)  # {source_name: 新規保存件数}
  ```

- 研究用ファクター計算の呼び出し例
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2025, 1, 31)
  mom = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  val = calc_value(conn, d)
  fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
  ```

- IC (Information Coefficient) の計算例
  ```python
  from kabusys.research import calc_ic
  ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- Zスコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normed = zscore_normalize(mom, ["mom_1m", "mom_3m"])
  ```

---

## 主要モジュールとディレクトリ構成

（src/kabusys 以下の主要ファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（必須設定の取得）
  - data/
    - __init__.py
    - jquants_client.py         — J‑Quants API クライアント（取得・保存）
    - news_collector.py         — RSS ニュース収集・保存
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - features.py               — feature 関連公開インターフェース
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py    — マーケットカレンダー管理ユーティリティ
    - audit.py                  — 監査ログ（order_requests 等）の初期化
    - etl.py                    — ETL 結果クラスの公開
    - quality.py                — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py    — 将来リターン / IC / サマリー等
    - factor_research.py        — momentum / volatility / value 等の計算
  - strategy/
    - __init__.py               — 戦略層用エクスポート（未実装の可能性あり）
  - execution/
    - __init__.py               — 発注実行層インターフェース（未実装の可能性あり）
  - monitoring/
    - __init__.py               — 監視 / メトリクス（プレースホルダ）

（トップレベル）
- src/                       — Python パッケージルート
- data/                      — デフォルトの DuckDB 等の保存先（例）

---

## 設計上の注意 / 運用メモ

- DuckDB の SQL 文でパラメータバインド（?）を使用しているため、SQL インジェクション等のリスクは低く抑えられていますが、ETL 実行時は適切な権限管理を行ってください。
- J‑Quants API のレート制限（120 req/min）は内部で固定間隔スロットリングにより保護しています。並列呼び出し時は注意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テストやカスタム環境で自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監査ログテーブルは UTC 保存が前提です（init_audit_schema は TimeZone を 'UTC' に固定します）。
- ファイル・テーブル作成は冪等に設計されています（init_schema 等は既存テーブルを上書きしません）。

---

## 参考（よく使う呼び出し）

- スキーマ初期化:
  - from kabusys.data.schema import init_schema
- ETL 実行:
  - from kabusys.data.pipeline import run_daily_etl
- J‑Quants 直接利用:
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
- ニュース収集:
  - from kabusys.data.news_collector import run_news_collection
- 研究用:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

---

何か特定の使用例（CI での自動 ETL、Docker 化、Slack 通知の実装例など）が必要であれば、その用途に合わせた README 拡張やサンプルスクリプトを作成します。どの部分を詳しく書くか教えてください。