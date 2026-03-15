Keep a Changelogに準拠した CHANGELOG.md（日本語）

すべての注目すべき変更はこのファイルに記録します。
フォーマット: https://keepachangelog.com/ja/1.0.0/

0.1.0 - 2026-03-15
==================

Added
-----
- パッケージ初期リリース。
  - パッケージメタ:
    - バージョン: `kabusys.__version__ = "0.1.0"`
    - パッケージ公開 API: `__all__ = ["data", "strategy", "execution", "monitoring"]`

- 環境設定管理モジュール (kabusys.config)
  - プロジェクトルート自動検出:
    - `.git` または `pyproject.toml` を基準にパッケージ内のファイルパスからプロジェクトルートを探索する `_find_project_root()` を実装。CWD に依存せず自動ロード可能。
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
    - 読み込み優先順位: OS環境変数 > .env.local > .env（.env.local は上書き）
  - .env パーサ:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して閉じクォートまで正しくパース。
    - クォートなし値での `#` は、直前がスペースまたはタブの場合のみコメント扱い。
    - 無効行やキー欠損行はスキップ。
  - `.env` 読み込みに対して保護 (protected) セットを用い、OS の既存環境変数を誤って上書きしない設計。
  - Settings クラス:
    - 必須値取得 `_require()` による明確なエラー (ValueError)。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供:
      - `jquants_refresh_token`, `kabu_api_password`, `kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
      - `slack_bot_token`, `slack_channel_id`
      - `duckdb_path`（デフォルト: data/kabusys.duckdb）, `sqlite_path`（デフォルト: data/monitoring.db）
    - 環境検証:
      - `KABUSYS_ENV` は `development`, `paper_trading`, `live` のいずれか（不正値は ValueError）。
      - `LOG_LEVEL` は `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` のいずれか（不正値は ValueError）。
    - ヘルパー: `is_live`, `is_paper`, `is_dev`

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 設計方針を反映した機能群:
    - API レート制限の遵守（120 req/min）:
      - 固定間隔スロットリングを行う `_RateLimiter` を実装（内部で最小間隔を算出し待機）。
    - 冪等かつ堅牢な HTTP 呼び出し `_request()`:
      - 最大リトライ回数 3 回、指数バックオフ（基底 2.0 秒）。
      - 408/429/5xx 系に対するリトライ、429 に対しては `Retry-After` を優先して待機。
      - ネットワークエラー（URLError/OSError）もリトライ対象。
      - JSON デコード失敗で RuntimeError を送出。
      - 401 発生時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止のため allow_refresh フラグを使用）。
    - 認証ヘルパー:
      - `get_id_token()`：リフレッシュトークンから ID トークンを取得（POST）。
      - モジュールレベルキャッシュ `_ID_TOKEN_CACHE` と `_get_cached_token()` によりページネーション間でトークン共有し無駄な再認証を回避。
    - データ取得（ページネーション対応）:
      - `fetch_daily_quotes()`：日足（OHLCV）取得。`code`, `date_from`, `date_to` でフィルタ。
      - `fetch_financial_statements()`：四半期 BS/PL（財務データ）取得。
      - `fetch_market_calendar()`：JPX マーケットカレンダー取得（祝日・半日・SQ 情報）。
      - ページネーションは `pagination_key` を利用し、ループ防止のための `seen_keys` を保持。
      - 取得件数はログ出力。
    - DuckDB への保存（冪等）:
      - `save_daily_quotes()`、`save_financial_statements()`、`save_market_calendar()` を提供。
      - 保存時に `fetched_at` を UTC（ISO 8601、末尾に Z）で記録し、Look-ahead Bias を防止。
      - INSERT は ON CONFLICT DO UPDATE を利用して冪等性を確保（主キー重複時に更新）。
      - PK 欠損行はスキップして警告ログを出力。
    - 値変換ユーティリティ:
      - `_to_float()`：空値や不正値は None。
      - `_to_int()`：整数または "1.0" のような浮動小数表現を受け付けるが、小数部が 0 でない場合は None を返して誤った切り捨てを防止。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataPlatform.md に基づいた 3 層（Raw / Processed / Feature）＋ Execution 層の DDL を定義。
  - 主なテーブル:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに CHECK 制約を設定して不正データを防止（例: price >= 0, size > 0, side の enum 制約 等）。
  - インデックス定義を用意し、典型的な問い合わせパターン（銘柄×日付スキャン、ステータス検索等）に対応。
  - 公開 API:
    - `init_schema(db_path)`：親ディレクトリの自動作成、全テーブル/インデックス作成（冪等）、DuckDB 接続を返す。
    - `get_connection(db_path)`：既存 DB への接続を返す（スキーマ初期化は行わない）。

- 監査ログモジュール (kabusys.data.audit)
  - シグナル→発注→約定のトレーサビリティを保証する監査用テーブル群を追加。
  - テーブル:
    - `signal_events`：戦略が生成したシグナルをすべて記録（棄却・エラー含む）。UUID 主キー、decision 列に詳細なステータス。
    - `order_requests`：冪等キー `order_request_id` を持つ発注要求ログ。注文種別ごとのチェック（limit/stop の価格制約）を実装。外部キーは ON DELETE RESTRICT（監査ログは削除しない前提）。
    - `executions`：証券会社からの約定情報（broker_execution_id をユニークな冪等キーとして保持）。
  - インデックス:
    - 日付/銘柄/戦略別検索、status ベースのキュー取得、broker_order_id による紐付け等のためのインデックス群を用意。
  - 公開 API:
    - `init_audit_schema(conn)`：既存の DuckDB 接続に監査テーブルとインデックスを追加。関数内で `SET TimeZone='UTC'` を実行し、すべての TIMESTAMP を UTC で保存する仕様を明示。
    - `init_audit_db(db_path)`：監査専用 DB を初期化して接続を返す（親ディレクトリ自動作成、UTC 準拠）。

- パッケージモジュール雛形
  - `kabusys.execution.__init__`, `kabusys.strategy.__init__`, `kabusys.data.__init__`, `kabusys.monitoring.__init__` の初期化ファイルを追加（モジュール構造の確立）。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Security
--------
- （本リリースで特記すべきセキュリティ修正はなし）
  - ただしトークン等の秘密は環境変数から取得する設計としており、.env ファイルの取り扱いや OS 環境変数の保護に注意すること。

Notes / 備考
------------
- DuckDB の初期化は冪等に実装されていますが、初回は `init_schema()` または `init_audit_db()` を呼んでスキーマ作成を行ってください。`get_connection()` はスキーマを作らない点に注意。
- J-Quants API のレートやエラー処理、トークン更新ロジックは実運用を意識した設計（レート制限・Retry-After サポート・トークンキャッシュ）になっていますが、実際の API レスポンス仕様や運用要件に応じてチューニングが必要です。
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされます（パッケージ配布後の挙動を想定）。

今後の予定（例）
----------------
- execution/strategy/monitoring 層の具体的実装（発注送信ロジック、戦略実装、監視・アラート）。
- 単体テスト・統合テストの追加、CI ワークフロー整備。
- ドキュメント（DataSchema.md、API 使用例、運用ガイド）の充実。

--- End of CHANGELOG ---