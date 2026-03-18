# CHANGELOG

すべての注目すべき変更点をこのファイルで管理します。フォーマットは Keep a Changelog に準拠します。  

参考: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-18 (初回リリース)

### 追加
- パッケージの初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージ公開用 __init__.py を追加し、サブパッケージ data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは export KEY=val 形式、クォート文字・バックスラッシュエスケープ、行内コメントの扱いに対応。
  - Settings クラスを提供し、アプリ設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを持つ）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL を検証）
  - 必須環境変数未設定時は ValueError を送出することで早期検出。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得用 API クライアントを実装。
  - レート制限対応: 120 req/min（固定間隔スロットリングによる最小間隔制御）。
  - リトライロジック: 指数バックオフ（最大3回）。対象: 408/429/5xx およびネットワークエラー。
  - 401 受信時は ID トークンを自動でリフレッシュして 1 回だけリトライ（無限再帰防止）。
  - モジュールレベルで ID トークンをキャッシュしてページネーション間で共有。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes
    - fetch_financial_statements
    - fetch_market_calendar
  - DuckDB への保存関数（冪等設計、ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 取得時刻のトレース: fetched_at を UTC ISO8601 で記録（Look-ahead Bias 対策）。
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換ロジック）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュースを収集し raw_news / news_symbols に保存する ETL 機能を実装。
  - 設計上の主要機能:
    - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ先頭32文字を使用（冪等性確保）。
    - SSRF 対策:
      - RSS フェッチ時に HTTP リダイレクト先スキームの検証。
      - リダイレクト先ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否。
      - fetch 前に URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - RSS 取得処理: fetch_rss（例外は呼び出し元へ伝播、XML パース失敗時は警告ログと空リスト）。
    - 前処理: preprocess_text（URL 除去、空白正規化）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、実際に挿入された記事 ID を返却。チャンク挿入・単一トランザクション。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING + RETURNING 1）。
    - 銘柄コード抽出: 4桁の数字パターンのみを候補とし、known_codes に含まれるものだけを返す（重複除去）。
    - 高レベルジョブ run_news_collection: 複数 RSS ソースを個別に処理し、失敗ソースをスキップしつつ新規保存数を集計。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種 CHECK 制約、外部キー、主キーを含む堅牢な DDL。
  - パフォーマンスのためのインデックス定義（銘柄×日付・ステータス検索など）。
  - init_schema(db_path) を提供: ディスク上パスの親ディレクトリ自動作成、DDL とインデックスを実行して接続を返す。
  - get_connection(db_path) を提供: 既存 DB への接続取得（初期化は行わない）。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - 差分更新を行う ETL パイプライン基礎を実装:
    - 差分更新の判定ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーを用いた trading day 調整ヘルパー (_adjust_to_trading_day)。
    - run_prices_etl: 差分取得ロジック、バックフィル日数（デフォルト backfill_days=3）対応、J-Quants API からの取得→保存の実装（fetch -> save）。初回ロードの最小日付は 2017-01-01。
  - 結果表現用データクラス ETLResult を追加:
    - 取得数 / 保存数 / 品質問題 / エラーの集約
    - has_errors / has_quality_errors のプロパティ
    - to_dict により品質問題を (check_name, severity, message) 構造で返却
  - 品質チェックモジュール quality との連携を想定（品質チェックは ETL を止めず、呼び出し元が対応を決定）。

### セキュリティ
- RSS パーサ/フェッチ周りで複数の安全対策を導入:
  - defusedxml を使用して XML 攻撃を軽減。
  - SSRF 対策: リダイレクト時と最終 URL のホスト検証（プライベートアドレス拒否）、スキーム検証 (http/https のみ)。
  - レスポンスサイズ制限・Gzip 解凍後のチェックによるメモリ DoS / Gzip bomb 対策。
- J-Quants クライアントは 401 時の自動トークンリフレッシュを実装しつつも無限再帰を防止する設計。

### 既知の注意点 / 使用上のメモ
- .env の自動ロードはパッケージインポート時に行われる（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。テスト環境や特殊な起動方法では無効化を検討してください。
- Settings の必須プロパティ（トークンやSlack周り）は未設定だと ValueError を投げます。CI/実行環境では必ず設定してください。
- DuckDB 初期化は init_schema を明示的に呼ぶ必要があります（get_connection はスキーマ作成を行いません）。
- news_collector の extract_stock_codes は known_codes に依存するため、常に最新の有効銘柄リストを渡してください。

### 変更点なし（今後の課題）
- strategy, execution, monitoring サブパッケージは __init__.py を配置済みだが、当リリース時点では実装がない/限定的です。今後、戦略実装や注文実行ロジック、監視機能を追加予定。

---

今後のリリースでは、戦略実装、発注実行の接続（kabuステーション連携）、モニタリング（Slack 通知等）、品質チェックルールの明確化と自動修復オプションの追加などを予定しています。