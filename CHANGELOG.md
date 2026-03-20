# CHANGELOG

すべての変更は Keep a Changelog の形式に従い記載しています。  
現在のバージョンは src/kabusys/__init__.py の __version__ に合わせて 0.1.0 としています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-20

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API に data, strategy, execution, monitoring を含む（__all__）。
  - バージョン情報: 0.1.0。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルや環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルートの検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント、コメント扱いの判定などをサポート。
  - .env と .env.local の読み込み順（OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - Settings クラスを提供し、必須環境変数取得（_require）や値検証（KABUSYS_ENV、LOG_LEVEL）、パス（duckdb/sqlite）の Path 変換などを実装。
  - 環境変数の上書き保護（protected set）に対応。

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。株価日足・財務データ・マーケットカレンダーの取得関数を提供（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
  - ページネーション対応、モジュールレベルでの ID トークンキャッシュ、get_id_token による自動トークン取得。
  - API レート制御: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
  - リトライロジック: 指数バックオフ、最大3回、408/429/5xx を再試行対象。429 の場合は Retry-After 優先。
  - 401 発生時はトークンを1回自動リフレッシュしてリトライするロジックを実装（無限再帰回避）。
  - DuckDB への冪等保存関数を実装（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT を用いた UPSERT、fetched_at の UTC 記録。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し不正データを安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集モジュールを実装（デフォルトに Yahoo Finance）。
  - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）を実装し、記事 ID を正規化 URL の SHA-256 で生成して冪等性を確保。
  - XML パースに defusedxml を使用して XML ベースの攻撃を防止。
  - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、HTTP スキーム検証、メモリ DoS 対策を実装。
  - raw_news / news_symbols などへのバルク挿入を想定したチャンク処理を実装（_INSERT_CHUNK_SIZE）。

- リサーチモジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日移動平均乖離率）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - データ不足時には None を返す等の堅牢化。
  - 特徴量探索・統計（kabusys.research.feature_exploration）
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、ホライズンの検証、単一クエリで取得）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのρ、サンプル閾値チェック、結合ロジック）。
    - 基本統計量 factor_summary、ランク変換 rank（同順位は平均ランク、丸めで ties 検出の安定化）。
  - zscore_normalize を kabusys.data.stats から re-export（パッケージ内で利用）。

- 戦略モジュール（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research の生ファクターを用いてユニバースフィルタ（最低株価、最低平均売買代金）、Zスコア正規化、±3 でのクリップを行い features テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性確保）。
    - 欠損値や休場日対応のため target_date 以前の最新価格を参照する実装。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算し重み付けして final_score を算出。
    - デフォルト重みと閾値（_DEFAULT_WEIGHTS/_DEFAULT_THRESHOLD）を実装。ユーザー重みの検証・補完・再スケール処理を実装。
    - Sigmoid 変換、欠損コンポーネントは中立値（0.5）で補完、Z スコアは ±3 クリップに合わせた扱いを採用。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合）による BUY シグナル抑制。
    - 保有ポジションのエグジット判定（ストップロス -8% およびスコア低下）を実装し SELL シグナルを生成。positions / prices_daily を参照。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）。
    - 最終的に生成した BUY/SELL 合計数を返す。

- その他ユーティリティ
  - 乱数や外部依存を最小化した設計、DuckDB に対する SQL クエリの実装、操作ログ（logger）を多所に埋め込み。

### Security
- ニュース XML パースに defusedxml を使用し XML 関連の脆弱性を低減。
- RSS の URL 正規化でトラッキングパラメータを削除し、一意 ID の衝突やトラッキングパラメータによる偽造を軽減。
- .env 読み込みは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテスト時に環境汚染を防止。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Notes / Implementation details
- 多くの DB 操作は「日付単位で削除してから挿入する」方式（置換）で冪等性を保証している（features / signals 等）。
- J-Quants クライアントは 401 → トークンリフレッシュ → 再試行の流れを組み込み、ページネーション中もトークンを共有して効率化している。
- 計算ロジック（Z スコア正規化、sigmoid、ランク付け、IC 計算等）は、外部依存（pandas 等）を使わず純 Python / DuckDB SQL で実装されているため軽量に動作する想定。

もしリリースノートを別の粒度（より高レベル／より詳細な関数単位）で出力したい場合は、その旨と希望のフォーマット（例: リリース概要 + 影響箇所の一覧）を教えてください。