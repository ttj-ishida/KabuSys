# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（データ取得・ETL、特徴量生成、監査・品質検査、ニュース収集、リサーチユーティリティ等）。

このリポジトリは以下の目的を想定しています：
- J-Quants API からの市場データ取得と DuckDB への永続化（冪等保存）
- 市場カレンダー管理、差分 ETL、品質チェック
- ファクター（モメンタム / ボラティリティ / バリュー 等）計算・探索（Research）
- ニュース（RSS）収集と銘柄紐付け
- 発注・監査用スキーマ（監査ログ）整備

---

## 主な機能（抜粋）

- 環境/設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示的取得（設定オブジェクト `settings`）

- データ取得 / ETL
  - J-Quants API クライアント（ページネーション / レート制御 / リトライ / トークン自動リフレッシュ）
  - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - 差分 ETL（株価・財務・カレンダー）、日次 ETL エントリポイント
  - データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）

- ニュース収集
  - RSS 取得と前処理（URL 正規化、SSRF 対策、gzip 制限、XML 安全パース）
  - raw_news 保存、記事ID（正規化URL→SHA-256）による冪等保存
  - 銘柄コード抽出と news_symbols への紐付け

- リサーチ / 特徴量
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計要約
  - z-score 正規化ユーティリティ

- 監査・発注スキーマ
  - signal / order_request / executions 等の監査テーブル定義と初期化ユーティリティ

---

## 動作要件

- Python 3.10+
  - 型注釈で | 合成型（PEP 604）を使用しているため Python 3.10 以上を推奨します。
- 必要ライブラリ（例）
  - duckdb
  - defusedxml
- （任意）その他ライブラリは用途に応じて追加してください。

インストール例：
```bash
python -m pip install "duckdb" "defusedxml"
# あるいはプロジェクト用 requirements.txt を用意して pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン / 開発環境に配置

2. Python 環境構築（仮想環境推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` や `.env.local` を置くと自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1`で無効化可）。
   - 主に必要な環境変数（一例）：
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
     - LOG_LEVEL: ログレベル ("DEBUG","INFO",...、デフォルト: INFO)

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから初期化できます。
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ファイルがなければディレクトリ作成して初期化
   ```

5. 監査ログ専用 DB 初期化（必要に応じて）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な例）

- 日次 ETL（市場カレンダー・株価・財務の差分取得と品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行（既知銘柄コードセットを渡して自動紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- リサーチ / ファクター計算例
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  today = date(2025, 1, 31)

  mom = calc_momentum(conn, today)
  vol = calc_volatility(conn, today)
  val = calc_value(conn, today)

  fwd = calc_forward_returns(conn, today, horizons=[1,5,21])
  # 例: mom と fwd を突合して IC を計算
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)

  summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- J-Quants API からデータを直接取得（ページネーション / 自動トークン処理あり）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar

  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  fins = fetch_financial_statements(date_from=date(2023,1,1))
  calendar = fetch_market_calendar()
  ```

---

## 設定 / 環境変数の要点

- 自動 .env 読み込み
  - プロジェクト内（__file__ から親方向）に `.git` または `pyproject.toml` を検出してルートを特定し、`.env` → `.env.local` の順で読み込みます。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。

- 重要な必須変数（不足時は ValueError）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

- KABUSYS_ENV
  - 許容値: "development", "paper_trading", "live"
  - settings.is_live / is_paper / is_dev で判定可能

- ログレベル
  - LOG_LEVEL に "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" を設定

---

## ディレクトリ構成（主なファイル）

（ルート: src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py        — RSS 収集・前処理・保存ロジック
    - schema.py                — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                 — z-score 等の統計ユーティリティ
    - features.py              — 特徴量公開インターフェース（zscore 再エクスポート）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — market_calendar 管理 / 営業日判定 / 更新ジョブ
    - audit.py                 — 監査ログテーブル定義と初期化ユーティリティ
    - etl.py                   — ETL 用公開 API（ETLResult の再エクスポート）
    - quality.py               — データ品質チェック
  - research/
    - __init__.py (calc_momentum 等を再エクスポート)
    - feature_exploration.py   — 将来リターン、IC、ファクター統計
    - factor_research.py       — モメンタム / ボラティリティ / バリュー等の計算
  - strategy/                  — 戦略関連（未実装ファイルのプレースホルダあり）
  - execution/                 — 発注/実行関連（未実装ファイルのプレースホルダあり）
  - monitoring/                — 監視/メトリクス（未実装）

---

## 開発上の注意点 / 実運用への留意点

- 実際に発注を行う機能（証券会社 API を叩く実装）はこのコードベースでは含まれていないか限定的です。運用前に十分なレビューとテストを行ってください。
- DuckDB の SQL 実行はパラメータバインド(?) を利用しており、SQL インジェクション対策は考慮されていますが、外部から渡す値の整合性は常に確認してください。
- J-Quants API のレート制限（120 req/min）を尊重する実装（固定間隔スロットリング）を行っていますが、実環境での負荷・スケジュールに合わせて調整してください。
- ニュース収集は外部 URL を扱うため SSRF 対策・レスポンスサイズ制限・XML の安全パースを実装していますが、運用環境ではさらに監視・制限を行うことを推奨します。
- テスト・CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、環境変数注入を明示的に行うと再現性が高くなります。

---

## 参考（よく使う関数 / モジュール）

- 設定: kabusys.config.settings
- DB スキーマ初期化: kabusys.data.schema.init_schema(db_path)
- 日次 ETL: kabusys.data.pipeline.run_daily_etl(...)
- J-Quants 取得: kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- ニュース: kabusys.data.news_collector.run_news_collection
- ファクター計算: kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- 統計ユーティリティ: kabusys.data.stats.zscore_normalize

---

README はここまでです。必要であれば以下を追加できます：
- さらに具体的な実行スクリプト（cron / Airflow / GitHub Actions 用例）
- テストの実行方法・カバレッジ
- 詳細な API 使用例（J-Quants のレスポンスサンプルに対する保存フロー）
- デプロイ / 運用ガイド（ログ・監視・アラート設計）

どの追加情報が必要か教えてください。