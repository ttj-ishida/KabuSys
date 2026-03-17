CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
形式は「Keep a Changelog」の慣習に準拠しています。

フォーマットの意味:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連の修正や強化

[Unreleased]
-------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-17
-------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ公開名 / エクスポート: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring

- 環境設定管理モジュール (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートの特定: .git または pyproject.toml を基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env 行パーサの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理
  - 環境変数取得ヘルパ（_require）と Settings クラスを提供
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須項目の明示
    - DUCKDB_PATH / SQLITE_PATH のデフォルト値処理
    - KABUSYS_ENV / LOG_LEVEL の入力値検証 (許容値チェック)
    - is_live / is_paper / is_dev の判定プロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - ベース機能:
    - API ベース URL とエンドポイントラッパー
    - get_id_token（refresh token から idToken を取得）
  - 信頼性/レート制御:
    - 固定間隔スロットリングでのレート制限実装（120 req/min）
    - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx を対象）
    - 401 受信時のトークン自動リフレッシュ（1回のみ）と再試行
    - モジュールレベルのトークンキャッシュ（ページネーション間で共有）
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（ページネーション対応）
    - fetch_financial_statements: 財務データ（四半期）取得（ページネーション対応）
    - fetch_market_calendar: JPX 市場カレンダー取得
    - 取得時のログ出力（取得件数）
  - DuckDB 保存関数（冪等性を確保）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - ON CONFLICT DO UPDATE を用いた重複更新、fetched_at に UTC タイムスタンプ記録
    - PK 欠損行のスキップと警告ログ
  - データ型変換ユーティリティ: _to_float, _to_int（安全なキャストを提供）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集処理（DEFAULT_RSS_SOURCES の定義を含む）
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ除去（utm_ 等）
    - URL 正規化後 SHA-256 の先頭32文字を記事IDに採用（冪等化）
  - セキュリティ・堅牢性:
    - defusedxml を利用した XML パース（XML Bomb 対策）
    - SSRF 対策（リダイレクト時のスキーム/ホスト検証、プライベートIP拒否）
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES=10MB、gzip 解凍後も検査）
    - 許可スキームは http/https のみ
  - テキスト前処理: URL 除去、空白正規化
  - DB 保存:
    - save_raw_news: チャンク分割による INSERT ... ON CONFLICT DO NOTHING RETURNING id を使った冪等保存（トランザクション内）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをチャンク・トランザクションで保存し、実際に挿入された件数を返す
    - 抽出ロジック: テキストからの4桁銘柄コード抽出（known_codes フィルタ）
  - run_news_collection: 複数 RSS ソースの統合収集ジョブ（ソース単位で独立したエラーハンドリング）

- DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層にまたがるテーブル定義を実装（DataSchema.md に準拠）
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約・型・チェック制約を明示
  - パフォーマンス向上のためのインデックス定義
  - init_schema(db_path): 親ディレクトリ自動作成、全DDLの適用（冪等）
  - get_connection(db_path): 既存 DB 接続を返すユーティリティ

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass: ETL 実行結果の構造化（品質問題・エラー収集を含む）
  - 差分更新・ヘルパ:
    - 最終取得日の取得ヘルパ (get_last_price_date / get_last_financial_date / get_last_calendar_date)
    - 営業日調整ヘルパ (_adjust_to_trading_day)
  - run_prices_etl（差分 ETL 実装の一部）:
    - 最終取得日からの差分取得、backfill_days による後出し修正吸収ロジック
    - jq.fetch_daily_quotes / jq.save_daily_quotes を利用した取得と保存
  - 設計方針メモ:
    - API 差分更新のデフォルト単位は営業日1日分
    - 品質チェック（quality モジュール）と ETL の連携を想定

Changed
- 初期リリースのため該当なし

Fixed
- 初期リリースのため該当なし

Security
- news_collector における SSRF 対策の実装:
  - リダイレクト時のスキーム検証、ホストのプライベートIP判定、初期 URL のホスト事前検証
  - defusedxml を用いた XML パースで外部攻撃耐性を向上
- HTTP レスポンスサイズ上限・gzip 解凍後サイズ検査によりメモリ DoS を軽減

Notes / Known limitations
- 環境変数未設定時は Settings._require により ValueError が発生します。README/.env.example に基づく設定が必要です。
- quality モジュールは pipeline から参照されていますが、品質チェックの具象実装（ルールや詳細な検出ロジック）は別モジュール側で実装される前提です。
- J-Quants API のレート制御は固定間隔スロットリング方式。必要に応じてより高精度なレート管理（トークンバケット等）に差し替え可能です。
- ニュース収集の既知コードリスト (known_codes) は外部で準備して注入する必要があります（run_news_collection の引数）。

参考
- バージョンはパッケージの __init__.py にて __version__ = "0.1.0" を使用しています。