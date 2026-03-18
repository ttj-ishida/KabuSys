# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

なお、このCHANGELOGはソースコードから実装内容を推測して作成しています。

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買プラットフォームのコアモジュール群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開モジュール指定）。
  - サブパッケージ骨組み: data, strategy, execution, monitoring。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルート自動検出（.git / pyproject.toml ベース）により CWD に依存しない読み込みを実現。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、コメント処理（クォートあり/なしでの挙動差異）。
  - Settings クラスを導入（settings インスタンスを公開）。
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供。
    - 必須変数未設定時は ValueError を発生させる _require 実装。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーション。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装（_request）。
    - レート制限（120 req/min）を厳守する固定間隔スロットリング（_RateLimiter）。
    - 再試行ロジック：指数バックオフ、最大再試行回数 3 回、対象ステータス (408, 429, 5xx)。
    - 401 受信時は自動でリフレッシュトークンを使って id_token を更新して 1 回リトライ（無限再帰回避）。
    - id_token キャッシュ機構（モジュールレベル）によりページネーション間でトークンを共有。
  - 認証ヘルパー: get_id_token（リフレッシュトークンから id_token 取得）。
  - データ取得関数（ページネーション対応）:
    - fetch_daily_quotes（株価日足: OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
    - 取得時に fetched_at を記録する設計方針（Look-ahead Bias 対策を想定）。
  - DuckDB への保存関数（冪等性を意識）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE による冪等挿入、PK 欠損レコードのスキップと警告ログ記録。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集パイプラインを実装。
  - セキュリティ・堅牢化:
    - defusedxml を用いた XML パースで XML Bomb 等を防御。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベート/ループバック判定、リダイレクト時の検査（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - User-Agent / Accept-Encoding ヘッダ設定。
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid, gclid, ref_, _ga）除去、クエリソート、フラグメント削除、小文字化等。
    - 正規化 URL の SHA-256（先頭32文字）を記事IDとして生成し、冪等性を担保。
  - テキスト前処理: URL 除去、空白正規化。
  - DB 保存ロジック（DuckDB）:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、新規に挿入された記事IDのみを返す。チャンク挿入と単一トランザクションでのコミット/ロールバックを実装。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルクで保存（ON CONFLICT DO NOTHING + INSERT RETURNING による正確な挿入数取得）。
  - 銘柄コード抽出: 4桁数字パターンから既知銘柄セットにマッチするものを抽出（重複排除）。
  - run_news_collection: 複数 RSS ソースを順に処理し、各ソースは独立してエラー処理。新規記事の銘柄紐付けをまとめて保存。

- DuckDB スキーマ定義 / 初期化 (kabusys.data.schema)
  - DataSchema.md に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 列制約（CHECK, NOT NULL, PRIMARY KEY, FOREIGN KEY）を含むDDLを提供。
  - クエリパフォーマンスを考慮した索引を作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) によりディレクトリ自動生成とテーブル・インデックス作成を行う。get_connection は既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass: ETL 実行のメタ情報と品質問題 / エラー集約を保持。to_dict によりシリアライズ可能。
  - 差分更新支援ユーティリティ:
    - _table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - 市場カレンダーに基づく営業日補正: _adjust_to_trading_day 実装（カレンダー未取得時はフォールバック）。
  - run_prices_etl（株価差分 ETL）を実装（差分算出、バックフィル日数考慮、J-Quants 呼び出し、保存呼び出し）。設計方針として backfill_days による数日前からの再取得で API の後出し修正を吸収する。

### Changed
- n/a（初回リリースのため変更履歴はありません）

### Fixed
- n/a（初回リリースのため修正履歴はありません）

### Security
- ニュース収集での SSRF 対策、defusedxml による XML パース保護、レスポンスサイズ制限、URL スキームフィルタにより外部入力の悪用を軽減。

### Notes / Migration
- DB 初期化: 新規で利用する際は kabusys.data.schema.init_schema(db_path) を実行してスキーマを作成してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などが Settings 経由で参照されます。未設定時は ValueError になります。
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。
- テスト容易性:
  - news_collector._urlopen をモック差替え可能（ネットワーク呼び出しのテスト容易化）。
  - jquants_client の id_token 注入によりテスト時のトークン固定が可能。

### Known limitations / TODOs
- run_prices_etl の戻り値処理・パイプラインの品質チェック統合は継続実装の余地あり（品質チェックモジュール quality との連携を期待する設計）。
- strategy, execution, monitoring パッケージは骨組みのみで、実際のトレーディングロジックや発注統合は今後実装予定。
- API クライアントのエラーログやメトリクス収集（監視・アラート連携）は拡張の余地あり。

---

今後のリリースでは ETL の完全実装、戦略モジュール、発注実行モジュール（kabuステーション連携）の追加、より詳細な品質チェックとモニタリング機能の追加を予定しています。