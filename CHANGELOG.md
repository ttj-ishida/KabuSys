# Changelog

すべての注目すべき変更履歴を記録します。本ファイルは Keep a Changelog の方針に準拠しています。  

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買システムのコア機能を実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージを定義し、サブパッケージ（data, strategy, execution, monitoring）を外部公開。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート判定: .git または pyproject.toml）。
  - .env パーサ実装（コメント行、export プレフィックス、クォートとエスケープ処理、インラインコメントの取り扱いを考慮）。
  - .env 読み込み時の override / protected（OS 環境変数保護）機能。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベルの取得・バリデーションを実施。
  - 必須環境変数未設定時は ValueError を発生させる _require を実装。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装。
  - 固定間隔（120 req/min）を守る RateLimiter 実装。
  - HTTP リトライロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 時はリフレッシュトークンで id_token を自動更新して 1 回リトライする仕組み。
  - ページネーション対応 API 呼び出し（fetch_*）。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等性を確保。
  - fetched_at を UTC で記録し、ルックアヘッドバイアス追跡を可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集基盤を実装（デフォルトに Yahoo Finance のビジネスカテゴリを設定）。
  - 記事本文の前処理、URL 正規化（トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - 記事 ID は正規化後の SHA-256 ハッシュ（先頭 32 文字）を用いて冪等性を確保。
  - defusedxml を利用して XML 関連の攻撃から防御。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES）やチャンク化したバルク INSERT によるリソース保護。
  - DB 保存はトランザクションにまとめ、挿入件数を明確に返却する設計。

- リサーチ／ファクター計算（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を用いてモメンタム・ボラティリティ・バリュー系ファクターを算出。
    - Momentum: mom_1m/mom_3m/mom_6m、200 日移動平均乖離（ma200_dev）。
    - Volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: PER（price / EPS）、ROE（最新財務データを target_date 以前から取得）。
  - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（スピアマンランク相関）、factor_summary（count/mean/std/min/max/median）、rank（同順位は平均ランク）を実装。
  - DuckDB クエリは営業日欠損（休場）を考慮するためカレンダーバッファを使用。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで計算された生ファクターを結合し、ユニバースフィルタ（最低株価・最低売買代金）を適用。
  - 指定列を Z スコア正規化し ±3 でクリップ（外れ値抑制）。
  - features テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性確保）。冪等。

- シグナル生成（kabusys.strategy.signal_generator）
  - features に基づきコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付き和で final_score を計算（デフォルト重みを提供、ユーザ指定の重みを受け入れスケール補正）。
  - AI スコア（ai_scores テーブル）を取り込み市場レジーム判定（regime_score の平均が負 → Bear）。Bear レジーム時は BUY シグナルを抑制。
  - BUY シグナル閾値（デフォルト 0.60）、SELL（エグジット）条件を実装:
    - ストップロス (-8%) を最優先。
    - final_score が閾値未満 → score_drop。
    - 保有ポジションの価格欠損時は判定をスキップする安全措置。
  - signals テーブルへ日付単位で置換（DELETE + INSERT、トランザクションで原子性確保）。
  - 未登録コンポーネント（None）は中立値 0.5 で補完し欠損銘柄の不当な降格を防止。
  - SELL 対象は BUY から除外、ランクを再付与（SELL 優先ポリシー）。

- 公開 API エクスポート
  - strategy/__init__.py, research/__init__.py による主要関数の再エクスポート（build_features, generate_signals, calc_* 等）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- J-Quants クライアント:
  - トークン自動リフレッシュ時の無限再帰を防止するフラグ（allow_refresh）を実装。
  - レート制限とリトライにより API 過負荷や一時的エラーに耐性を持たせる。
- News Collector:
  - defusedxml の利用、受信バイト上限、URL トラッキングパラメータ除去等の対策を実装し、XML/SSRF/DoS に配慮。

### Notes / Limitations / TODO
- signal_generator のエグジット条件の一部（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加情報が必要であり未実装。
- feature_engineering と signal_generator は発注層（execution）へ直接依存しない設計。execution 層は別実装の想定。
- news_collector における IP 検査や SSRF 対策の骨組み（ipaddress/socket のインポート）は存在するが、詳細ルールは今後拡張予定。
- 一部の入力検証やエラーメッセージは今後一層の整備が必要。

---

配布バージョン: 0.1.0 (パッケージ内 __version__ に一致)