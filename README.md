# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）。

注意: 本 README はリポジトリ内のソースコードを元に作成しています。実行には各種 API トークンや外部パッケージが必要です。

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL・特徴量生成・研究（リサーチ）・発注監査のためのモジュール群を提供するライブラリです。主な目的は以下の通りです。

- J-Quants からの市場データ（株価・財務・市場カレンダー）取得と DuckDB への冪等保存
- RSS ベースのニュース収集と記事・銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター（モメンタム・ボラティリティ・バリュー等）計算、IC 計算・統計サマリー
- 発注・約定・監査用のスキーマ設計（監査ログの初期化補助）
- ETL パイプラインの統合実行（差分取得・保存・品質チェック）

設計上の特徴：
- DuckDB をデータレイヤに採用（オンディスク / :memory: 両対応）
- J-Quants API のレート制御・リトライ・トークン自動リフレッシュに対応
- ニュース収集は SSRF/ZIP爆弾対策や入力正規化を考慮した実装
- 外部に過度に依存しないよう標準ライブラリでの実装を心がけたユーティリティ群

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、レート制御、IDトークン自動更新）
  - pipeline: 日次 ETL（市場カレンダー、株価、財務データ）と差分更新の実装
  - schema / audit: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit）
  - news_collector: RSS 取得、記事正規化、ID作成、raw_news 保存、銘柄抽出・紐付け
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）および集約実行
  - stats / features: Zスコア正規化など統計ユーティリティ
- research/
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、ランク関数
  - factor_research: モメンタム / ボラティリティ / バリューファクター算出
- config: 環境変数の読み込み（.env / .env.local 自動ロード）と型付き設定アクセス
- execution, strategy, monitoring: パッケージプレースホルダ（実装拡張想定）

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10+ を推奨（ソースに | 型ヒントを使用）
- Git リポジトリをクローン済み

1. 仮想環境の作成と有効化（例）
   - Linux / macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 依存パッケージのインストール
   リポジトリに pyproject.toml / requirements.txt がある想定で、プロジェクトルートから:
   - pip install -e .      # 開発インストール（パッケージ化されている場合）
   - もしくは必要最低限:
     - pip install duckdb defusedxml

   （プロジェクトの pyproject.toml に依存が定義されていれば pip install -e . が推奨）

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動的に読み込まれます（ただしプロセス環境の変数が優先）。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

   最低限設定が必要な環境変数（コード内で `_require` を使っているもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. DuckDB 初期化
   - Python からスキーマを作成します（親ディレクトリがなければ自動作成されます）:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # ファイルパスまたは ":memory:" 可
     ```

5. 監査用 DB 初期化（任意）
   ```python
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（いくつかの例）

以下は代表的なユースケースの使用例です。Python スクリプト / REPL から実行します。

1. DuckDB スキーマの初期化
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL を実行（J-Quants トークンは settings から取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data import schema
   conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続

   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

   - ETL は市場カレンダー→株価→財務→品質チェックの順に実行します。
   - エラーは各ステップでキャッチされ結果オブジェクトに記録されます。

3. J-Quants から株価を直接取得して保存
   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.data import schema
   conn = schema.get_connection("data/kabusys.duckdb")
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)
   ```

4. RSS ニュース収集ジョブ（銘柄抽出付き）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data import schema
   conn = schema.get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄コードを準備する
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: saved_count}
   ```

5. 研究用ファクター計算（例: モメンタム）
   ```python
   from kabusys.research import calc_momentum
   from kabusys.data import schema
   from datetime import date

   conn = schema.get_connection("data/kabusys.duckdb")
   recs = calc_momentum(conn, target_date=date(2024,3,15))
   # recs: [{"date": ..., "code": "7203", "mom_1m": ..., "ma200_dev": ...}, ...]
   ```

6. 将来リターン計算・IC・統計サマリー
   ```python
   from kabusys.research import calc_forward_returns, calc_ic, factor_summary
   # forward = calc_forward_returns(conn, date.today())
   # ic = calc_ic(factor_records, forward, factor_col="mom_1m", return_col="fwd_1d")
   ```

---

## 主要な API と挙動メモ

- 環境変数管理
  - kabusys.config.Settings 経由で設定にアクセス（settings.jquants_refresh_token 等）。
  - .env ファイルをプロジェクトルート（.git または pyproject.toml の検出位置）から自動読み込みします。プロセス環境変数が優先されます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限 120 req/min を固定間隔で守る実装（内部 RateLimiter）。
  - 408/429/5xx 系に対する指数バックオフリトライ（最大 3 回）。
  - 401 受信時にリフレッシュトークンで ID トークンを自動更新して 1 回リトライ。
  - fetch_* 系関数はページネーション対応。

- ニュース収集（kabusys.data.news_collector）
  - RSS の XML パースは defusedxml による安全化済み。
  - レスポンスサイズ上限（10MB）や Gzip 解凍後のサイズチェックを行う。
  - リダイレクトやホスト検証で SSRF 対策を実施（プライベートアドレスへのアクセスを禁止）。

- データ品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency を提供。
  - run_all_checks でまとめて実行し QualityIssue のリストを得られる。

- DuckDB スキーマ（kabusys.data.schema）
  - init_schema(db_path) で全テーブル・インデックスを冪等に作成。
  - get_connection(db_path) で接続のみ取得（スキーマ初期化は行わない）。

- 監査ログ（kabusys.data.audit）
  - init_audit_db(db_path) で監査用 DB を初期化。TimeZone を UTC に固定して作成。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - etl.py
    - features.py
    - stats.py
    - quality.py
    - calendar_management.py
    - audit.py
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各ファイルの責務は上の「主な機能一覧」やコード内の docstring を参照してください。

---

## 注意事項・セキュリティ

- API トークン等の機密情報は .env に保存する場合は権限管理（.gitignore）を徹底してください。
- J-Quants の API レート制限を超えるとサービスに拒否される可能性があります。本ライブラリは固定間隔で制限を守る実装ですが、運用側でも実行頻度に注意してください。
- ニュース収集は外部 URL に接続するため、ネットワークポリシーや環境に応じてプロキシやアクセス制限を検討してください。
- DuckDB のバージョン互換（外部機能のサポート）に依存する箇所があるため、実行環境の duckdb バージョンに注意してください。

---

## 今後の拡張案（参考）

- strategy / execution / monitoring の実装強化（発注フローと監視ダッシュボード）
- Slack 通知モジュールの実装（settings.slack_* を活用）
- テスト用モック・CI の整備（外部 API 呼び出しをモックしてユニットテストを作成）
- docker イメージでの一括デプロイ用設定

---

この README はコードベースの docstring と実装を基に作成しました。実行やデプロイ時は環境に合わせて環境変数や依存パッケージを適切に設定してください。必要であればサンプルスクリプトや .env.example を追加することを推奨します。