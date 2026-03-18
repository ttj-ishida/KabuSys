# KabuSys

日本株自動売買プラットフォーム用のライブラリ群。データ取得（J-Quants）、ETLパイプライン、ニュース収集、DuckDBスキーマ管理、品質チェック、監査ログなど、取引システムのデータ基盤・トレーサビリティ機能を提供します。

主な設計方針：
- データ取得は API レート制限・リトライ・トークン自動リフレッシュを考慮
- データ保存は冪等（ON CONFLICT）で上書き・重複排除
- ニュース収集は SSRF/XML 攻撃対策、トラッキング除去、記事ID のハッシュ化で冪等性を担保
- DuckDB を中心とした 3 層（Raw / Processed / Feature）＋ Execution / Audit のスキーマを提供

---

## 機能一覧

- J-Quants API クライアント（jquants_client）
  - 株価日足（OHLCV）、財務四半期データ、JPX カレンダー取得
  - レートリミット管理、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等保存（save_* 関数）

- ETL パイプライン（data.pipeline）
  - 差分更新（最終取得日基準）、バックフィル、カレンダー先読み
  - 日次 ETL の統合 run_daily_etl（品質チェック付き）

- ニュース収集（data.news_collector）
  - RSS 取得、URL 正規化、記事ID(sha256先頭32文字)生成、前処理、DuckDB への冪等保存
  - SSRF 対策、Gzip サイズ制限、defusedxml による XML 攻撃緩和、銘柄コード抽出

- データスキーマ管理（data.schema）
  - DuckDB の DDL をまとめて初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブルとインデックスを定義

- カレンダー管理（data.calendar_management）
  - 営業日判定、next/prev_trading_day、営業日リスト取得、夜間カレンダー更新ジョブ

- 品質チェック（data.quality）
  - 欠損、重複、スパイク（前日比閾値）、日付不整合（未来日・非営業日）を検出
  - QualityIssue オブジェクトで検出結果を返却

- 監査ログ（data.audit）
  - シグナル → 発注要求 → 約定 を UUID 連鎖でトレースする監査用テーブル群
  - init_audit_schema / init_audit_db による初期化

- 設定管理（config）
  - .env 自動読み込み（プロジェクトルート検知）と Settings オブジェクト経由の環境変数アクセス
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - サポートされる環境: development, paper_trading, live

---

## セットアップ手順

前提：
- Python 3.9+（コードは型アノテーションで Path | None 等を使用。実行環境に合わせて適宜）
- DuckDB を利用（ローカルファイルまたは :memory:）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - ない場合は最低限以下をインストールしてください:
     ```
     pip install duckdb defusedxml
     ```
   - パッケージとしてインストールする（プロジェクト配布時）:
     ```
     pip install -e .
     ```

4. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を作成できます（自動ロードされます）。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=eyJ...            # 必須
     KABU_API_PASSWORD=your_kabu_password     # 必須
     SLACK_BOT_TOKEN=xoxb-...                 # 必須（Slack通知を使う場合）
     SLACK_CHANNEL_ID=C01234567               # 必須（Slack通知を使う場合）
     DUCKDB_PATH=data/kabusys.duckdb          # 任意（デフォルト）
     SQLITE_PATH=data/monitoring.db           # 任意（デフォルト）
     KABUSYS_ENV=development                  # development|paper_trading|live
     LOG_LEVEL=INFO                           # DEBUG|INFO|WARNING|ERROR|CRITICAL
     ```
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（主な例）

以下は Python スクリプト／REPL での利用例です。import パスはパッケージ配置に依存します（src 配下でパッケージ化されている想定）。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" でも可
  ```

- 監査DB 初期化（監査専用 DB）
  ```python
  from kabusys.data import audit
  conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants ID トークン取得（明示的に）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
  ```

- 日次 ETL を実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # デフォルトは本日
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved={saved}")
  ```

- RSS ニュース収集（既知銘柄セットを渡す）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # ソース毎の新規保存数
  ```

- データ品質チェックを個別実行
  ```python
  from kabusys.data.quality import run_all_checks
  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

メソッドの多くは例外を投げる可能性があるため、実運用では適切な例外ハンドリング・ロギングを行ってください。

---

## 環境変数一覧（重要）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token の元）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack Bot トークン（通知を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知を使う場合）

任意（デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite path（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化するフラグ（値は任意）

設定は Settings オブジェクト（kabusys.config.settings）からアクセスできます。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py              — J-Quants API クライアント（取得・保存）
      - news_collector.py              — RSS 取得・記事保存・銘柄抽出
      - schema.py                      — DuckDB スキーマ定義・初期化
      - pipeline.py                    — ETL パイプライン（日次 ETL 等）
      - calendar_management.py         — 営業日判定・カレンダーバッチ
      - quality.py                     — データ品質チェック
      - audit.py                       — 監査ログ（signal/order/execution）
    - strategy/
      - __init__.py                     — 戦略関連（拡張ポイント）
    - execution/
      - __init__.py                     — 発注 / ブローカー連携（拡張ポイント）
    - monitoring/
      - __init__.py                     — 監視 / メトリクス用フック（拡張ポイント）

各モジュールは設計上拡張しやすく分離されています。strategy／execution／monitoring は実戦向けに実装を追加する想定です。

---

## 設計上の注意点・運用メモ

- J-Quants API はレート制限（120 req/min）に従うため、クライアント側でも固定間隔スロットリングを実装しています。大量データ取得時は考慮してください。
- jquants_client は 401 を検出した場合にリフレッシュトークンを用いて id_token を自動更新します（1 回のみ再試行）。
- ニュース収集は SSRF や XML 攻撃対策を実装していますが、外部 URL を扱うため運用時の監視（ログ・TLS 設定など）は重要です。
- DuckDB スキーマは冪等性を重視しており、既存データへの上書きは ON CONFLICT 句で制御します。ETL はバックフィルを行い API 側の後出し修正に耐性を持たせています。
- audit モジュールは監査性重視で、削除しない前提の設計（FK は ON DELETE RESTRICT）です。タイムゾーンは UTC を使用。

---

## 貢献・拡張ポイント

- strategy / execution モジュールは骨組みのみのため、実際のシグナル生成やブローカー連携ロジック（kabuステーションとの API 通信等）を実装してください。
- 監視（monitoring）や Slack 通知のためのユーティリティを追加可能です（config に Slack 設定あり）。
- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境読み込みを無効化し、テスト用の環境を注入してください。

---

必要であれば、README に「デプロイ例」「cron / Airflow でのスケジュール実行例」「Dockerfile」「CI 設定」の雛形も追加できます。どれを追加しますか？