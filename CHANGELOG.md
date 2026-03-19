# Changelog

すべての変更は https://keepachangelog.com/ja/ のガイドラインに従って記載しています。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システムのコア機能を実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期バージョンを追加。バージョンは `0.1.0`。
  - パッケージ内公開API: data, strategy, execution, monitoring をエクスポート。

- 設定管理
  - 環境変数/設定読み込みモジュールを実装（kabusys.config）。
  - プロジェクトルートを .git または pyproject.toml から自動検出し、プロジェクトルート直下の `.env` / `.env.local` を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサを堅牢化（コメント・export 形式・クォート内エスケープ・インラインコメント処理対応）。
  - 環境設定 `Settings` を提供（必須キー検査、env/log_level の検証、DB パスの Path 型返却、is_live/is_paper/is_dev 判定等）。

- Data 層（J-Quants クライアント）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
  - API レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装。
  - リトライ戦略（指数バックオフ、最大 3 回、HTTP 408/429/5xx のリトライ・429 の Retry-After 優先）を実装。
  - 401 受信時は refresh token を用いて自動的に ID トークンをリフレッシュしてリトライ（1 回のみ）。
  - ページネーション対応でデータ取得関数を実装:
    - fetch_daily_quotes（株価日足 / pagination）
    - fetch_financial_statements（財務データ / pagination）
    - fetch_market_calendar（マーケットカレンダー）
  - DuckDB への保存ユーティリティを実装（冪等性を担保する ON CONFLICT/DO UPDATE を利用）:
    - save_daily_quotes → raw_prices テーブル
    - save_financial_statements → raw_financials テーブル
    - save_market_calendar → market_calendar テーブル
  - HTTP 層やデータ変換のユーティリティ（_to_float / _to_int）を実装。

- ニュース収集
  - RSS からのニュース収集モジュールを実装（kabusys.data.news_collector）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント削除）による冪等 ID 生成方針を採用。
  - defusedxml を使用して XML Bomb 等の攻撃を防止。
  - 受信サイズ上限（10MB）によるメモリ DoS 対策、HTTP スキーム確認等による SSRF 対策の記載。
  - INSERT をバルク/チャンク化し、1トランザクションで保存してオーバーヘッドを削減。挿入数を正確に返す設計。

- リサーチ（研究用）モジュール
  - ファクター計算モジュールを実装（kabusys.research.factor_research）:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（20日 ATR / atr_pct / avg_turnover / volume_ratio）
    - calc_value（PER / ROE の算出、raw_financials と prices_daily を結合）
    - DuckDB の SQL とウィンドウ関数を活用した効率的な実装（営業日補正のためカレンダーバッファなどを考慮）。
  - 特徴量探索モジュールを実装（kabusys.research.feature_exploration）:
    - calc_forward_returns（複数ホライズンに対する将来リターン計算、まとめて 1 クエリで取得）
    - calc_ic（factor と forward return の Spearman ランク相関を計算）
    - factor_summary（count/mean/std/min/max/median を計算）
    - rank（平均ランクを扱う tie 処理を含むランク関数）
  - 研究モジュールは外部ライブラリ（pandas 等）に依存せず、DuckDB と標準ライブラリで完結する設計。

- 戦略（Strategy）層
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）:
    - research で算出した生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定の数値カラムに対して Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + バルク INSERT、トランザクションで原子性保証）。
  - シグナル生成（kabusys.strategy.signal_generator）:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完、重みの検証と正規化（デフォルト重みは StrategyModel.md に準拠）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負のとき。サンプル閾値あり）。
    - BUY/SELL シグナル生成（BUY は閾値 0.60、Bear 時は BUY を抑制）。
    - エグジット判定にストップロス（-8%）とスコア低下を実装（トレーリングストップ等は未実装で注記）。
    - signals テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - weights 引数の入力検証（未知キー・非数値・負値は無視）と自動リスケーリングを実装。

### 変更 (Changed)
- なし（初回リリースのため既存リポジトリからの差分はありません）。

### 修正 (Fixed)
- なし（初回実装段階。ログ・警告により欠損・不整合を通知する実装を含む）。

### セキュリティ (Security)
- RSS パーシングに defusedxml を使用し XML 関連の脆弱性に配慮。
- ニュース収集での URL 正規化・スキームチェック・トラッキングパラメータ除去により SSRF やトラッキングによる冪等性崩壊を軽減。
- J-Quants クライアントはリトライ制御・トークン自動リフレッシュ・タイムアウト等を実装し、堅牢性を向上。

### 既知の制約 / TODO
- signal_generator のトレーリングストップや時間決済など一部エグジット条件は未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- 一部の関数は prices_daily / raw_financials / features / ai_scores / positions 等のテーブルスキーマ依存（ドキュメント上のテーブル定義との整合性が必要）。
- 外部 API 呼び出しやネットワーク周りはテストが必要（モック推奨）。
- NewsCollector の挿入/紐付けロジック（news_symbols など）は実装詳細に応じてマイナー調整が想定される。

--- 

詳細な設計・仕様はコード内ドキュメント（docstring）と同梱の設計文書（StrategyModel.md / DataPlatform.md / Research 内ドキュメント）を参照してください。