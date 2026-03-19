# Changelog

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。

※このリポジトリは初回リリースとしてバージョン 0.1.0 を公開します。

## [0.1.0] - 2026-03-19

### Added
- パッケージ基盤
  - パッケージ初期化を追加（kabusys.__init__）。バージョンは 0.1.0、公開 API として data, strategy, execution, monitoring をエクスポート。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルや環境変数からの自動読み込みを実装。プロジェクトルートは __file__ を起点に .git または pyproject.toml で探索するため CWD に依存しない。
  - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）、および KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - export KEY=val 形式、クォート値内のエスケープやインラインコメント処理、コメント付き行の無視など堅牢な .env パーサを実装。
  - Settings クラスを提供し、必要な環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）やデフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV）を取得・検証するユーティリティを追加。
- Data 層（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。機能:
    - ID トークン取得（get_id_token）と自動リフレッシュ（401 の際に1回リトライ）。
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）。_RateLimiter 実装。
    - リトライ（指数バックオフ）、最大試行回数、429 の Retry-After 優先などの堅牢な HTTP エラーハンドリング。
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar のページネーション対応。
    - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、fetched_at に UTC タイムスタンプを付与、ON CONFLICT を使った冪等保存を行う。
    - 変換ユーティリティ (_to_float / _to_int) を提供し、不正データを安全に扱う。
- News 層（kabusys.data.news_collector）
  - RSS フィードからニュースを収集して raw_news に保存する処理（設計／ユーティリティ）を追加。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）および記事ID生成方針（正規化後の SHA-256 の先頭）を実装。
  - defusedxml を用いた安全な XML パース、HTTP/HTTPS チェック、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、バルク INSERT チャンク処理などセキュリティ・安定性対策を導入。
- Research 層（kabusys.research）
  - 研究用ファクター計算と探索ユーティリティを追加:
    - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）：prices_daily / raw_financials を参照し、モメンタム・ボラティリティ・バリュー系ファクターを計算。
    - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）：将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリー、ランク計算を標準ライブラリで実装。
  - 外部ライブラリ（pandas 等）に依存しない実装方針を採用。
- Strategy 層（kabusys.strategy）
  - feature_engineering.build_features:
    - research で計算した raw ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats を利用）し ±3 でクリップ、features テーブルに日付単位の置換（DELETE + bulk INSERT）で冪等に保存。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付け合算で final_score を計算。
    - weights の入力検証とデフォルト補完、合計が 1 でない場合のリスケール処理を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）により BUY シグナル抑制を実装。
    - BUY（閾値 default 0.60）・SELL（ストップロス -8% / final_score が閾値未満）シグナルの生成と signals テーブルへの日付単位置換を実装。
    - 既存ポジションの価格欠損時の警告スキップ、features に存在しない保有銘柄は score=0 として扱う等の安全策を導入。
- 公開 APIの整理
  - kabusys.strategy.__init__ で build_features / generate_signals をエクスポート。
  - kabusys.research.__init__ で主要研究用関数と zscore_normalize をエクスポート。

### Notes / Known limitations
- エグジット条件の未実装項目（strategy.signal_generator 内コメントで明記）
  - トレーリングストップ（ピーク価格管理）や時間決済（保有日数ベース）は未実装。positions テーブルに peak_price / entry_date が必要。
- DuckDB に依存する設計
  - 多くのモジュールは DuckDB 接続を前提としており、prices_daily / raw_financials / features / ai_scores / positions 等のテーブルスキーマが前提となる。
- NewsCollector
  - RSS のパース・ネットワークリソースに対する簡易的な安全対策は導入済みだが、外部フィードの多様性による例外ケースが発生する可能性がある。
- 自動環境読み込み
  - 自動ロードはプロジェクトルート検出に依存する。ルートが特定できない場合はスキップされる（テスト等で挙動を制御するため KABUSYS_DISABLE_AUTO_ENV_LOAD を提供）。

## Unreleased
- （なし）

--- 

開発者向け補足:
- 主要な設計方針として「ルックアヘッドバイアス防止」「冪等性」「本番 API への依存回避（研究用コード）」が一貫して採用されています。
- 今後の改善候補:
  - signal_generator の売買数最適化ロジック、ポジションサイズ計算、execution 層への統合テスト。
  - news_collector のより高度な自然文処理とシンボルマッチング。
  - モジュール間インタフェースの詳細ドキュメント化（テーブルスキーマ、NULL ポリシーなど）。