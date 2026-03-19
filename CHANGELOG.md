# Changelog

すべての notable な変更をこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。設計方針として「ルックアヘッドバイアスの排除」「DuckDB を利用したローカルデータ管理」「外部 API 呼び出しの安全・冪等性確保」を重視しています。

### Added
- パッケージ初期構成
  - `kabusys` パッケージの基本エクスポートを追加（data, strategy, execution, monitoring）
  - バージョン `0.1.0` を設定

- 環境設定管理 (`kabusys.config`)
  - .env / .env.local 自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env パーサーの堅牢化（export プレフィックス対応、クォート処理、インラインコメント処理）。
  - OS 環境変数の保護（読み込み時に既存変数を protected として扱う）。  
  - 自動読み込み無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用）。
  - 必須設定を取得する `Settings` クラスを実装。プロパティ例:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 環境判定ユーティリティ（is_live / is_paper / is_dev）を提供

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装（/prices, /fins/statements, /markets/trading_calendar などの取得、ページネーション対応）。
  - レート制限制御（120 req/min）のための固定間隔スロットリング（RateLimiter）を実装。
  - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx をリトライ対象）を実装。
  - 401 Unauthorized を検出した場合、リフレッシュトークンから ID トークンを再取得して 1 回リトライする自動リフレッシュ機能を実装。
  - ページネーション間で共有するモジュールレベルのトークンキャッシュを実装。
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE を用いた upsert）:
    - save_daily_quotes -> `raw_prices`
    - save_financial_statements -> `raw_financials`
    - save_market_calendar -> `market_calendar`
  - 型変換ユーティリティ `_to_float`, `_to_int` を実装（不正値や空値を None として扱う）

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード収集と raw_news への冪等保存機能を実装（デフォルトに Yahoo Finance のビジネス RSS を含む）。
  - セキュリティ対策：
    - defusedxml を用いた XML パースで XML Bomb を防止
    - 最大受信バイト数制限（10MB）
    - URL 正規化／トラッキングパラメータ削除（utm_*, fbclid 等）
    - HTTP(S) スキーム以外の URL を拒否など SSRF 対策の考慮
  - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保
  - DB へのバルク挿入ではチャンク化を実施しパフォーマンスと SQL 長制限に配慮

- 研究用モジュール (`kabusys.research`)
  - ファクター計算（factor_research）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - Value（per, roe。raw_financials から最新の財務データを取得）
    - 全て DuckDB の prices_daily / raw_financials テーブルを参照する実装
    - SQL ウィンドウ関数を活用した高速集計
  - 特徴量探索（feature_exploration）:
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）
    - IC（Information Coefficient）計算（Spearman の ρ）とランク関数（ties は平均ランク処理）
    - factor_summary（count/mean/std/min/max/median を算出）
  - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装

- 戦略モジュール (`kabusys.strategy`)
  - 特徴量エンジニアリング（feature_engineering.build_features）:
    - research の生ファクター（momentum/volatility/value）を統合
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 選択カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ
    - features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性）
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみ使用
  - シグナル生成（signal_generator.generate_signals）:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - 各コンポーネントはシグモイド変換や逆転処理を適用して 0..1 にマップ
    - デフォルト重みは StrategyModel.md に従う（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ重みを受け付け、検証・正規化後に適用
    - final_score >= 0.60（デフォルト）で BUY シグナル生成。ただし Bear レジーム（ai_scores の regime_score 平均が負）では BUY を抑制
    - エグジット判定（SELL）:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - SELL は BUY より優先。signals テーブルへ日付単位の置換で保存（トランザクション）
    - 欠損データに対する保護（欠損コンポーネントは中立値 0.5 で補完、価格欠損時は SELL 判定をスキップ等）
    - ログと例外処理（トランザクションの ROLLBACK 時の警告等）

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- ニュース XML パースに defusedxml を利用し、XML ベースの攻撃を軽減
- RSS/URL 正規化、トラッキングパラメータ削除、受信サイズ制限等で外部入力の安全性向上
- J-Quants クライアントは 401 時のトークンリフレッシュを管理し、再試行中の無限ループを回避する仕組みを実装

### Known limitations / Notes
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date 等の追加が必要）。
- calc_value では PBR や配当利回りは未実装。
- NewsCollector の記事 ID は SHA-256 の先頭 32 文字を使用する仕様だが、将来的に変更する場合は互換性に注意。
- DuckDB テーブルスキーマ（features, signals, positions, raw_prices, raw_financials, ai_scores 等）はこの実装に合わせて事前に準備する必要がある。
- 外部 API（J-Quants）利用には有効なトークン（JQUANTS_REFRESH_TOKEN）が必要。

---

作成者: KabuSys 開発チーム（初期実装）