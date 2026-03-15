# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

なお、この CHANGELOG はリポジトリ内の現在のコードベースから推測して作成しています（自動生成ではなく手作業の要約です）。

## [0.1.0] - 2026-03-15
初回リリース

### 追加
- パッケージ初期化
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ を使ったトップレベルエクスポート: data, strategy, execution, monitoring

- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に .git / pyproject.toml を探索（CWD に依存しない）
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ:
    - 空行・コメント（#）の扱い
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープに対応
    - クォートなし値のインラインコメント処理（直前がスペースまたはタブの場合のみ）
  - .env のロードロジック:
    - override フラグ（.env.local は上書き）、protected セット（OS 環境変数の保護）を実装
    - ファイル読み込み失敗時は警告を出力
  - Settings クラス:
    - J-Quants, kabuステーション, Slack, DB パス等のプロパティを提供
    - 必須環境変数は未設定時に ValueError を送出（_require）
    - env / log_level の値検証（許容値を限定）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本設計:
    - API レート制限遵守（120 req/min）
    - リトライ（最大 3 回、指数バックオフ）、対象ステータス: 408 / 429 / 5xx
    - 401 受信時はトークン自動リフレッシュして 1 回だけリトライ
    - ページネーション対応
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
  - 実装要素:
    - _RateLimiter クラスによる固定間隔スロットリング
    - トークンキャッシュ (_ID_TOKEN_CACHE) と get_id_token()（リフレッシュ処理）
    - HTTP ユーティリティ _request():
      - タイムアウト、ヘッダ、JSON デコードエラーハンドリング
      - リトライループ、429 の Retry-After 優先、指数バックオフ
    - データ取得関数:
      - fetch_daily_quotes(code, date_from, date_to)
      - fetch_financial_statements(code, date_from, date_to)
      - fetch_market_calendar(holiday_division)
      - すべてページネーションを適切に処理し、ログを出力
    - DuckDB 保存関数（冪等）:
      - save_daily_quotes(conn, records): raw_prices へ保存（PK 重複は UPDATE）
      - save_financial_statements(conn, records): raw_financials へ保存（PK 重複は UPDATE）
      - save_market_calendar(conn, records): market_calendar へ保存（PK 重複は UPDATE）
      - 保存時に PK 欠損行をスキップし警告ログを出力
    - データ変換ユーティリティ:
      - _to_float, _to_int（厳密な変換ルールを採用、例: 小数部がある場合は int へ変換しない）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - 3 層データアーキテクチャ（Raw / Processed / Feature）および Execution レイヤの DDL を追加
  - Raw Layer:
    - raw_prices, raw_financials, raw_news, raw_executions
  - Processed Layer:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature Layer:
    - features, ai_scores
  - Execution Layer:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリパターン用）を追加
  - init_schema(db_path) による初期化関数を追加
    - db_path の親ディレクトリを自動作成
    - :memory: をサポート
  - get_connection(db_path): 既存 DB への接続（初期化は行わない）

- 監査ログ / トレーサビリティ (kabusys.data.audit)
  - トレーサビリティ階層・設計原則に基づく監査テーブルを追加
    - signal_events（シグナル生成ログ）
    - order_requests（発注要求ログ、order_request_id を冪等キーとして扱う）
    - executions（約定ログ、broker_execution_id を冪等キーとして扱う）
  - 各種チェック制約、ステータス遷移列、created_at/updated_at が含まれる
  - インデックスを追加（status スキャン、signal_id の検索等）
  - init_audit_schema(conn): 既存 DuckDB 接続に監査テーブルを追加（UTC タイムゾーン設定）
  - init_audit_db(db_path): 監査ログ専用 DB の初期化関数

- モジュールスケルトン
  - 空のパッケージモジュールを追加（プレースホルダ）
    - kabusys.execution, kabusys.strategy, kabusys.data.__init__, kabusys.monitoring.__init__

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 削除
- なし（初回リリース）

---

注記:
- 本 CHANGELOG はソースコードの状態から推測して作成しています。実際のコミット履歴や作者コメントが存在する場合はそれらに基づく差分管理を推奨します。