# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しています。主にデータ収集・保存、リサーチ（ファクター計算・探索）、特徴量エンジニアリング、シグナル生成、環境設定の取り扱いに関するモジュールを提供します。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名とバージョン（0.1.0）、公開モジュール一覧を定義。

- 環境変数・設定管理
  - src/kabusys/config.py:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みする仕組みを実装（CWD に依存しない）。
    - .env パーサ実装（export 形式、引用符対応、インラインコメント処理などに対応）。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須変数チェック（_require）を提供し、設定されていない場合は ValueError を送出する。
    - Settings クラスで主要設定項目をプロパティ提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV 検証（development/paper_trading/live のみ許容）
      - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
      - is_live / is_paper / is_dev ヘルパー

- データ取得・保存（J-Quants API）
  - src/kabusys/data/jquants_client.py:
    - API クライアント実装。ベース URL、ページネーション対応の fetch 関数を提供:
      - fetch_daily_quotes（株価日足、ページネーション対応）
      - fetch_financial_statements（四半期財務、ページネーション対応）
      - fetch_market_calendar（JPX カレンダー）
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）、HTTP 408/429/5xx に対するリトライ対応。
    - 401 応答時はトークンを自動リフレッシュして1回リトライする実装（get_id_token と統合）。
    - 保存関数（DuckDB へ冪等保存）:
      - save_daily_quotes -> raw_prices（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar（ON CONFLICT DO UPDATE）
    - ペイロードの整形・型変換ユーティリティ: _to_float / _to_int
    - fetched_at に UTC タイムスタンプを記録して「データ取得時点」をトレース可能に。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィードから記事を取得し raw_news へ冪等保存する処理設計。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を利用して冪等性を確保する方針を採用。
    - text 前処理（URL 除去・空白正規化）、トラッキングパラメータ削除と URL 正規化実装（_normalize_url）。
    - セキュリティ対策: defusedxml を利用して XML Bomb 等を防止、HTTP(S) スキーム以外の URL 拒否、受信サイズ制限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策。
    - バルク INSERT のチャンク処理実装（_INSERT_CHUNK_SIZE）で DB 負荷を抑制。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py:
    - ファクター計算関数を実装（prices_daily / raw_financials のみ参照）:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA を考慮、データ不足時は None）
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR の NULL 伝播に注意）
      - calc_value: per, roe（raw_financials の最新レコードを結合）
    - 各関数は date, code をキーとする dict リストを返す設計。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: ランク相関（Spearman の ρ）を計算するユーティリティ（有効レコードが 3 件未満は None）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクとするランク付け実装（丸めによる ties 対策あり）。
  - src/kabusys/research/__init__.py: 主要関数を公開。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py:
    - build_features(conn, target_date):
      - research で計算した生ファクター（calc_momentum / calc_volatility / calc_value）を取得。
      - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20 日平均売買代金 _MIN_TURNOVER=5e8 円）を適用。
      - 指定数値カラムを zscore_normalize（kabusys.data.stats）で正規化、±3 でクリップして外れ値影響を抑制。
      - features テーブルへ日付単位で置換（DELETE -> INSERT、トランザクションで原子性確保）し、冪等性を保つ。
    - ユニバースフィルタは当該日以前の最新終値を参照して休場日対応。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py:
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features と ai_scores を用いて各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - コンポーネントはシグモイド変換・平均化等により 0〜1 に正規化し、重み付け合算で final_score を算出（デフォルト重みは StrategyModel 準拠）。
      - weights 引数は検証・補完（既知キーのみ受け入れ、非数値や負値は無視）、合計が 1.0 となるようリスケール。
      - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY を抑制、サンプル数閾値あり）。
      - BUY シグナル: final_score >= threshold（デフォルト 0.60）、ランク付けを付与。
      - SELL シグナル（エグジット判定）:
        - ストップロス: (close / avg_price - 1) < -0.08（-8%）
        - final_score が threshold 未満（score_drop）
        - 価格欠損時の SELL 判定スキップや features 未登録の保有銘柄は warning 出力のうえ final_score=0 として扱う方針。
      - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
      - 関数は書き込んだシグナル数（BUY + SELL）を返す。

- strategy パッケージ公開
  - src/kabusys/strategy/__init__.py: build_features, generate_signals を公開。

### Security
- ニュース収集:
  - defusedxml を利用し XML 関連の攻撃（XML bomb 等）に対処。
  - RSS や記事に含まれる URL の正規化でトラッキングパラメータを除去し、ID 生成の冪等性を向上。
  - HTTP/HTTPS 以外のスキームを拒否し SSRF リスクを低減。
  - 受信バイト上限（MAX_RESPONSE_BYTES）を設定しメモリ DoS を防止。

- データ取得:
  - J-Quants API 呼び出しでレート制限を守る実装により外部 API に対して安全にアクセス。
  - 401 発生時のトークン自動リフレッシュは allow_refresh 制御により無限再帰を回避。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Migration
- 環境変数:
  - 本リリースでは JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / KABU_API_PASSWORD などの環境変数が必須です。未設定の場合は Settings のプロパティアクセス時に ValueError が発生します。
  - 自動的に .env/.env.local をプロジェクトルートから読み込みますが、テストなどで自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- データベース:
  - デフォルトの DuckDB パスは data/kabusys.duckdb、SQLite は data/monitoring.db です。settings.duckdb_path / settings.sqlite_path を利用して上書き可能です。
- DuckDB スキーマ:
  - 本コードは raw_prices / raw_financials / market_calendar / prices_daily / raw_financials / features / ai_scores / positions / signals 等のテーブルを参照・更新します。実行前に期待するスキーマを準備してください（テーブル定義はドキュメントを参照）。

---

（補足）本 CHANGELOG はソースコードから機能・設計意図を推測して作成しています。実際のリリースノートとして公開する場合は、利用環境や追加変更点に合わせて追記・修正してください。