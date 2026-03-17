# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
初期リリースの内容はコードベースから推測して作成しています。

なお日付はリポジトリ内のバージョン（kabusys.__version__ == 0.1.0）を基に記載しています。

## [Unreleased]

## [0.1.0] - 2026-03-17

### Added
- パッケージ基本構成を追加
  - パッケージ名: kabusys、公開モジュール: data, strategy, execution, monitoring
  - バージョン: 0.1.0

- 環境設定モジュール (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート
  - .env パース機能の実装（export 形式、引用符内のエスケープ、インラインコメント処理等）
  - 環境変数取得ヘルパー `_require` と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須設定
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV
    - env の検証（development / paper_trading / live 等）
    - is_live / is_paper / is_dev のブールプロパティ

- J-Quants API クライアント (kabusys.data.jquants_client)
  - ベース機能:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）
    - 再試行ロジック（指数バックオフ、最大3回）と対象ステータス管理（408, 429, 5xx）
    - 401 受信時の自動トークンリフレッシュを1回行う仕組み（トークンキャッシュをモジュールレベルで保持）
    - ページネーション対応（pagination_key を用いた連続取得）
    - Look-ahead bias 対策として fetched_at を UTC で記録
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実装
  - API取得関数:
    - fetch_daily_quotes (日足 OHLCV)
    - fetch_financial_statements (四半期 BS/PL)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - 保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar （DuckDB への挿入／更新）
  - データ型ユーティリティ: _to_float, _to_int（厳密な変換・空値ハンドリング）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集パイプライン（DEFAULT_RSS_SOURCES に yahoo_finance を含む）
  - セキュリティと堅牢性:
    - defusedxml による XML パース（XML Bomb 等対策）
    - SSRF 対策: スキーム検証、ホストのプライベートアドレス判定、リダイレクトハンドラでの検査
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリDoS対策
    - gzip 解凍時のサイズ検証（Gzip bomb 対策）
  - URL 正規化: トラッキングパラメータ除去（utm_*, fbclid 等）、フラグメント削除、クエリをキーソート
  - 記事ID生成: 正規化URL の SHA-256 の先頭32文字（冪等性保証）
  - テキスト前処理: URL 除去、空白正規化
  - DuckDB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id（チャンク挿入、トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（RETURNING を使用し実際に挿入された件数を返す）
  - 銘柄抽出: 4桁数字（日本株）から既知コード集合に基づき抽出するユーティリティ extract_stock_codes
  - 集約ジョブ: run_news_collection（複数ソースの収集→保存→新規記事に対する銘柄紐付け）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層に分かれたテーブル群を定義
  - 主なテーブル: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions 等
  - 各テーブルのチェック制約、主キー、外部キーを定義
  - インデックス定義（頻出クエリのための index を作成）
  - init_schema(db_path): スキーマ初期化（ディレクトリ作成含む）と接続返却
  - get_connection(db_path): 既存 DB への接続取得

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - 差分更新設計（最終取得日からの差分取得、backfill_days による過去再取得）
  - 市場カレンダーの先読み（日数設定）
  - ETLResult dataclass による監査情報および品質問題 / エラー記録
  - DB ヘルパー: テーブル存在確認、最大日付取得、営業日調整関数
  - run_prices_etl の実装（差分算出 → fetch_daily_quotes → 保存（save_daily_quotes））を追加（差分ETLの基本フロー）

- その他
  - module-level logger の使用や詳細なログメッセージを各所に追加
  - テスト容易性を考慮した設計（_urlopen の差し替え、id_token 注入等）

### Security
- defusedxml を使用した XML パースにより XML 関連の脆弱性軽減
- RSS 取得時にスキーム検証、プライベートIP/ホスト検出、リダイレクト検査を実施し SSRF 対策を実装
- レスポンスサイズ制限と gzip 解凍後検証により DoS / Bomb 攻撃に対策

### Known issues / Notes
- run_prices_etl の戻り値がコード内では (取得数, 保存数) を期待する設計だが、現状の実装スニペットでは戻り値の組が不完全に見える箇所があります（取得数のみを返す/返却タプルが期待と一致しない可能性があるため、呼び出し側での確認・修正が必要）。（コードは途中で切れている可能性があるため、実装完了の確認を推奨）
- strategy / execution / monitoring パッケージは存在するが、今回のスナップショットでは具体的な実装が含まれていません（スケルトン状態）。
- J-Quants クレデンシャル等の必須環境変数未設定時は ValueError を送出するため、本番導入前に .env を準備してください。

---

変更履歴は今後のコミットで逐次更新してください。必要であれば各関数・モジュールごとの細かい変更点（関数シグネチャの差分・バグ修正など）を追加します。