CHANGELOG
=========

すべての注目すべき変更点をこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-18
------------------

Added
- 初期リリースを追加。
- パッケージ構成
  - kabusys パッケージの基本構造を追加（data, strategy, execution, monitoring を __all__ に公開）。
  - バージョン: 0.1.0（src/kabusys/__init__.py）
- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local からの自動読み込み機能を実装（読み込み優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - 複数の .env フォーマットに対応（export プレフィックス、クォート、コメント処理など）。
  - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - 必須環境変数取得用 _require と Settings クラスを提供。
  - Settings にて必須項目 / デフォルト値 / 値検証を含むプロパティを実装:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（有効値: development, paper_trading, live）およびログレベル検証
    - is_live / is_paper / is_dev 補助プロパティ
- Data モジュール（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - リトライ戦略（最大 3 回、指数バックオフ、408/429/5xx 対象）。
    - 401 受信時は自動トークンリフレッシュを試行（1 回のみ）し、その後再試行。
    - ID トークンのモジュールレベルキャッシュと強制更新機能。
    - DuckDB への冪等保存メソッド（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE で重複排除）。
    - 数値変換ユーティリティ _to_float / _to_int（堅牢なパースと不正値処理）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead bias 対策に配慮。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードからのニュース収集と DuckDB への保存ワークフローを実装。
    - セキュリティ指向の設計:
      - defusedxml による XML パース（XML Bomb 等対策）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、プライベートアドレスの検出拒否、リダイレクト時の事前検査（カスタム RedirectHandler）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ確認（Gzip bomb 対策）。
      - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成し冪等性を担保（utm_ 等のトラッキングパラメータを除去して正規化）。
    - RSS 取り込みパイプライン:
      - fetch_rss：RSS 取得、前処理（URL 除去、空白正規化）、pubDate の解析（UTC へ正規化）。
      - save_raw_news：チャンク INSERT + INSERT ... RETURNING を用いた新規挿入 ID の取得、トランザクションで処理。
      - save_news_symbols / _save_news_symbols_bulk：news と銘柄コード紐付けを冪等に保存（チャンク・トランザクション処理）。
      - extract_stock_codes：本文から 4 桁銘柄コードを抽出（既知銘柄セットでフィルタ・重複除去）。
      - run_news_collection：複数ソースの収集ジョブを実装（個々のソースは独立してエラーハンドリング）。
    - テスト容易性: _urlopen を差し替え可能にして外部ネットワーク依存をモック可能。
  - スキーマ定義（src/kabusys/data/schema.py）
    - DuckDB 用の DDL を定義（Raw / Processed / Feature / Execution 層の考え方）。
    - raw_prices, raw_financials, raw_news 等の CREATE TABLE 文を含む（型・制約・PK 定義付き）。
    - 初期化用途のスキーマ管理基盤を提供。
- Research モジュール（src/kabusys/research）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns：指定日に対する各ホライズンの将来リターンを DuckDB の prices_daily を参照して計算（複数ホライズンを一度に取得、ホライズン検証）。
    - calc_ic：ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効ペア < 3）や分散ゼロ時は None を返す。
    - rank：同順位は平均順位でランク化（丸めで ties 検出を安定化）。
    - factor_summary：各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで計算（None は除外）。
    - 設計上、DuckDB の prices_daily テーブル以外にはアクセスせず、本番発注 API には影響しない。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum：mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算（LAG / AVG ウィンドウ関数使用、データ不足時は None）。
    - calc_volatility：20 日 ATR（平均 true range）、ATR 比率、20 日平均売買代金、出来高比率を計算（真の true_range の NULL 伝播に配慮）。
    - calc_value：raw_financials の最新財務データと当日の株価を組み合わせて PER / ROE を計算（EPS 0/NULL の場合は PER を None）。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API にはアクセスしない設計。
  - research/__init__.py で主要関数群をエクスポート（zscore_normalize は data.stats からインポート）。
- その他
  - テストフレンドリーな設計箇所を各所に用意（例: RSS の _urlopen の差し替え、KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - ロギング（logger）を各モジュールに追加し、処理状況や警告を詳細に出力。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- RSS 収集における SSRF 対策、defusedxml による XML パース、安全なレスポンスサイズチェック等を実装。
- J-Quants API クライアントでのトークン取り扱いやリトライ制御に注意（401 リフレッシュは限定的に実行）。

Deprecated
- なし

Removed
- なし

Breaking Changes
- なし（初回リリース）

利用上の注意（ユーザー向け）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。未設定時は Settings のプロパティアクセスで ValueError が発生します。
- DuckDB / SQLite のデフォルトパス:
  - DUCKDB_PATH: data/kabusys.duckdb（expanduser 対応）
  - SQLITE_PATH: data/monitoring.db
- .env 自動読み込み:
  - プロジェクトルートが見つかる場合にのみ .env/.env.local を自動読み込みします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- RSS ニュース収集:
  - デフォルト RSS ソースは yahoo_finance（business カテゴリ）に設定されていますが、run_news_collection の引数で上書き可能です。
- テスト:
  - ネットワーク依存部分（_urlopen 等）はモック差し替え可能に実装してあります。

既知の制約 / TODO
- schema.py の実装は主要な Raw テーブルを含みますが、Execution 層や一部の DDL がファイル内で切れている箇所が見られます（今後の拡張/完成予定）。
- data.stats.zscore_normalize の実装はここに含まれていませんが、research パッケージから参照されています（別ファイルでの提供を想定）。

-- End of CHANGELOG --