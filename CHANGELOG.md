CHANGELOG
=========

全般
-----
この CHANGELOG は "Keep a Changelog" 準拠の形式で記載しています。  
バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

[0.1.0] - 2026-03-26
-------------------

Added
- 初期リリース。日本株自動売買システムのコア機能を実装。
- パッケージ構成（主なモジュール）:
  - kabusys.config: 環境変数／.env 管理（自動ロード、パース、必須チェック）。
  - kabusys.portfolio: 銘柄選定・配分・リスク調整・株数決定（portfolio_builder / risk_adjustment / position_sizing）。
  - kabusys.strategy: 特徴量生成（feature_engineering）およびシグナル生成（signal_generator）。
  - kabusys.research: 研究用ファクター計算・探索ユーティリティ（factor_research / feature_exploration）。
  - kabusys.backtest: バックテスト用シミュレータと評価指標（simulator / metrics）。
  - その他: data / execution / monitoring 等のパッケージ公開用エントリ（__all__ 指定）。

- 環境設定（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込み。
  - 読み込み順: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサーは export プレフィックス、引用符（シングル／ダブル）、バックスラッシュエスケープ、行末コメントなどに対応。
  - Settings クラスで必須環境変数の取得をラップ:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値: KABU_API_BASE_URL="http://localhost:18080/kabusapi", DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - KABUSYS_ENV の許容値: development, paper_trading, live（無効値は ValueError）
    - LOG_LEVEL の検証: DEBUG/INFO/WARNING/ERROR/CRITICAL

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順、同点時は signal_rank でタイブレークして上位 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（全スコアが 0 の場合は等分配にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーが閾値（デフォルト 30%）を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告ログ出力の上 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じた株数計算を実装。
      - サポート: "risk_based"（リスクベース）、"equal"、"score"
      - リスクパラメータ（risk_pct, stop_loss_pct）、1銘柄上限 max_position_pct、投下資金上限 max_utilization、単元 lot_size、コストバッファ cost_buffer を考慮。
      - 単元（lot_size）での丸め処理、portfolio_value と available_cash による aggregate cap（総投資額が available_cash を超える場合にスケールダウン）。スケールダウン時は小数残差を計算して残余資金で lot 単位の追加配分を行う（再現性のためソート安定化）。
      - 価格欠損や不正価格はスキップしてログを出力。

- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールの生ファクター（momentum / volatility / value）を取得。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）を適用。
    - 数値ファクターを Z スコア正規化し ±3 でクリップして features テーブルへ日付単位で置換（冪等）。
    - DuckDB を使用しトランザクションで原子性を確保。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算して final_score を算出（デフォルト重みはコード内定義）。
    - AI ニューススコアは未登録時は中立（0.5）で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負且つサンプル数 >= 3 の場合）で BUY シグナルを抑制。
    - BUY 閾値のデフォルトは 0.60。SELL 条件（エグジット）としてストップロス（終値/avg_price -1 < -8%）とスコア低下（final_score < threshold）を実装。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
    - weights 入力は検証・補完・正規化される（未知キー・負値・非数値は無視、合計が 1 でなければ再スケール）。

- 研究ユーティリティ（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日移動平均乖離）を算出。データ不足時は None。
    - calc_volatility: 20 日 ATR、atr_pct（ATR/close）、avg_turnover（20日平均売買代金）、volume_ratio を算出。true_range の NULL 伝播を制御して厳密に計算。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を算出（EPS が 0/NULL の場合 PER は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算（有効レコードが 3 未満は None）。
    - factor_summary: 指定カラムの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクを返すランク関数（丸めによる tie 対応）。

- バックテスト（kabusys.backtest）
  - metrics.calc_metrics: DailySnapshot（履歴）と TradeRecord（約定履歴）から評価指標（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio, total_trades）を算出。
  - simulator.PortfolioSimulator:
    - メモリ内でポートフォリオ状態管理（cash, positions, cost_basis, history, trades）。
    - execute_orders: SELL を先に処理し BUY を後で処理（資金確保）。SELL は保有全量クローズ。スリッページ率（BUY:+, SELL:-）と手数料率を適用して TradeRecord を記録。
    - TradeRecord / DailySnapshot データ構造を定義。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Known issues / TODO（現実装で意識すべき点）
- apply_sector_cap:
  - price_map に price が欠損（0.0）の場合、エクスポージャーが過小評価されてしまいブロックが外れる可能性あり。前日終値や取得原価などのフォールバック価格を将来検討する旨をコメントに記載。
- position_sizing:
  - 銘柄ごとの単元サイズ lot_map を将来サポートする予定（現在は全銘柄共通 lot_size 引数）。
- signal_generator._generate_sell_signals:
  - トレーリングストップや時間決済（保有 60 営業日超過）は未実装。positions テーブルに peak_price / entry_date が必要。
- feature_engineering / strategy:
  - features 作成やシグナル生成は DuckDB のテーブル（prices_daily / raw_financials / ai_scores / positions / features / signals）に依存。適切なスキーマとデータ準備が必要。
- 環境変数の必須チェックにより、本番実行時は必要な env が設定されていないと ValueError が発生する（意図的）。
- generate_signals における AI スコアの扱いは単純なシグモイド変換であり、AI モデルの仕様に応じて変更が必要な場合がある。

補足
- 本リリースは主に純粋関数群・DB 読み取り部分・バックテストロジック・シミュレータを実装しており、実際のブローカ API（kabu API）や外部サービス（Slack 通知等）への具体的な接続は設定層と execution 層で実装する想定です。
- ログ出力（logging）を多用しており、挙動の追跡とデバッグを行いやすい設計になっています。

--- 
（メモ）今後のリリースでは以下を想定:
- 戦略パラメータの外部化（設定ファイル / 管理 UI）
- 銘柄別単元管理、手数料モデルの細分化
- Trailing stop / time-based exit の実装
- テストカバレッジの拡充および CI/CD での自動検証

