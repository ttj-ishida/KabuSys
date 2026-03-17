# Changelog

すべての注目に値する変更をこのファイルに記載します。
このプロジェクトでは Keep a Changelog の形式に準拠しています。  
バージョニングは https://semver.org/ に従います。

## [0.1.0] - 2026-03-17

初回公開リリース。

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 高度な .env パーサ:
    - export KEY=val 形式に対応
    - シングル/ダブルクォートとバックスラッシュエスケープ処理
    - コメント (#) の取り扱い（クォート有無で挙動を区別）
  - Settings クラスを公開:
    - J-Quants / kabuステーション / Slack / DB パスなどのプロパティを提供
    - env（development/paper_trading/live）および log_level の入力検証
    - duckdb/sqlite のデフォルトパス設定（expanduser 対応）

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 通信の共通ユーティリティを実装
  - レート制限制御: 固定間隔スロットリング（120 req/min に合わせたインターバル）
  - 再試行ロジック: 指数バックオフ (最大 3 回)、リトライ対象ステータス (408, 429, 5xx)
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）と再試行
  - id_token キャッシュ（モジュールレベル）を共有してページネーションを効率化
  - ページネーション対応の取得関数:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (四半期財務)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ型変換ユーティリティ: _to_float, _to_int（安全な変換と不正値処理）
  - レスポンス JSON デコード失敗時の明示的エラー

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news へ保存する一連処理を提供
  - セキュリティおよび堅牢性のための対策:
    - defusedxml を利用した XML パース（XML Bomb 等の対策）
    - SSRF 対策: URL スキーム検証 (http/https のみ)、ホストのプライベートアドレス判定、リダイレクト時の検査ハンドラ
    - 受信制限: 最大受信バイト数（10 MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - User-Agent と Accept-Encoding ヘッダ対応
  - 記事 ID の冪等設計:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）
    - 正規化 URL の SHA-256 を用いた 32 文字 ID
  - テキスト前処理ユーティリティ:
    - URL 除去、空白正規化
  - DB 保存:
    - save_raw_news: チャンク INSERT + INSERT ... RETURNING id（実際に挿入された ID を返す）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの銘柄紐付け（重複除去、チャンク挿入、INSERT ... RETURNING を使用）
  - 銘柄コード抽出 (extract_stock_codes):
    - 4 桁数字パターンから既知の銘柄コードのみ抽出（重複除去）

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - DataSchema.md に基づくスキーマ定義を実装（Raw / Processed / Feature / Execution の 4 層）
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対するチェック制約（型・範囲チェック・NOT NULL）を設計
  - 外部キー制約とテーブル作成順を考慮
  - パフォーマンスを考慮したインデックス群を定義
  - init_schema(db_path) によりディレクトリ自動作成 → テーブル作成（冪等）
  - get_connection(db_path) による既存 DB への接続

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計方針とユーティリティを実装
  - ETLResult データクラス（品質問題やエラーの集約、シリアライズ用の to_dict を備える）
  - 差分更新用ユーティリティ:
    - _table_exists, _get_max_date
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
  - 市場カレンダーを用いた営業日調整: _adjust_to_trading_day
  - run_prices_etl: 差分取得・バックフィルロジック（最終取得日の backfill_days 前から再取得）と保存（jquants_client を利用）
  - ETL は品質チェック（quality モジュール）と組み合わせる設計（品質問題は収集を止めない）

### 変更 (Changed)
- （初回リリースのため変更履歴はありません）

### 修正 (Fixed)
- （初回リリースのため修正履歴はありません）

### セキュリティ (Security)
- RSS パーサに defusedxml を採用し、さらに SSRF 対策（スキーム検証・プライベートアドレス検査・リダイレクト検査）を実装。
- HTTP レスポンスの最大バイト数制限や gzip 解凍後のチェックを実装し、外部からのメモリ攻撃に対処。

### 備考 / マイグレーションノート
- DuckDB スキーマは init_schema を使って作成してください（初回作成時は親ディレクトリが自動生成されます）。
- 環境変数を .env に置く場合、プロジェクトルートの .env/.env.local が自動読み込みされます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止できます。
- J-Quants の認証トークン取得は settings.jquants_refresh_token を利用します。credentials が正しくない場合は get_id_token でエラーとなります。
- news_collector の extract_stock_codes は known_codes を参照して有効な 4 桁銘柄のみ抽出します。実運用では known_codes を最新化してお使いください。

---

今後のリリースでは、strategy / execution / monitoring モジュールの具体的実装（シグナル生成、発注処理、監視・アラート機能）、品質チェックモジュールの実装強化、ETL のジョブスケジューリングやテスト補強を予定しています。