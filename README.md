# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ実装）

このリポジトリは、データ収集（J-Quants）、ETL、データ品質チェック、特徴量生成、研究用ファクター計算、ニュース収集、監査ログなどの基盤機能を含むライブラリ群を提供します。実際の発注・ブローカー接続部分はレイヤーとして用意されています（execution/strategy モジュールなど）が、プロジェクト内の多くのモジュールは本番口座や発注 API にアクセスしない設計になっています（Research/Data 層は読み取り専用）。

---

## 主な特徴

- 環境変数管理
  - プロジェクトルートの `.env` / `.env.local` を自動ロード（必要に応じて無効化可）。
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN 等）。
- データ取得（J-Quants）
  - 日足（OHLCV）、四半期財務データ、JPXマーケットカレンダーの取得（ページネーション対応）。
  - レート制限遵守、リトライ、トークン自動リフレッシュ。
  - DuckDB への冪等的保存（ON CONFLICT / DO UPDATE）。
- ニュース収集
  - RSS フィード取得（SSRF対策、gzip制限、XMLパースの安全化）。
  - URL 正規化・トラッキングパラメータ除去、記事IDは正規化URLのSHA-256先頭32文字。
  - DuckDB への冪等的保存と銘柄コード抽出。
- データベーススキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化ユーティリティ。
  - 監査ログ（signal / order_request / executions）テーブル用の初期化機能。
- ETL パイプライン
  - 差分更新（最終取得日ベース + バックフィル）、市場カレンダー先読み、品質チェック統合。
  - ETL 実行結果を ETLResult に集約。
- データ品質チェック
  - 欠損・重複・スパイク（前日比閾値）・将来日付/非営業日データ検出。
  - 各チェックは QualityIssue を返す（error / warning）。
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB の prices_daily / raw_financials のみ参照）。
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Zスコア正規化。
  - 研究モジュールは本番発注 API にはアクセスしない設計。
- 軽量な依存（urllib を利用）で外部 HTTP クライアントに依存しない実装（ただし DuckDB・defusedxml などは必要）。

---

## 必要条件

- Python 3.10 以上（ファイル内で `X | Y` 型記法を使用しているため）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクト配布時は pyproject.toml / requirements.txt を利用してください）

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存インストール
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を用意します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
     - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化（最初に一度実行）
   Python REPL やスクリプトで:
   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   # またはメモリDBで試す場合:
   # conn = schema.init_schema(":memory:")
   ```

---

## 使い方（主なユースケース例）

以下はライブラリ呼び出しの代表例です。（アプリケーションとして起動する CLI は本コードベースに含まれていません）

- ETL（日次）を実行する:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection
  from kabusys.config import settings
  from datetime import date

  conn = get_connection(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())  # ETLResult を返す
  print(result.to_dict())
  ```

- J-Quants から日足を直接取得（テストや局所取得）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  from kabusys.data.jquants_client import get_id_token

  token = get_id_token()  # settings.jquants_refresh_token を利用
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,12,31))
  ```

- ニュース収集ジョブを実行する:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄一覧のセット（銘柄紐付けに使う）
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 研究用ファクター計算（例: モメンタム）:
  ```python
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  d = date(2025, 1, 15)
  momentum = calc_momentum(conn, d)
  fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  # Zスコア正規化
  normalized = zscore_normalize(momentum, ["mom_1m", "ma200_dev"])
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意: research モジュール・data モジュールは原則として prices_daily / raw_financials 等のみを参照し、発注 API にはアクセスしない設計です。実際の発注処理を組み合わせる際は execution レイヤーや外部ブローカーライブラリを実装してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション等の API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

.env の自動読み込み仕様:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` の設定を上書きします。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用など）。

---

## ディレクトリ構成（主要ファイルの一覧）

src/kabusys/
- __init__.py (パッケージエクスポート)
- config.py — 環境変数・設定管理（.env 自動ロード、必須チェック、設定プロパティ）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS 取得・前処理・保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義・初期化
  - stats.py — 統計ユーティリティ（z-score 等）
  - pipeline.py — ETL パイプライン（差分更新・品質チェック統合）
  - features.py — features の公開インターフェース（再エクスポート）
  - calendar_management.py — 市場カレンダー管理ユーティリティ
  - audit.py — 監査ログ（signal/order_request/executions）DDL と初期化
  - etl.py — ETL の公開型再エクスポート
  - quality.py — データ品質チェック
- research/
  - __init__.py — 研究 API のエクスポート
  - factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算
  - feature_exploration.py — 将来リターン計算・IC 計算・統計サマリー
- strategy/ (空のパッケージ初期化ファイル)
- execution/ (空のパッケージ初期化ファイル)
- monitoring/ (空のパッケージ初期化ファイル)

---

## 開発・テストに関する注意

- 型記法および一部標準ライブラリの挙動により Python 3.10 以上を想定しています。
- 自動環境変数ロードはテストで邪魔になる場合があるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- DuckDB を使っているため、ローカル開発ではファイルパス（デフォルト: data/kabusys.duckdb）を確認してください。
- HTTP 取得周りは urllib を利用しており、SSRF や Gzip Bomb 等に対する防護（レスポンス上限・リダイレクト検証・defusedxml）が施されていますが、外部公開環境での運用時には更なるセキュリティ・監査を推奨します。

---

必要であれば以下を追加で作成できます:
- CLI ラッパー（ETL 定期実行、calendar update job、news collection job）
- execution / broker ラッパー（kabuステーション等への安全な接続）
- サンプル .env.example / pyproject.toml / requirements.txt

ご希望があれば README にサンプル .env.example や具体的な CLI 実行例、起動スクリプトのテンプレートを追記します。