# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティック バージョニングを使用します。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。日本株の自動売買システム「KabuSys」のコア機能を提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = 0.1.0）。
  - サブパッケージ公開: data, strategy, execution, monitoring。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env パーサーの実装: export プレフィックス対応、クォートとエスケープの処理、インラインコメントの取り扱いを細かく制御。
  - 自動ロード無効化のためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 環境変数の必須チェック用 _require() と Settings クラスを提供。必須キー（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）やログレベル / 環境（development/paper_trading/live）検証を実装。
  - データベースパス（DuckDB / SQLite）の既定値を設定可能（DUCKDB_PATH, SQLITE_PATH）。

- データ収集クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。日次株価・財務データ・マーケットカレンダー取得をサポート（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx に対する再試行、429 の Retry-After を考慮。
  - 401 受信時のリフレッシュトークンによる自動トークン更新（1 回だけリフレッシュして再試行）。
  - データ保存ユーティリティ: raw_prices/raw_financials/market_calendar への冪等的保存（ON CONFLICT DO UPDATE）を実装。
  - データ型変換ヘルパー (_to_float, _to_int) により入力の頑健性を向上。
  - fetched_at を UTC ISO8601 で保存し、データ入手時刻をトレース可能に。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存する基礎実装（デフォルトで Yahoo Finance のビジネス RSS を利用可能）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）および記事 ID を SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
  - defusedxml を用いた安全な XML パース（XML Bomb 等への対策）。
  - SSRF・不正スキーム対策や最大受信バイト数（10 MB）によるメモリ DoS 緩和。
  - バルク挿入のチャンク化を行い DB への負荷を抑制。

- リサーチ（src/kabusys/research/）  
  - ファクター計算モジュール（factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離率）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials を参照して計算。
    - 欠損やデータ不足時の処理を明確にし、結果を (date, code) キーの dict リストで返す。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（指定ホライズンの fwd returns、デフォルト [1,5,21]）。
    - IC（Spearman の ρ）計算実装（rank 関数に平均ランク同順位ハンドリング）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）の計算。
    - pandas 等に依存せず標準ライブラリのみで実装。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールの生ファクターを取得して正規化（z-score）・合成し features テーブルへ UPSERT（トランザクションで日付単位の置換）を実行する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
  - Z スコアを ±3 でクリップし外れ値影響を抑制。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算、重み付け合成して final_score を算出する generate_signals を実装。
  - デフォルト重み・閾値（threshold=0.60）を設定。ユーザー指定の weights を受け付け、検証・正規化（合計が 1.0 に再スケール）を実施。
  - Sigmoid で Z スコアを [0,1] にマッピング、欠損コンポーネントは中立値 0.5 で補完。
  - Bear レジーム判定（ai_scores の regime_score の平均が負の場合）による BUY の抑制を実装。サンプル数不足時は誤判定を防ぐため Bear とみなさない。
  - SELL（エグジット）条件としてストップロス（-8%）とスコア低下を実装。価格欠損時の判定スキップや、positions に存在しない銘柄扱いのロギング等の安全策あり。
  - signals テーブルへの日付単位の置換をトランザクションで行い冪等性を確保。
  - BUY と SELL の優先ポリシー（SELL 対象は BUY から除外）を導入。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を使用して XML 関連の攻撃を緩和。
- ニュース収集で受信サイズ制限や URL スキーム検証を導入し SSRF / DoS のリスクを低減。
- J-Quants クライアントではトークンの自動リフレッシュとリトライ制御により、認証・ネットワーク障害時の堅牢性を向上。

### Notes / Requirements
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB を用いたローカルデータストアを前提とする（デフォルトパス: data/kabusys.duckdb）。
- research モジュール/strategy モジュールは DuckDB の prices_daily / raw_financials / features / ai_scores / positions などのテーブル構成を前提としている。スキーマを生成するマイグレーション / DDL は別途用意する必要があります。
- 本バージョンでは一部の戦術（トレーリングストップ、時間決済など）は未実装（signal_generator に注釈あり）。将来的に positions テーブルの拡張（peak_price, entry_date 等）で対応予定。

---

今後のリリースでは以下を予定しています:
- execution 層（kabuステーション API 経由の発注ロジック）と monitoring 層の実装
- PBR / 配当利回り等の追加ファクター、トレーリングストップなどのエグジット戦略
- 単体テスト・統合テストの追加と CI/CD パイプライン統合

（以上）