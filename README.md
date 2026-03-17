# KabuSys

日本株向けの自動売買およびデータ基盤ライブラリです。J-Quants API や RSS を介したニュース収集、DuckDB を用いたデータスキーマ／ETL、監査ログ（オーダー／約定トレース）などを提供します。

概要:
- データ収集（J-Quants：日足/財務/カレンダー）
- ニュース収集（RSS → 正規化／DB 保存／銘柄抽出）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 市場カレンダー管理（営業日判定・next/prev）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- DuckDB を中心とした冪等保存（ON CONFLICT / INSERT ... RETURNING 等）

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レート制限（120 req/min）管理、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録

- ニュース収集
  - RSS フィード取得・XML サニタイズ（defusedxml）
  - URL 正規化（トラッキング削除）、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証、ホストのプライベート判定、リダイレクト検査）
  - 受信サイズ制限（デフォルト 10MB）、gzip 解凍後サイズチェック
  - DuckDB へ一括保存（トランザクション、INSERT ... RETURNING）

- DuckDB スキーマ
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス定義、監査ログ（signal_events / order_requests / executions）用DDL

- ETL パイプライン
  - run_daily_etl：カレンダー → 株価 → 財務 → 品質チェック（差分更新 + バックフィル）
  - 差分更新により過去分は最小限の API コールで更新

- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合（未来日・非営業日）を検出して QualityIssue を返す

- カレンダー管理
  - 営業日判定、次/前営業日取得、期間の営業日リスト作成、夜間カレンダー更新ジョブ

---

## 前提（Prerequisites）

- Python 3.10 以上（union 型表記 `X | Y` を使用）
- 主な依存パッケージ:
  - duckdb
  - defusedxml
- ネットワークアクセス権（J-Quants API、RSS フィード）
- 推奨：仮想環境（venv, pyenv など）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを編集可能モードでインストールする場合（pyproject.toml がある想定で）
pip install -e .
```

（プロジェクトに pyproject.toml / requirements.txt があればそちらに従ってください）

---

## 環境変数 / 設定

自動的にプロジェクトルートの `.env` または `.env.local` を読み込みます（CWD ではなくパッケージ位置から探索）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（アプリ起動に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development, paper_trading, live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)（デフォルト: INFO）

.env 例（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   pip install -e .
   ```

2. 環境変数を設定（.env を作成）
   - 先述の必須キーを `.env` に記載

3. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで実行:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・テーブル作成
   conn.close()
   ```

4. （任意）監査ログ DB 初期化（監査専用 DB を使う場合）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（主要な API と実行例）

- 日次 ETL 実行（カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)  # まだ初期化していない場合
  result = run_daily_etl(conn)  # target_date などを引数で指定可能
  print(result.to_dict())
  conn.close()
  ```

- 個別 ETL ジョブ
  - 株価差分 ETL:
    ```python
    from kabusys.data.pipeline import run_prices_etl
    run_prices_etl(conn, target_date=date.today())
    ```
  - 財務差分 ETL:
    ```python
    from kabusys.data.pipeline import run_financials_etl
    run_financials_etl(conn, target_date=date.today())
    ```
  - カレンダー ETL:
    ```python
    from kabusys.data.pipeline import run_calendar_etl
    run_calendar_etl(conn, target_date=date.today())
    ```

- ニュース収集ジョブ（RSS から収集して DB に保存）
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 任意に有効な銘柄コードを用意
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(stats)  # {source_name: 新規保存件数}
  conn.close()
  ```

- スキーマ／監査テーブルの初期化（既存接続に監査を追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)  # List[QualityIssue]
  for i in issues:
      print(i)
  ```

注意点:
- J-Quants API のレートは 120 req/min に制御されています（モジュール内でスロットリング）。
- ネットワーク・HTTP エラーはリトライされます（408/429/5xx 等）。
- get_id_token は 401 を検出すると自動でリフレッシュを試みます（1 回のみリトライ）。
- DuckDB への保存は冪等性を意識した SQL（ON CONFLICT）を使用しています。

---

## よく使う設定 / 挙動

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化（テスト時に便利）。
- デフォルトのバックフィル日数:
  - ETL: backfill_days = 3（日足、財務） — 最終取得日の数日前から再取得して後出し修正に対応
  - カレンダー: lookahead_days = 90（先読み）
- ニュース収集の受信サイズ上限は 10MB（gzip 解凍後も検査）
- RSS の記事ID は正規化 URL の SHA-256（先頭32文字）で一意化
- SSRF対策、DNS 解決によるプライベート IP 判定を実装

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 -- 環境設定読み込み / Settings
    - data/
      - __init__.py
      - jquants_client.py       -- J-Quants API クライアント（取得・保存）
      - news_collector.py       -- RSS → raw_news 保存、銘柄抽出
      - schema.py               -- DuckDB スキーマ定義 / init_schema
      - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py  -- 市場カレンダー管理 / 夜間更新ジョブ
      - audit.py                -- 監査ログスキーマ（signal/order/execution）
      - quality.py              -- データ品質チェック
    - strategy/
      - __init__.py             -- 戦略層（拡張ポイント）
    - execution/
      - __init__.py             -- 発注／ブローカー連携（拡張ポイント）
    - monitoring/
      - __init__.py             -- 監視関連（拡張ポイント）

---

## 開発・拡張ポイント

- strategy/、execution/、monitoring/ はプレースホルダで、戦略実装やブローカー接続、監視アラートを追加する場所です。
- DuckDB スキーマは DataPlatform.md に基づく想定で作成済み。機能追加時は schema.py の DDL を更新してください。
- news_collector は RSS 正規化・SSRF 対策・トラッキング削除を実装済み。別ソースの追加は DEFAULT_RSS_SOURCES を拡張するか run_news_collection に sources を渡してください。

---

## トラブルシューティング / FAQ

- Q: .env が読み込まれない
  - A: パッケージは __file__ を起点にプロジェクトルートを探索して `.env` / `.env.local` を読み込みます。プロジェクトルートに .git または pyproject.toml が必要です。自動ロードを無効にしている場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。

- Q: J-Quants API で 401 が返る
  - A: クライアントは 401 を検出すると一度トークンをリフレッシュして再試行します。リフレッシュが失敗する場合は JQUANTS_REFRESH_TOKEN を確認してください。

- Q: ニュース収集で特定の RSS が取得できない
  - A: レスポンスサイズ上限、gzip 解凍失敗、XML パースエラー、あるいは最終 URL がプライベートアドレスにリダイレクトされた可能性があります。ログを確認して原因を特定してください。

---

## ライセンス / 貢献

（この README にはライセンス情報が含まれていません。実プロジェクトでは LICENSE ファイルを追加してください）

貢献: プルリクエスト歓迎。仕様変更・設計議論は issue でお願いします。

---

必要であれば README に実行スクリプト（例: cron / systemd / Airflow のタスク定義）や CI 設定、より詳細な環境変数の説明（.env.example）を追加できます。どの情報を優先して追記しましょうか？