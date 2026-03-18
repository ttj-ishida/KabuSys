# KabuSys

日本株向けの自動売買システム向けユーティリティ群（ライブラリ）

本リポジトリは、J-Quants / kabuステーション 等の外部データソースと連携して
データ収集・ETL・品質チェック・監査ログの初期化を行う Python モジュール群です。
戦略・発注・モニタリング層と組み合わせて自動売買プラットフォームを構築するための
データプラットフォーム基盤を提供します。

主な用途例:
- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に永続化
- RSS からニュースを収集して記事と銘柄の紐付けを行う
- 日次 ETL（差分更新・バックフィル・品質チェック）の実行
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマの初期化

---

## 機能一覧

- 環境変数・設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可能）
  - アプリ実行環境（development / paper_trading / live）やログレベル検証

- J-Quants クライアント（data/jquants_client.py）
  - 株価日足（OHLCV）、財務四半期データ、JPX マーケットカレンダーの取得
  - API レート制限（120 req/min）に基づくスロットリング
  - リトライ（指数バックオフ）、401 発生時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT）

- ニュース収集（data/news_collector.py）
  - RSS フィード取得・XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事ID を SHA-256 で生成（先頭32文字）
  - SSRF 対策（スキーム検証・プライベートIP拒否・リダイレクト検査）
  - 受信サイズ制限（Gzip除く、10MB）や gzip 解凍後の再検査
  - DuckDB への冪等保存（INSERT ... ON CONFLICT DO NOTHING / RETURNING）

- DuckDB スキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution 層を想定したテーブル定義
  - インデックス作成、初期化関数（init_schema）

- ETL パイプライン（data/pipeline.py）
  - 差分更新（最終取得日を基に自動算出）、バックフィル対応
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損、重複、スパイク、日付整合性）と集約結果返却

- カレンダー管理（data/calendar_management.py）
  - 営業日判定、前後の営業日検索、期間内営業日列挙
  - 夜間バッチでのカレンダー更新（calendar_update_job）

- 監査ログ（data/audit.py）
  - signal_events / order_requests / executions テーブルでトレーサビリティを担保
  - UTC 固定、冪等キー、各種制約・インデックスの初期化ヘルパー

- 品質チェック（data/quality.py）
  - 欠損データ、重複、前日比スパイク、将来日付／非営業日データ検出
  - QualityIssue を返す形で結果を集約

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.9+（型アノテーションの一部は 3.10 の union 型等を使用しているため 3.9/3.10 を想定）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   本リポジトリのコードから必要な主要パッケージは以下です:
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt や pyproject.toml がある場合はそれに従ってください）

4. 環境変数を設定
   プロジェクトルートに .env（および必要なら .env.local）を置くと自動読み込みされます。
   自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   任意（デフォルトあり）:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト: INFO

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡単なサンプル）

以下は Python スクリプトや REPL での操作例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  ```

- J-Quants の ID トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.JQUANTS_REFRESH_TOKEN を使って取得
  ```

- 日次 ETL を実行する（市場カレンダー取得 → 株価・財務データ取得 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
  print(result.to_dict())
  ```

- RSS ニュース収集（既知銘柄コードを与えて紐付けまで行う）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema(":memory:")  # または実ファイルパス
  known_codes = {"7203", "6758", "9984"}  # 事前に取得した有効コードの集合
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: new_count}
  ```

- 監査ログスキーマ初期化（audit）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 市場カレンダーの営業日判定例
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  print(is_trading_day(conn, date(2026, 1, 1)))
  ```

注意点:
- ETL 内の API 呼び出しは rate limit に従うため時間がかかる場合があります。
- 実運用（live）では設定やシークレット管理に注意してください（.env ファイルを公開しない等）。

---

## よくある操作・オプション

- 自動 env ロードを無効にする（テスト等）
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- ログレベルを調整する
  ```
  export LOG_LEVEL=DEBUG
  ```

- DuckDB をインメモリで実行して素早く試す
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  ```

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                  -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py        -- J-Quants API クライアント（取得・保存）
      - news_collector.py       -- RSS ニュース収集・DB 保存
      - schema.py               -- DuckDB スキーマ定義・初期化
      - pipeline.py             -- ETL パイプライン（差分更新・品質チェック）
      - calendar_management.py  -- カレンダー管理・営業日判定
      - audit.py                -- 監査ログ（signal/order/execution）スキーマ
      - quality.py              -- データ品質チェック
    - strategy/
      - __init__.py              -- 戦略用プレースホルダ
    - execution/
      - __init__.py              -- 発注/ブローカー連携用プレースホルダ
    - monitoring/
      - __init__.py              -- モニタリング関連プレースホルダ

- pyproject.toml / .git / .env.example 等（プロジェクトルートに配置される想定）

---

## 設計上のポイント（開発者向けメモ）

- J-Quants クライアント:
  - レート制限はモジュール単位の固定間隔スロットリングで実装（_RateLimiter）。
  - 再試行は最大 3 回、408/429/5xx に対して指数バックオフを行う。
  - 401 を受け取った場合はリフレッシュトークンを使って id_token を再取得して 1 回だけ再試行。

- ニュース収集:
  - defusedxml を使用して XML の脆弱性対策を行う。
  - SSRF 対策としてスキーム検証、リダイレクト先のプライベートアドレス検査を実施。
  - 受信データの上限を設け、Gzip 解凍後も上限超過を検査する。

- データ保存:
  - DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）にして再実行可能性を高める。

- 品質チェック:
  - Fail-Fast ではなく、全チェックを実行して問題リストを返す設計。

---

## 注意事項・運用上の留意点

- 本ライブラリは取り扱うデータや鍵情報（API トークン）によっては機密情報を扱います。環境変数・シークレットは安全に管理してください。
- 実運用での取引系処理は重大なリスクを伴います。paper_trading 環境で十分に検証した上で live 環境へ移行してください。
- J-Quants / 証券会社の API 利用ルールやレート制限は変更される可能性があります。運用時は最新の仕様を確認してください。

---

README に記載されていない使い方や、CI／運用スクリプト、戦略層・発注層との統合方法については開発者向けの追加ドキュメント（Design.md, DataPlatform.md 等）を参照してください。必要であれば README のサンプルや運用手順を拡充しますので、用途に応じて教えてください。