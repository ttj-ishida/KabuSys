CHANGELOG
=========
すべての注記は Keep a Changelog の形式に準拠しています。  
このファイルは、コードベース（kabusys パッケージ）の実装内容から推測して作成した変更履歴です。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-26
-------------------

初回公開リリース。日本株自動売買システムのコア機能を実装しています。主な追加点・仕様は以下の通りです。

Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = "0.1.0"）。
  - public API エクスポート: data, strategy, execution, monitoring を公開。

- 環境設定 / .env 管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を探索）。
  - 読み込みロジックは OS 環境変数を保護し、.env.local を .env より優先して上書き。
  - 読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑止可能。
  - .env のパースは export プレフィックス、クォート（'"/" エスケープ処理）、インラインコメント処理に対応。
  - Settings クラスで主要設定項目をプロパティとして提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。
  - 入力検証:
    - KABUSYS_ENV は development/paper_trading/live のみ許容。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
  - 必須環境変数未設定時は ValueError を送出する _require() を用意。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定: select_candidates — スコア降順、同点は signal_rank でタイブレーク。
  - 重み計算:
    - calc_equal_weights — 等金額配分。
    - calc_score_weights — スコア比率に応じた配分。全スコアが 0 の場合は等金額にフォールバック（WARNING）。
  - リスク調整:
    - apply_sector_cap — セクターごとの既存エクスポージャーを計算し、セクター集中上限(max_sector_pct)を超えるセクターの新規候補を除外。unknown セクターは上限対象外。
    - calc_regime_multiplier — 市場レジーム（bull/neutral/bear）に対応した資金乗数を返す（未定義レジームは 1.0 でフォールバックし警告）。
  - 株数決定（position sizing）:
    - calc_position_sizes — allocation_method により "risk_based" / "equal" / "score" をサポート。
    - risk_based: 許容リスク（risk_pct）と stop_loss_pct を使って個別の基準株数を算出。
    - equal/score: ウェイトに基づく配分、銘柄・aggregate のキャップを考慮。
    - lot_size（単元株）による丸め、cost_buffer を用いた保守的コスト見積もり、available_cash を超えた場合のスケールダウンと再配分ロジック（端数処理で再現性確保）。
    - _max_per_stock による per-stock 上限を考慮。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research モジュールの calc_momentum / calc_volatility / calc_value を利用して素のファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - DuckDB に対して日付単位で DELETE→INSERT のトランザクション（冪等）を実行。コミット失敗時はロールバックを試行。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold, weights) を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算（シグモイド変換、欠損は中立 0.5 で補完）。
    - デフォルト重みを定義し、ユーザー提供 weights は検証・マージ・リスケールする（無効値はスキップ）。
    - Bear レジーム判定（AI の regime_score の平均 < 0）による BUY シグナル抑制。
    - BUY は threshold を超えた銘柄に付与、SELL はエグジット条件（ストップロス、スコア低下）で生成。
    - SELL 優先ポリシーにより SELL 対象は BUY から除外し、BUY のランクを再付与。
    - signals テーブルへ日付単位の置換（DELETE→INSERT、トランザクション）。

- 研究用ファクター計算（kabusys.research）
  - calc_momentum, calc_volatility, calc_value を実装:
    - モメンタム: 1M/3M/6M リターン、MA200 乖離（ウィンドウ未満は None）。
    - ボラティリティ: 20日 ATR / close（atr_pct）、20日平均売買代金、出来高比率。
    - バリュー: 最新財務（raw_financials）を用いて PER / ROE を算出（EPS=0 は None）。
  - 追加ユーティリティ:
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（1/5/21 日など）を一括取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンの IC（ランク相関）を実装（同順位は平均ランク、3 サンプル未満は None）。
    - factor_summary / rank: 基本統計量とランク変換を提供。
  - いずれも DuckDB の prices_daily/raw_financials を参照し外部依存を持たない設計。

- バックテスト / シミュレータ（kabusys.backtest）
  - PortfolioSimulator:
    - メモリ内での資金・ポジション管理、約定処理を実装。
    - SELL を先に処理し（保有全量クローズ）、BUY を後で処理する資金確保方針。
    - スリッページ（BUY は +、SELL は -）、手数料率を適用した約定価格と手数料計算。
    - TradeRecord / DailySnapshot 型を定義。
    - lot_size に基づく丸めをサポート（引数で指定可）。
  - BacktestMetrics / calc_metrics:
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティを実装。

Changed
- （初回リリースのため過去の変更はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- 環境変数読み込みは OS 環境変数を保護（protected set）しており、.env による既存値上書きは制御可能。

Known issues / Notes
- apply_sector_cap / calc_position_sizes:
  - price_map や open_prices に 0.0 または欠損があると想定よりエクスポージャーが過少評価される可能性あり（コード内に TODO コメントあり）。将来的なフォールバック価格の導入を検討。
- calc_regime_multiplier:
  - 未知のレジームは 1.0 でフォールバックし警告を出す。Bear レジームでは generate_signals が BUY を生成しない仕様（multiplier は追加のセーフガード）。
- feature_engineering / signal_generator:
  - features が空の場合は BUY 生成は行わず、SELL 判定のみを実施（warnings を出力）。
  - features に存在しない保有銘柄は final_score を 0.0 と見なして SELL 判定の対象となる（警告あり）。
- DB 操作:
  - features / signals への書き込みは DELETE→INSERT のトランザクションで実施。例外時はロールバックを試みるが、ロールバック自体の失敗を警告で通知する。
- execution パッケージは初期化ファイルのみ含まれており、実際のブローカー接続等は未実装／別途実装が必要。
- 単元株（lot_size）関連:
  - 現状は全銘柄共通の lot_size 引数を想定。将来的には銘柄別 lot_map を受け取る設計に拡張予定（TODO コメントあり）。

Compatibility
- DuckDB に依存するモジュール（strategy/research）は DuckDB のテーブルスキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals 等）に依存します。既存スキーマを用いる前提。

Authors
- 本 CHANGELOG はコード内容のコメント・実装から推測して作成しています。実際のリリースノートや配布物と差異がある場合があります。

-----