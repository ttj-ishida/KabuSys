# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
慣例: "Added", "Changed", "Fixed", "Security" 等のセクションで機能追加や修正点を記載しています。コードベースから推測できる実装内容・設計意図を元に記載しています。

## [Unreleased]

- 今後のリリースで予定される変更や改善点の記載用。

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システムのコア機能群を実装。

### Added
- パッケージ基礎
  - パッケージ名: kabusys。バージョン定義: 0.1.0。
  - モジュール公開API: data, strategy, execution, monitoring を __all__ で公開。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込み無効化可能。
  - .env の行パーサーは export 句、クォート文字列、インラインコメント、エスケープを考慮して安全にパース。
  - 環境変数の上書き制御（override と protected セット）をサポート。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの取得・検証を行うプロパティを実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得関数を実装:
    - fetch_daily_quotes: 日足（OHLCV）取得（ページネーション対応）
    - fetch_financial_statements: 財務データ取得（ページネーション対応）
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - 認証: refresh_token から id_token を取得する get_id_token を実装。モジュールレベルで id_token をキャッシュ。
  - HTTP リクエスト層に以下を実装:
    - 固定間隔のレートリミッタ（120 req/min）
    - リトライ（指数バックオフ, 最大 3 回）、対象ステータス/エラーに対する再試行ロジック（408/429/>=500、およびネットワークエラー）
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）と再試行
    - JSON デコード失敗時に明確な例外とログ
  - DuckDB への保存関数（冪等性を重視）:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials へ同様の冪等保存
    - save_market_calendar: market_calendar へ保存（HolidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を設定）
  - レコードの型変換ユーティリティ(_to_float, _to_int) を実装。誤った形式は None 扱いにすることで堅牢性を確保。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集パイプラインを実装:
    - fetch_rss: RSS 取得・パース（defusedxml を使用して XML Bomb 等を緩和）
    - preprocess_text: URL 除去・空白正規化
    - URL 正規化と記事ID生成: トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去。記事ID は正規化 URL の SHA-256（先頭32文字）を使用して冪等性を担保。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - ホストのプライベート/ループバック/リンクローカル/マルチキャスト判定（直接 IP と DNS 解決の両対応）
      - リダイレクト時にスキームとホストを検査するカスタム RedirectHandler を使用
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - raw_news テーブルへバルク挿入（INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、実際に挿入された記事IDを返す）。チャンク挿入で SQL 長制限に配慮。
    - news_symbols テーブルへの銘柄紐付けを一括保存する内部関数（重複除去・トランザクション化）。
    - 銘柄コード抽出関数 extract_stock_codes（4桁数字の抽出、既知コードセットとの照合、重複除去）。
    - run_news_collection: 複数 RSS ソースの統合収集ジョブ（各ソース個別にエラーハンドリングし失敗しても続行）。

- DuckDB スキーマ管理 (kabusys.data.schema)
  - DataPlatform 設計に基づくスキーマを定義・初期化:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 型チェック・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を付与してデータ整合性を担保
  - 頻出クエリ向けのインデックスを作成（例: code,date 検索用等）
  - init_schema(db_path) でディレクトリ作成・DDL 実行・接続返却、get_connection() で接続取得

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新を行う ETL ヘルパーとジョブを実装:
    - ETLResult dataclass: 実行結果、品質問題、エラー一覧などを格納・辞書化する to_dict() を実装
    - テーブル存在チェック・最大日付取得ユーティリティ
    - market_calendar を考慮した営業日調整関数 _adjust_to_trading_day
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - run_prices_etl: 差分更新ロジック（最終取得日の backfill 処理、_MIN_DATA_DATE を初回ロードの下限、jquants_client の fetch/save を利用）
  - 設計方針（コード内コメント）:
    - 差分更新・backfill により API の後出し修正に対応
    - 品質チェックは収集継続を優先し、呼び出し元が対処を決める

### Changed
- （初回リリースにつき無し）コード構成・設計に関する明確な設計原則と注釈を追加（レート制限、冪等性、SSRF対策、XML パース安全化、トランザクションまとめ挿入等）。

### Fixed
- （初回リリースにつき無し）既知のバグ修正履歴なし。

### Security
- ニュース収集で以下のセキュリティ対策を実装:
  - defusedxml を使った XML パースで XML Bomb や外部実行攻撃を緩和
  - SSRF 対策（スキーム制限、プライベートアドレス拒否、リダイレクト先検査）
  - レスポンスサイズ上限、gzip 解凍後検査による DoS 対策
- 環境ファイル読み込み時に OS 環境変数を保護する protected セットにより不要な上書きを回避

### Notes / Implementation details
- 多くの操作が DuckDB を前提としており、接続は duckdb.DuckDBPyConnection を使用する。
- SQL 文は ON CONFLICT / RETURNING を利用して冪等性と正確な挿入結果取得を行う（一部 DB の互換性に注意）。
- jquants_client のレート制御は固定間隔スロットリングで実装されているため、他プロセスとの共有を想定していない（プロセス内単一実装）。
- 日付やタイムゾーンの扱いに注意（RSS 日付は UTC に正規化して保存する等）。
- extract_stock_codes はベーシックな正規表現（4桁）を用いており、誤検出回避のため known_codes によるフィルタを推奨。

---

既存のコードから推測して作成した CHANGELOG です。より詳細な変更履歴／コミット単位の差分が必要であれば、リポジトリのコミットログやリリースノートを基に追記できます。