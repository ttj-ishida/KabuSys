# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

- リリース日付は YYYY-MM-DD 形式で記載しています。
- バージョン番号はパッケージ内の __version__ と整合しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加しました。以下は本リリースで導入された主な機能・改善点・セキュリティ対策の概要です。

### Added
- 基本パッケージ初期化
  - src/kabusys/__init__.py: パッケージメタ情報と公開サブパッケージ（data, strategy, execution, monitoring）を定義。
- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイル（.env, .env.local）と OS 環境変数の自動読み込み（プロジェクトルートの検出 .git / pyproject.toml を基準）。
    - 複数形式の .env 行解析（export プレフィックス、クォートやエスケープ、インラインコメント処理）。
    - 上書き制御（override）と保護キー（protected）機構。
    - 必須環境変数取得ヘルパー（_require）と Settings クラス（J-Quants / kabu / Slack / DB / 環境モード等のプロパティ）。
    - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得の実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - レート制限（固定間隔スロットリング, 120 req/min）を守る RateLimiter 実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx に対応）。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）を実装。
    - ページネーション対応とモジュールレベルの ID トークンキャッシュ共有。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供し、ON CONFLICT を用いた冪等保存を実現。
    - 取得タイムスタンプ（fetched_at）を UTC で記録（Look-ahead bias 対策）。
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、空値・不正値時の安全な扱いを行う。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py:
    - RSS フィードから記事を収集して raw_news に保存する一連の機能（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
    - デフォルト RSS ソース（yahoo_finance）を提供。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
    - テキスト前処理（URL 除去、空白正規化）と pubDate の堅牢なパース。
    - defusedxml による XML パースで XML-Bomb 等の攻撃を防止。
    - レスポンス上限（MAX_RESPONSE_BYTES=10MB）、gzip 解凍後サイズ検証、Content-Length の事前チェックによるメモリ DoS 対策。
    - SSRF 対策（http/https 限定、プライベート IP/ループバック判定、リダイレクト時の事前検査用ハンドラ _SSRFBlockRedirectHandler）。
    - DB へのバルク INSERT はチャンク化（_INSERT_CHUNK_SIZE）してトランザクションで実行、INSERT ... RETURNING により実際に挿入されたレコードを返却。
    - 銘柄コード抽出ユーティリティ（extract_stock_codes、4桁数字 + known_codes フィルタ）。
- スキーマ定義・DB 初期化
  - src/kabusys/data/schema.py:
    - DuckDB 向けのスキーマ定義を追加（Raw / Processed / Feature / Execution 層）。
    - 各種テーブル（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）を含む DDL を定義。
    - インデックス定義（頻出クエリ用）を追加。
    - init_schema(db_path) によりディレクトリ作成→DDL 実行→インデックス作成を行い DuckDB 接続を返す。get_connection() で既存 DB に接続可能。
- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py:
    - ETL 結果を表す ETLResult dataclass（品質問題・エラー集約・シリアライズ用 to_dict）。
    - 差分取得に必要なヘルパー（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 市場カレンダーを用いた営業日調整ヘルパー（_adjust_to_trading_day）。
    - run_prices_etl: 差分更新ロジック（最終取得日から backfill 日数分さかのぼる／_MIN_DATA_DATE で初回ロード対応）、jquants_client を使った取得→保存フローを実装。
- その他
  - 複数モジュールで詳細なログ出力を実装し運用観測性を向上。

### Changed
- （初回リリースのため該当なし）

### Fixed
- データ変換の堅牢化:
  - _to_int の実装で "1.0" のような文字列を float 経由で整数変換し、小数部が存在する場合は None を返すことで意図しない切り捨てを回避。
- RSS パース / URL 正規化周りの堅牢化（フラグメント除去、クエリソート、トラッキングパラメータ除去）。

### Security
- RSS/XML の安全化:
  - defusedxml を利用して XML 関連の脆弱性（XML Bomb 等）を緩和。
  - fetch_rss / _urlopen で SSRF 対策: スキーム検証、ホストのプライベートアドレス判定、リダイレクト先の事前検査。
- 環境変数の扱い:
  - OS 環境変数を保護する protected 機構を導入し、.env により意図せず既存の OS 環境を上書きしないデフォルト挙動を採用。自動読み込みを無効化するフラグを用意。

### Performance
- API レート制御:
  - 固定間隔スロットリング（_RateLimiter）で J-Quants API のレート制限を守り、スロットリングによる安定性を確保。
- DB 書き込み最適化:
  - バルク INSERT のチャンク化、1 トランザクション内での処理、INSERT ... RETURNING による不要な再読込軽減。
- ページネーション対応で無駄な走査を低減。

### Documentation
- 各モジュールに docstring を追加して設計意図・利用方法・安全上の注意を明記（config, jquants_client, news_collector, schema, pipeline 等）。

### Removed / Deprecated
- （初回リリースのため該当なし）

---

開発者向けメモ:
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。
- 今後の作業候補:
  - pipeline.run_prices_etl の継続実装（financials / calendar ETL、品質チェック quality モジュールとの連携）。
  - strategy / execution / monitoring サブパッケージの実装充実（現在は __init__ のみ）。
  - 単体テスト・統合テストの追加（ネットワーク周りはモック差し替えを想定した設計）。
  - ドキュメント（運用手順、データスキーマ仕様、環境変数一覧 .env.example）の整備。

以上。