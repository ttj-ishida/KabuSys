# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠しており、セマンティックバージョニングを採用しています。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買（KabuSys）システムのコア機能群を実装しました。設計上の方針として、ルックアヘッドバイアス回避、冪等性（idempotency）、DuckDB ベースのローカルデータ処理、外部 API へのレート制御・リトライ、セキュリティ対策（XML/SSRF/メモリDoS等）を重視しています。

### Added
- パッケージ基礎
  - src/kabusys/__init__.py に __version__ と公開 API を定義。
- 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数からの設定読み込み機能を実装。
    - プロジェクトルート検出（.git または pyproject.toml を探索）に基づく自動 .env ロード。
    - .env パースの強化（export プレフィックス、クォート内エスケープ、インラインコメント処理など）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数取得 helper (_require) と Settings クラス（各種 API トークン、DB パス、環境種別、ログレベル、is_live/paper/dev フラグ等）。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
- Data 層（外部データ取得・保存）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（認証トークン取得、ページネーション対応のデータ取得）。
    - 固定間隔レートリミッタ（120 req/min）実装。
    - リトライ（指数バックオフ、最大 3 回、特定ステータスでの挙動）、429 の Retry-After 優先等。
    - 401発生時の自動トークンリフレッシュ（1回限り）実装。
    - fetch_* 系（株価日足、財務データ、マーケットカレンダー）のページネーション取得。
    - DuckDB への保存（save_daily_quotes / save_financial_statements / save_market_calendar）を冪等に実装（ON CONFLICT DO UPDATE / DO NOTHING）。
    - データ型安全な変換ユーティリティ（_to_float, _to_int）を実装。
    - fetched_at を UTC ISO8601 で記録し、データ取得時点を明示（ルックアヘッドバイアス対策）。
  - src/kabusys/data/news_collector.py
    - RSS フィードからのニュース収集機能を実装。
    - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント除去）と記事ID生成方針（SHA-256 先頭など）を想定。
    - defusedxml を用いた XML セキュリティ対策、受信サイズ制限（最大 10 MB）、SSRF／非 HTTP(S) スキーム除外等のセキュリティ考慮。
    - バルク INSERT のチャンク化、トランザクションまとめによる効率化・正確な挿入数取得設計。
- Research 層（因子計算・解析）
  - src/kabusys/research/factor_research.py
    - モメンタム（mom_1m / mom_3m / mom_6m / ma200_dev）、ボラティリティ（atr_20 / atr_pct / avg_turnover / volume_ratio）、バリュー（per / roe）等のファクター計算。
    - DuckDB のウィンドウ関数を活用した効率的な計算（LAG, AVG OVER 等）。
    - 営業日欠損対策のためのカレンダーバッファ設計（カレンダー日数でのスキャン幅）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、SQL で一括取得）。
    - IC（Information Coefficient）計算（スピアマンの ρ をランクで計算、ties を平均ランクで処理）。
    - factor_summary（count/mean/std/min/max/median）・rank ユーティリティ。
    - 標準ライブラリのみで実装（pandas 等に依存しない）。
  - src/kabusys/research/__init__.py
    - 主要研究関数を公開するパッケージ初期化。
- Strategy 層（特徴量・シグナル）
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境の生ファクターを正規化・合成し features テーブルへ書き込む build_features を実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - Z スコア正規化（外部 zscore_normalize を利用）、±3 クリップ、日付単位での置換（DELETE+INSERT をトランザクションで実施）により冪等性を保証。
    - ルックアヘッド回避のため target_date 時点のデータのみ使用。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）の計算ロジックを実装（シグモイド変換、欠損補完ルール等）。
    - ファクター重みのマージ・検証・再スケーリング機能（デフォルト重みは StrategyModel.md の値を使用）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負のとき）により BUY を抑制。
    - SELL 判定ロジック（ストップロス -8%、スコア低下）を実装。positions / prices を参照して判定。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）。
  - src/kabusys/strategy/__init__.py
    - build_features, generate_signals を公開。
- API / Public exports
  - パッケージの __all__ に data, strategy, execution, monitoring を含め、モジュール構成を明示。

### Changed
- -（初回リリースのため変更履歴は無し）

### Fixed
- -（初回リリースのため修正履歴は無し）

### Notes / Known limitations
- execution モジュールはパッケージ初期化のみで具体的な発注ロジックは未実装（将来的に execution 層で発注 API 連携を想定）。
- signal_generator 内の一部のエグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の情報が必要であり、未実装として明記されています。
- news_collector の記事 ID ポリシーや URL 正規化・記事→銘柄紐付け（news_symbols）は設計方針として定義されていますが、実際のフィード一覧拡張や紐付けルールの微調整が必要です。
- data 層では zscore_normalize 等のユーティリティが kabusys.data.stats に依存（このファイルは今回の範囲外）。統合時に依存関係を確認してください。
- DuckDB スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は本 CHANGELOG 外で定義・マイグレーションする必要があります。

### Security
- news_collector で defusedxml を利用、受信サイズ制限やスキーム検査を導入することで XML Bomb や SSRF 等のリスクを軽減しています。
- jquants_client は外部 HTTP エラーやネットワーク障害に対してリトライ・バックオフ・トークンリフレッシュを実装しています。

---

発行者: KabuSys 開発チーム  
初版: 0.1.0 (2026-03-21)

※ この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はリリース対象コミットやマージ履歴、リリース担当者の確認を反映してください。