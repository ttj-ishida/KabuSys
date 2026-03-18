# KabuSys — 日本株自動売買システム

日本株向けのデータ収集・ETL・監査・実行基盤のライブラリ群です。主に J-Quants API や RSS フィードを用いた市場データ収集、DuckDB を用いた永続化、品質チェック、監査ログ（トレーサビリティ）、および発注／実行管理のためのスキーマとユーティリティを提供します。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定間隔スロットリング）
  - 再試行（指数バックオフ、最大3回）、401時の自動トークンリフレッシュ（1回）
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアス対策
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードから記事を収集して raw_news に保存
  - URL 正規化・トラッキングパラメータ除去による記事ID生成（SHA-256 の先頭32文字）
  - SSRF 対策（スキーム検証、リダイレクト先ホストのプライベートアドレス検査）
  - レスポンスサイズ上限（デフォルト 10MB）と gzip 解凍後の検査
  - 銘柄コード抽出（テキストから 4 桁コードを抽出して既知コードと照合）
  - DB 保存はチャンク化してトランザクション内で実施、INSERT ... RETURNING による実挿入検出

- ETL パイプライン
  - 差分更新（最終取得日から未取得分のみ取得）
  - backfill による直近データ再取得（API 側の後出し修正吸収）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 市場カレンダー先読み（デフォルト 90 日）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化関数
  - 監査ログ（signal / order_request / executions 等）用スキーマ（トレーサビリティ重視）
  - インデックス定義（クエリパターンを考慮）

- データ品質チェック
  - 欠損（OHLC 欄）、スパイク（前日比閾値）、重複（主キー）、将来日付／非営業日検出
  - チェックはすべての問題を収集して戻す（Fail-Fast ではない）

- マーケットカレンダー管理
  - 営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - JPX カレンダーを J-Quants から夜間バッチで差分更新

---

## 要件

- Python 3.10+
- 必須 Python パッケージ（例）
  - duckdb
  - defusedxml
- （必要に応じて）その他依存パッケージはプロジェクトの packaging/requirements を参照してください

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトが package 配布されている場合）pip install -e .

4. 環境変数ファイルを作成
   - リポジトリルートに `.env`（または `.env.local`）を作成してください。
   - `.env.example` があればそれを参考にしてください。
   - 自動ロードはデフォルトで有効です（config.py がプロジェクトルートを検出して `.env` を読み込みます）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（少なくともこれらを設定してください）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite path（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読み込みを無効化

---

## 使い方（基本例）

以下は Python REPL またはスクリプトから利用する例です。

- DuckDB スキーマ初期化
  - from kabusys.config import settings
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)
  - （`:memory:` を指定するとインメモリ DB を使用できます）

- 監査ログ DB 初期化（専用 DB を使う場合）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # デフォルトは本日を対象
  - result は ETLResult オブジェクト（処理結果・品質チェック結果・エラー概要を含む）

- 指定日の ETL 実行（例: 2024-01-01）
  - from datetime import date
  - run_daily_etl(conn, target_date=date(2024, 1, 1))

- 市場カレンダー夜間更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
  - from kabusys.data.schema import get_connection
  - results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))

- J-Quants API から直接データ取得（テスト／デバッグ）
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  - token = get_id_token()
  - records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)

各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。init_schema / init_audit_db は接続を生成して返します。

---

## 運用例（スケジューリング）

- 日次 ETL:
  - 夜間の cron / CI ジョブで run_daily_etl を実行（品質チェックを有効）
- カレンダー更新:
  - calendar_update_job を日次で実行して market_calendar を先読み（デフォルト 90 日）
- ニュース収集:
  - 短間隔で複数ソースを巡回して raw_news を蓄積し、銘柄紐付けを行う

注意:
- ETL / データ収集は外部 API に依存するため、適切なレート管理や再試行設定を尊重してください（jquants_client はデフォルトで 120 req/min に合わせた RateLimiter を有しています）。
- 重要な環境（live）では `KABUSYS_ENV=live` を設定し、ログ・通知・実行ロジックを適切に管理してください。

---

## ディレクトリ構成

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py         -- RSS ニュース収集 & 保存・銘柄抽出
    - schema.py                 -- DuckDB スキーマ定義 & 初期化
    - pipeline.py               -- ETL パイプライン（差分更新 / 品質チェック統合）
    - calendar_management.py    -- マーケットカレンダー管理ユーティリティ
    - audit.py                  -- 監査ログ（トレーサビリティ）スキーマ初期化
    - quality.py                -- データ品質チェック
  - strategy/
    - __init__.py               -- 戦略層（将来的な拡張）
  - execution/
    - __init__.py               -- 発注・実行関連（将来的な拡張）
  - monitoring/
    - __init__.py               -- 監視・メトリクス関連（将来的な拡張）

---

## 開発メモ / 重要な設計ポイント

- 環境変数の自動ロード
  - config._find_project_root() により .git または pyproject.toml を基準にプロジェクトルートを探して `.env` / `.env.local` を読み込みます。
  - テスト時など自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J-Quants クライアント
  - 固定間隔スロットリング（_RateLimiter）で 120 req/min を守る実装
  - 408/429/5xx に対するリトライ（指数バックオフ）
  - 401 を受けた場合はリフレッシュトークンから id_token を再取得して 1 回リトライ
  - ページネーションに対応し、ページ間で id_token を共有（モジュールレベルのキャッシュ）

- ニュース収集の安全対策
  - defusedxml を利用して XML パース攻撃を防ぐ
  - リダイレクト時のホスト検査やスキーマ検証による SSRF 防止
  - レスポンスサイズ制限や gzip 解凍後の再チェックで DoS 対策

- DuckDB スキーマ
  - Raw→Processed→Feature→Execution と層を分けた設計
  - 多くの INSERT は ON CONFLICT を使って冪等に保存する
  - audit.init_audit_schema はタイムゾーンを UTC に設定（監査ログの一貫性確保）

- 品質チェック
  - 全てのチェックは問題を全て収集して戻す（ETL 側でどのレベルで止めるかを判断）
  - スパイク閾値や backfill 日数はパラメータで調整可能

---

## 参考 / よくある質問

- Q: DuckDB の接続は同一プロセスで共有しても大丈夫？
  - A: DuckDB はマルチスレッドやプロセスの挙動に注意が必要です。単一プロセス内での共有接続は可能ですが、並行トランザクションやネストトランザクションに関しては DuckDB の仕様に従ってください。

- Q: テスト時に .env を読み込ませたくない
  - A: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

この README はコードベースの現状に基づいています。戦略ロジック（strategy/）や実際のブローカー連携（execution/）は拡張ポイントとして用意されています。さらに詳しい仕様や DataPlatform.md 等の設計文書がある場合はそれらを参照して運用／拡張してください。