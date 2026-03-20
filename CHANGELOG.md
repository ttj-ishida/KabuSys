# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルはコードベースの現状（バージョン 0.1.0）から推測して作成した初回リリース向けの変更履歴です。

注: バージョン番号はパッケージの __version__（0.1.0）に基づいています。リリース日: 2026-03-20

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-20

### Added
- パッケージ概要
  - kabusys: 日本株自動売買システムのベース実装。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local ファイルおよび OS 環境変数からの設定自動読み込み機能を追加。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して判別（CWD 非依存）。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等を扱える堅牢な実装。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ユーティリティ _require を提供。必須キー:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
    - SLACK_BOT_TOKEN
    - SLACK_CHANNEL_ID
  - デフォルト設定:
    - KABUSYS_ENV のデフォルトは "development"（有効値: development / paper_trading / live）。
    - LOG_LEVEL のデフォルトは "INFO"（有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - DUCKDB_PATH のデフォルト: data/kabusys.duckdb
    - SQLITE_PATH のデフォルト: data/monitoring.db

- Data 層: J-Quants API クライアント（kabusys.data.jquants_client）
  - API レート制御を行う固定間隔レートリミッタ（120 req/min）を導入。
  - リトライ機構（指数バックオフ、最大 3 回）を実装。再試行対象: 408, 429, 5xx 系。
  - 401 Unauthorized を検出した場合、リフレッシュトークンから自動で id_token を再取得して 1 回リトライ。
  - ページネーション対応（pagination_key を利用）で /prices/daily_quotes, /fins/statements, /markets/trading_calendar などを取得。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead バイアスのトレースを可能に。
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。INSERT は ON CONFLICT DO UPDATE により冪等性を確保。
  - 型変換ユーティリティ _to_float / _to_int を実装して不正データ耐性を向上。

- Data 層: ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news テーブルへ保存する基盤を実装。
  - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成して冪等性を確保。
  - URL 正規化: スキーム/ホスト小文字化、既知トラッキングパラメータ（utm_*, fbclid, gclid など）の除去、フラグメント削除、クエリキーソート。
  - defusedxml を用いた XML パース（XML Bomb 対策）。
  - SSRF 回避の観点から https?/http のみ許可、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を実装。
  - デフォルト RSS ソースを提供（例: Yahoo Finance のビジネス RSS）。

- 研究（Research）モジュール（kabusys.research）
  - ファクター計算ユーティリティを集約して公開:
    - calc_momentum: モメンタム（1/3/6ヶ月相当）と 200 日移動平均乖離率を計算。
    - calc_volatility: ATR(20)、相対ATR(atr_pct)、20 日平均売買代金、出来高比率などを計算。
    - calc_value: PER / ROE を raw_financials と prices_daily から算出。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランク（ties は平均ランク）で扱うランク関数。
  - 外部ライブラリに依存せず、DuckDB 接続のみを受け取って動作するよう設計。

- 戦略層（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を使用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + バルク INSERT、トランザクションで原子性確保）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score は重み付き和（デフォルト重みは StrategyModel.md に準拠）で算出し、閾値（デフォルト 0.60）を超えた銘柄に BUY シグナルを生成。
    - Bear レジーム（AI の regime_score 平均が負）時は BUY を抑制。
    - 保有ポジションに対するエグジット判定（ストップロス -8% / final_score が閾値未満）に基づいて SELL シグナルを生成。
    - signals テーブルへ日付単位で置換（DELETE + INSERT、トランザクションで原子性確保）。
    - 重みの入力値検証、合計が 1.0 でない場合の再スケーリング機能を実装。
    - 不足データがあるコンポーネントは中立 0.5 で補完して極端な不利評価を防止。

- 実行層の基礎（パッケージ構成）
  - kabusys.__init__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- J-Quants クライアント: 401 時の自動トークンリフレッシュは allow_refresh フラグにより無限再帰を防止。
- news_collector: defusedxml 利用による XML に関する脆弱性対策、最大レスポンスバイト数制限、URL 正規化によるトラッキング除去、HTTP スキーム検証。

### Notes / Known limitations
- signal_generator の一部エグジット条件は未実装（コメントで明記）:
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- feature_engineering / signal_generator は発注 API（execution 層）に依存しない設計だが、signals テーブルの内容を execution 層が参照して注文を出す想定。
- research モジュールは pandas 等に依存しない純 Python + DuckDB 実装。ただし zscore_normalize は kabusys.data.stats に依存する（該当ユーティリティは別モジュールで提供）。
- .env の自動読み込みはプロジェクトルートが検出できない場合スキップされる点に注意。
- J-Quants API のレート制御は固定間隔スロットリングで実装しているため、burst 性の高い取得には調整が必要な場合がある。

### Migration / Usage notes
- 必須環境変数を設定してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。不足すると Settings のプロパティアクセスで ValueError が発生します。
- 自動 .env ロードを無効にしたいテスト環境等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite のデフォルトパスは settings.duckdb_path / settings.sqlite_path を参照します。必要に応じて環境変数で上書きしてください。

---

今後のリリースでは、execution（発注）層の実装、監視（monitoring）機能の追加、追加のエグジット条件やリスク管理ロジックの実装、テストとドキュメントの拡充が想定されます。