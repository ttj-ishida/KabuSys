# KabuSys

日本株自動売買・データ基盤ライブラリ KabuSys の README（日本語）

概要、機能一覧、セットアップ手順、使い方（主要 API の利用例）、ディレクトリ構成を記載しています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集、ETL、特徴量生成、リサーチ（ファクター解析）、監査ログ、そして発注周りのスキーマ/ユーティリティを含む、取引システム向けの内部ライブラリ群です。主に以下の役割を持ちます。

- J-Quants API からのデータ取得（株価日足・財務データ・マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義・永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース RSS 収集と記事→銘柄紐付け（SSRF 等のセキュリティ対策付き）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と評価（IC など）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 開発 / ペーパー / 本番（live）モードの設定管理

設計方針としては「DuckDB を中心に SQL と純粋な Python（標準ライブラリ中心）で完結」「API 呼び出しはレート制限やリトライを備える」「ETL は冪等（ON CONFLICT）で実行できる」ことを重視しています。

---

## 主な機能一覧

- 環境変数設定管理（自動 .env ロード、必須キー取得）
- DuckDB スキーマの初期化（data.schema.init_schema）
- J-Quants クライアント（レート制御・リトライ・トークン自動更新）
- 日次 ETL（data.pipeline.run_daily_etl：calendar / prices / financials の差分取得）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ベースのニュース収集（SSRF/サイズ/GZIP チェック、記事ID のハッシュ化）
- ニュース→銘柄抽出（4桁コード抽出・既知銘柄フィルタ）
- ファクター計算（calc_momentum / calc_volatility / calc_value）
- 将来リターン計算・IC 計算（calc_forward_returns / calc_ic / rank）
- Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ用スキーマ（signal_events / order_requests / executions）
- ETL の結果を表す ETLResult 型（詳細な監査・ログ出力に利用可能）

---

## セットアップ手順

前提
- Python 3.9+（型注釈に | を使っているため Python 3.10 を想定するコードもありますが、互換性はコードベース次第）
- duckdb パッケージ
- （J-Quants 利用時）ネットワークアクセス
- （ニュース収集）インターネットアクセス

1. リポジトリをクローン／配置
   - 既にコードがある想定のため省略。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - その他プロジェクト固有の依存があれば requirements.txt に従ってください。

4. 環境変数（.env）を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（コード参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化（DuckDB）
   - Python REPL やスクリプトから実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB を作る場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要 API と実行例）

※ 以下は簡単な利用例です。実運用ではログ設定や例外処理、認証トークンの管理を適切に行ってください。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL の実行
   - ETL は市場カレンダー→株価→財務データ→品質チェックの順に実行します。
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定しないと今日を利用
   print(result.to_dict())
   ```

3. J-Quants から単体で取得する（例：株価日足）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = save_daily_quotes(conn, records)
   ```

4. ニュース収集ジョブの実行
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   known_codes = {"7203","6758", "6501"}  # 例: 有効な銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

5. ファクター計算・研究ユーティリティ
   ```python
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
   target = date(2024, 1, 31)
   mom = calc_momentum(conn, target)
   vol = calc_volatility(conn, target)
   val = calc_value(conn, target)

   # 将来リターンと IC 計算
   fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
   ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
   ```

6. Z スコア正規化
   ```python
   from kabusys.data.stats import zscore_normalize
   normed = zscore_normalize(mom, columns=["mom_1m", "ma200_dev"])
   ```

7. 品質チェックを単体で実行
   ```python
   from kabusys.data.quality import run_all_checks
   issues = run_all_checks(conn, target_date=date(2024,1,31))
   for i in issues:
       print(i)
   ```

---

## 注意 / 実装上のポイント

- 環境読み込み
  - config モジュールはプロジェクトルート（.git や pyproject.toml を基準）から `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 必須 env が未設定の場合、Settings のプロパティアクセス時に ValueError が発生します。

- J-Quants クライアント
  - レート制御（120 req/min）と指数バックオフリトライ、401 時のトークン自動リフレッシュを実装しています。
  - ページネーション対応で全件を取得します。

- ニュース収集
  - RSS の XML パースは defusedxml を利用し、SSRF 対策（リダイレクト先・ホストのプライベート判定）や受信サイズ制限を実施しています。
  - 記事 ID は正規化した URL の SHA-256 先頭 32 文字で生成し、冪等性を確保します。

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution の多層スキーマを定義しています。
  - ON CONFLICT を用いた冪等保存（save_* 関数）に対応しています。

- 品質チェック
  - fail-fast ではなく全チェックを走らせて問題のリストを収集し、呼び出し元で対処方針を決定できるようにしています。

---

## ディレクトリ構成（概要）

以下はコードベースの主なファイルとモジュール階層です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
    - schema.py                    — DuckDB スキーマ定義・初期化
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - features.py                  — 特徴量インターフェース
    - calendar_management.py       — 市場カレンダー管理ユーティリティ
    - audit.py                     — 監査ログスキーマ初期化
    - etl.py                       — ETL 型の再エクスポート
    - quality.py                   — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py           — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py       — 将来リターン・IC・要約統計
  - strategy/                       — 戦略用パッケージ（未実装エントリ）
  - execution/                      — 発注/実行系（未実装エントリ）
  - monitoring/                     — 監視系（未実装エントリ）

---

## 追加情報 / 推奨

- ログレベルや KABUSYS_ENV によって挙動（例えば実際に発注するかどうか）を分ける想定です。実運用では `KABUSYS_ENV=live` を利用する前に十分なテスト（paper_trading）を実施してください。
- DuckDB ファイルはデフォルトで `data/kabusys.duckdb` に保存されます。バックアップや権限設定を適切に行ってください。
- ニュース収集や外部 API 呼び出し部分はネットワークエラーやタイムアウトを考慮した呼び出し設計が必要です。既にライブラリは多くの対策を導入していますが、実運用では監視や再試行ポリシーを上乗せしてください。

---

この README はコードベースの主要点をまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば README にサンプルスクリプトや運用手順（cron / Airflow / systemd 例）を追加します。