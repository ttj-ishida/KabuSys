# Changelog

すべての notable な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の仕様に従います。  
バージョン番号は SemVer に従います。

## [0.1.0] - 2026-03-19

初回リリース。

### Added
- パッケージ初期構成
  - パッケージルート: kabusys (バージョン `0.1.0`)。
  - 公開 API: `kabusys.strategy.build_features`, `kabusys.strategy.generate_signals` など主要関数を __all__ で公開。

- 環境設定 / 設定読み込み
  - settings 管理クラス（kabusys.config.Settings）を実装。
  - .env 自動読み込み機能:
    - プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動ロード（環境変数が存在する場合は上書き制御）。
    - 環境変数自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ (`_parse_env_line`) はコメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート。
  - 必須環境変数チェック `_require` と `Settings` の多くのプロパティを提供（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、実行環境・ログレベル検証等）。
  - `KABUSYS_ENV` / `LOG_LEVEL` の検証（許容値チェック）と補助プロパティ（is_live / is_paper / is_dev）。

- データ取得・保存（J-Quants）
  - J-Quants API クライアント（kabusys.data.jquants_client）実装:
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象。
    - 401 受信時はリフレッシュトークンを用いて自動的に ID トークンを更新して 1 回リトライ。
    - ページネーション対応（pagination_key）。
    - 取得時刻（fetched_at）を UTC ISO8601 で保存し、look-ahead バイアスのトレースをサポート。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。ON CONFLICT による冪等保存。
    - 入力変換ユーティリティ `_to_float` / `_to_int` を提供（堅牢な型変換 / 欠損処理）。

- ニュース収集
  - RSS ニュース収集モジュール（kabusys.data.news_collector）実装:
    - RSS フィード取得 → 正規化（URL トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント削除、クエリソート）→ raw_news へ冪等保存。
    - セキュリティ対策: defusedxml による XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）、HTTP/HTTPS スキーム検証、SSRF の緩和を意識した設計。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - バルク挿入チャンク化（_INSERT_CHUNK_SIZE）。

- リサーチ / ファクター計算
  - 研究用モジュール（kabusys.research.*）を実装:
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。データ不足時は None を扱う。
      - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
      - calc_value: raw_financials と当日の株価を組み合わせて PER / ROE を計算（財務データは target_date 以前の最新を使用）。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを効率的に取得。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None を返す。
      - factor_summary / rank: 基本統計量とランク付けユーティリティを提供。
    - 全リサーチ関数は DuckDB の prices_daily / raw_financials を参照し、本番 API への依存なし。

- 特徴量エンジニアリング
  - strategy.feature_engineering.build_features を実装:
    - research モジュールが算出した生ファクターを取得しマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコアで正規化し ±3 でクリップ（_NORM_COLS）。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで実行）して冪等性を確保。

- シグナル生成（戦略）
  - strategy.signal_generator.generate_signals を実装:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完。
    - デフォルト重みは StrategyModel.md の定義に準拠（momentum 0.40 等）。ユーザー指定 weights を受け付け、検証・正規化（合計 1.0 にスケール）。
    - final_score に基づく BUY シグナル（デフォルト閾値 0.60）と、保有ポジションに対する SELL（エグジット）判定を実装。
      - SELL 条件にストップロス（-8%）とスコア低下を含む。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合に BUY を抑制。
    - signals テーブルへ日付単位置換（トランザクション＋バルク挿入）で冪等性を保証。
    - SELL 判定は BUY より優先し、BUY から除外後にランクを再付与。

- ロギングとエラーハンドリング
  - 各モジュールにおいて警告ログ・情報ログを適切に出力。トランザクション失敗時は ROLLBACK を試み、失敗ログを記録。

- その他ユーティリティ
  - データ操作における NULL / NaN / 非有限値の扱いに配慮した実装（math.isfinite 等を使用）。
  - DuckDB を中心とした SQL クエリ設計（ウィンドウ関数等を活用）で効率的に集計・ラグ取得を実装。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / 設計・セキュリティ上の注記
- Look-ahead バイアス対策:
  - すべての計算・シグナル生成は target_date 時点で利用可能なデータのみを使用する設計（fetched_at の記録等を利用）。
- 冪等性:
  - 各種保存処理は基本的に ON CONFLICT / 日付単位 DELETE+INSERT を用いて冪等に動作するように設計。
- セキュリティ:
  - RSS パーサで defusedxml を利用、受信サイズ制限、URL 正規化によるトラッキングパラメータ削除等を実装。
- 未実装（今後の改善候補）:
  - signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の情報が必要で未実装。
  - news_collector の完全な SSRF 対策（IP アドレスブロック検査等）は限定的に実装されており、強化の余地あり。

如果他に CHANGELOG に記載してほしい粒度（例: もっと技術的な SQL クエリの要約や各関数の公開 API シグネチャ一覧など）があれば指示ください。