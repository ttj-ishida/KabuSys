# KabuSys

KabuSys は日本株の自動売買・データ基盤を想定した Python ライブラリ群です。  
DuckDB ベースのデータレイク、J-Quants からのデータ取得、ニュース収集、品質チェック、ファクター計算、ETL パイプライン、監査ログなどを含むモジュール群を提供します。

---

## 主な特徴

- DuckDB を用いた三層（Raw / Processed / Feature）データスキーマ
- J-Quants API クライアント（レートリミット制御・リトライ・トークン自動リフレッシュ）
- 日足・財務・市場カレンダーの差分 ETL（backfill 対応）
- ニュース（RSS）収集器（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と IC / 統計サマリー
- 監査ログ（信号 → 発注 → 約定 のトレーサビリティ用スキーマ）
- 設定管理（.env / 環境変数の自動読み込み・保護機能）

注: research 関連モジュールは「読み取り専用」であり、本番発注 API にはアクセスしない設計です。

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）
  - サポート環境: development / paper_trading / live
- kabusys.data.jquants_client
  - J-Quants API との通信（fetch / save / pagination / retry / rate limit）
  - save_* 関数は DuckDB に対して冪等に保存（ON CONFLICT）
- kabusys.data.schema
  - DuckDB の DDL を定義、init_schema() による初期化
- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得・バックフィル対応
- kabusys.data.news_collector
  - RSS 取得（gzip 対応、SSRF 対策）
  - 記事正規化、ID 生成（URL 正規化→SHA-256 の先頭 32 文字）
  - raw_news / news_symbols への保存（チャンク・トランザクション）
- kabusys.data.quality
  - 欠損 / スパイク / 重複 / 日付不整合チェック
- kabusys.research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC 計算（calc_forward_returns, calc_ic）
  - zscore_normalize（data.stats から）
- kabusys.data.audit
  - 監査ログスキーマ（signal_events / order_requests / executions）
  - init_audit_db / init_audit_schema

---

## 必要条件・依存ライブラリ

- Python 3.10 以上（| 型アノテーション等を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- (任意) J-Quants API 使用時にネットワーク接続

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```
※ 実プロジェクトでは requirements.txt / pyproject.toml を用意してください。

---

## 環境変数（主要）

KabuSys は .env / .env.local を自動で読み込みます（プロジェクトルートに .git か pyproject.toml がある場合）。自動読み込みを止めるには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須（Settings._require を参照）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live、デフォルト development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成とパッケージのインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```

3. .env を作成（.env.example を参考に）
   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化（Python REPL またはスクリプト）
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")
   # 監査ログを追加で初期化する場合:
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要な操作）

- 日次 ETL 実行（市場カレンダー・日足・財務・品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  ```

- ニュース収集と保存
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  ```

- ファクター計算（例: モメンタム）
  ```python
  from kabusys.research import calc_momentum
  from datetime import date
  rows = calc_momentum(conn, target_date=date(2025,1,31))
  ```

- 将来リターン・IC 計算
  ```python
  from kabusys.research import calc_forward_returns, calc_ic, rank
  fwd = calc_forward_returns(conn, date(2025,1,31))
  # factor_records は別途 calc_momentum, calc_value 等の結果を用意
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- J-Quants から日足を直接取得（テスト用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - execution/                — 発注関連（空パッケージ）
  - strategy/                 — 戦略関連（空パッケージ）
  - monitoring/               — 監視関連（空パッケージ）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - news_collector.py       — RSS 収集 / 前処理 / DB 保存
    - schema.py               — DuckDB スキーマ定義 & init_schema
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - features.py             — features の公開インターフェース
    - calendar_management.py  — 市場カレンダー管理 / ジョブ
    - audit.py                — 監査ログスキーマの初期化
    - etl.py                  — ETL 公開インターフェース (ETLResult)
    - quality.py              — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py  — 将来リターン / IC / summary
    - factor_research.py      — モメンタム / ボラティリティ / バリュー
  - その他: strategy, execution, monitoring の骨格を提供

---

## 運用上の注意

- J-Quants API のレート制限（120 req/min）に注意。ライブラリは固定間隔スロットリングで制御しますが、大量取得時は調整してください。
- save_* 系関数は冪等性を考慮した実装（ON CONFLICT）です。複数回の ETL 実行で重複を防げます。
- news_collector は外部 URL を扱うため SSRF 対策・レスポンスサイズ制限などを実装しています。任意の RSS を追加する場合は信頼できるソースを選んでください。
- settings.jquants_refresh_token 等の機密情報は .env に保存し、リポジトリに含めないでください。
- DuckDB ファイル（デフォルト data/kabusys.duckdb）はアプリ運用で定期的にバックアップしてください。

---

## テスト / 開発ヒント

- 自動で .env を読み込む機能は単体テストで邪魔になることがあるため、テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- ETL の個別ステップ（run_prices_etl / run_financials_etl / run_calendar_etl）は単体で呼べるので、デバッグや部分更新に便利です。
- research モジュールは外部依存を避ける設計（標準ライブラリ + DuckDB）なので、ローカルの DuckDB を使った単体検証が容易です。

---

この README はコードの主要な機能と基本的な使い方をまとめたものです。詳細な API 仕様や運用手順は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば README にサンプルスクリプトや CI/CD、運用 runbook を追加できます。