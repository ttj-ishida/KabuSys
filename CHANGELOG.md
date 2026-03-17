Keep a Changelog
すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買基盤「KabuSys」の基礎機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージルート: kabusys（__version__ = 0.1.0）。
  - サブモジュールプレースホルダ: kabusys.execution, kabusys.strategy。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数の読み込み機能（プロジェクトルート自動検出: .git / pyproject.toml を起点）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート（テスト用途）。
  - .env パーサ: export プレフィックス、クォート文字列、インラインコメントの取り扱いに対応。
  - Settings クラス: 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）取得、既定値 (KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等)、env/log_level のバリデーション、is_live/is_paper/is_dev ヘルパ―。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API レート制御 (120 req/min) を厳守する固定間隔レートリミッタ実装。
  - 冪等性を考慮したデータ取得/保存ワークフロー:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - save_daily_quotes, save_financial_statements, save_market_calendar: DuckDB へ ON CONFLICT を使った upsert を行い冪等保存を実現。
  - リトライ/バックオフ:
    - 指数バックオフによるリトライ（最大3回）。対象ステータス: 408, 429, 5xx。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証トークン管理:
    - refresh_token から id_token を取得する get_id_token。
    - 401 受信時に自動で id_token をリフレッシュして1回のみリトライする仕組み。
    - ページネーション間での id_token キャッシュ共有。
  - データ取得時に fetched_at を UTC で付与（Look-ahead bias 防止、トレーサビリティ）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード収集・前処理・DB保存の実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の緩和）。
    - URL スキーム検証（http/https のみ許可）およびプライベートアドレス検出（SSRF 防止）。
    - リダイレクト時にもスキーム/プライベートホスト検査を行うカスタムリダイレクトハンドラ。
    - レスポンスの最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - テキスト前処理: URL 除去、空白正規化（preprocess_text）。
  - URL 正規化とトラッキングパラメータ削除（utm_* など）→ SHA-256 ハッシュ先頭32文字を記事IDとして生成。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用、新規挿入された記事IDの一覧を返す。トランザクションでまとめて処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（ON CONFLICT DO NOTHING RETURNING を利用）し、挿入件数を正確に返す。
  - 銘柄抽出: 正規表現による4桁銘柄コード抽出（known_codes によるフィルタリング、重複除去）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PRIMARY KEY / CHECK / FOREIGN KEY）を付与。
  - 代表的なインデックスを作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) による初期化（ディレクトリ自動作成を含む）と get_connection() を提供。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass による実行結果の集計（品質問題・エラーを含む）。
  - 差分取得ユーティリティ:
    - テーブルの最終取得日取得ヘルパー（get_last_price_date 等）。
    - 営業日調整ヘルパー (_adjust_to_trading_day)。
  - run_prices_etl の実装（差分再取得、backfill_days サポート、jquants_client 経由の取得と save 呼出し）。
  - 設計方針:
    - 差分更新／backfill による API 後出し修正吸収。
    - 品質チェックは検出しても ETL を継続（呼び出し元での判断を想定）。
    - id_token を注入可能にしてテスト容易性を確保。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS収集・外部アクセスに関する複数のセキュリティ対策を追加:
  - defusedxml を使用した安全な XML パース。
  - HTTP リダイレクト先のスキーム/ホスト検証（SSRF 対策）。
  - プライベート/ループバックアドレスへの接続拒否。
  - レスポンスサイズと gzip 解凍後サイズの上限設定（DOS対策）。
- J-Quants API クライアント側でのトークン自動リフレッシュは allow_refresh フラグにより無限再帰を防止。

### Performance / Reliability
- レートリミッタとリトライ（指数バックオフ）により API 呼び出しの安定性を確保。
- DuckDB 保存処理は ON CONFLICT / トランザクション / チャンク化を使い冪等性と効率を強化。
- fetch_* 系はページネーションをループ処理で安全に扱う（pagination_key 重複チェック）。

### Known issues / TODO
- pipeline.run_prices_etl 以外の ETL ジョブ（財務データ・カレンダーなど）の統合的なスケジュール/監視フローは今後実装予定。
- strategy / execution / monitoring の具体実装はまだプレースホルダが多く、発注ロジック・モニタリング周りは今後追加予定。
- 単体テスト・統合テストを拡充する必要あり（HTTP/外部API のモックや DuckDB のテストフィクスチャ等）。
- メトリクス収集・監視（Prometheus, Sentry 等）の統合も検討中。

### Breaking Changes
- なし（初回リリース）

---

（この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノート作成時はコミット履歴・リリース手順に基づいて適宜補正してください。）