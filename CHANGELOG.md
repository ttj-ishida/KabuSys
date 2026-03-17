# CHANGELOG

すべての注目すべき変更はここに記録します。  
フォーマットは Keep a Changelog に準拠します。  

※このファイルはコードベースから推測して作成しています。

## [0.1.0] - 2026-03-17

### Added
- 初期リリース。KabuSys 日本株自動売買システムの基盤モジュールを追加。
- パッケージエントリポイント
  - src/kabusys/__init__.py: パッケージ名とバージョン（__version__ = "0.1.0"）を定義。公開サブパッケージとして data, strategy, execution, monitoring を指定。
- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - .env パーサ（クォート・エスケープ・インラインコメント・export プレフィックス対応）を実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを提供（J-Quants、kabuステーション、Slack、DBパス等のプロパティ）。KABUSYS_ENV と LOG_LEVEL の値検証を実装。
    - デフォルト DuckDB / SQLite パスの設定と Path 展開をサポート。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - 基本 API 呼び出しユーティリティ（_request）を実装。JSON デコードの検査、タイムアウト、ヘッダ管理を行う。
    - レート制限 (120 req/min) を固定間隔スロットリングで制御する _RateLimiter を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）、429 の Retry-After 対応を実装。
    - 401 発生時はリフレッシュトークンから id_token を自動更新して 1 回だけリトライする仕組みを実装（無限再帰防止の仕組みあり）。
    - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar の取得関数（ページネーション対応）を追加。
    - DuckDB への保存関数 save_daily_quotes, save_financial_statements, save_market_calendar を追加。ON CONFLICT DO UPDATE による冪等保存を実現し、fetched_at (UTC) を記録。
    - 型変換ユーティリティ _to_float / _to_int を提供（堅牢な変換ルールを実装）。
- ニュース収集モジュール
  - src/kabusys/data/news_collector.py:
    - RSS 取得・パース・正規化・DB保存の一連処理を実装。
    - RSS フェッチ fetch_rss:
      - URL 正規化（_normalize_url）、トラッキングパラメータ除去、記事ID を正規化 URL の SHA-256（先頭32文字）で生成。
      - defusedxml による XML パース（XML Bomb 対策）。
      - レスポンス最大サイズ (MAX_RESPONSE_BYTES=10MB) 制限、gzip 解凍後のサイズチェック（Gzip bomb 対策）。
      - リダイレクト時にスキーム/ホスト検査を行う専用ハンドラ (_SSRFBlockRedirectHandler) を使用し、内部ネットワークへのアクセスを防止。
      - link/guid のフォールバック、content:encoded の優先処理、pubDate の堅牢なパース（失敗時は現在時刻で代替）。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて実際に挿入された記事IDのリストを返す（チャンク処理、1トランザクション）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT で重複排除、INSERT RETURNING を利用）。
    - 銘柄コード抽出:
      - extract_stock_codes: 正規表現で 4 桁数字を候補抽出し、与えられた known_codes に基づき有効な銘柄のみ返す（重複除去）。
    - run_news_collection: 複数ソースの統合収集ジョブを実装。各ソースは独立エラーハンドリング。既定の RSS ソースとして Yahoo Finance ビジネスカテゴリを設定。
- DuckDB スキーマ管理
  - src/kabusys/data/schema.py:
    - Raw / Processed / Feature / Execution 層のテーブル定義を網羅（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
    - 各種制約（PRIMARY KEY、CHECK、外部キー）を定義し、データ整合性を明示。
    - 頻出クエリ向けのインデックス定義を提供。
    - init_schema(db_path) によりディレクトリ作成 → 全 DDL とインデックスを実行して DuckDB を初期化するユーティリティを実装（冪等）。
    - get_connection(db_path) を提供（初期化は行わない）。
- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py:
    - ETL の設計方針・流れに基づく差分更新ロジックを実装。
    - ETLResult dataclass: ETL 実行結果、品質チェック結果、エラー一覧を格納。to_dict() により監査用に変換可能。
    - 市場カレンダーヘルパー（_adjust_to_trading_day）やテーブル存在確認 / 最大日付取得ヘルパー（_table_exists, _get_max_date）を実装。
    - get_last_price_date, get_last_financial_date, get_last_calendar_date および run_prices_etl（差分取得／backfill 対応、J-Quants からの取得と保存）の骨組みを提供。
- その他
  - モジュール間でテスト容易性を考慮した設計（例: news_collector._urlopen をモック可能）。
  - 豊富なログ出力（info/warning/exception）を各所に追加し運用観察を容易に。

### Security
- RSS/XML処理におけるセキュリティ対策を導入
  - defusedxml を使用して XML による攻撃を軽減。
  - URL スキーム検証（http/https のみ許可）とプライベートアドレス拒否を実装し SSRF を防止。
  - リダイレクト時にもスキーム/ホストチェックを行う専用の redirect handler を導入。
  - レスポンスサイズ上限と gzip 展開後の検査を行い（Gzip Bomb 対策）、メモリ DoS を抑止。
- .env の読み込みは OS 環境変数を保護する仕組み（protected set）を採用。

### Changed
- （初期リリースのため過去バージョンからの変更はなし）

### Fixed
- （初期リリースのため既知のバグ修正はなし）

### Notes / Observations
- 多くの保存処理が DuckDB の ON CONFLICT / INSERT RETURNING を利用しており、冪等性と正確なインサート計測を重視した設計になっています。
- J-Quants クライアントはページネーション・レート制限・自動トークンリフレッシュ・堅牢なリトライ戦略を備え、運用向けの耐障害性を考慮しています。
- strategy/execution/monitoring の各サブパッケージがパッケージとして公開されていますが（__all__）、現状では空の __init__ が配置されており、各レイヤーの実装は今後追加される想定です。

---

今後のリリース案内（例）
- 0.2.0: strategy と execution の実装、発注フロー（kabuステーション連携）、監視アラートの追加
- セキュリティ改善/パフォーマンスチューニング等

（以上）