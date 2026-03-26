# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このパッケージの最初の公開リリースに相当する変更点を日本語でまとめています。

全般:
- セマンティクスに従いバージョンはパッケージ内で __version__ = "0.1.0" として設定されています。
- パッケージは内部モジュールを公開し、トップレベル export は __all__ によって管理されています。

[0.1.0] - 2026-03-26
Added
- 基本パッケージ構成を実装（kabusys）。
  - モジュール構成: data, strategy, execution, monitoring などの名前空間を想定したパッケージ構成を用意。
- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local から自動的に設定値を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して判定（配布後も堅牢）。
  - .env のパースロジックを強化（export プレフィックス、クォート、エスケープ、インラインコメントの取り扱い）。
  - Settings クラスを提供し、必須環境変数取得時は未設定で ValueError を送出する _require を実装。
  - 設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（development|paper_trading|live 検証）, LOG_LEVEL（DEBUG|INFO|... 検証）など。
- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定 / 重み計算（純粋関数、DB参照なし）
    - select_candidates: スコア降順＋タイブレークで上位 N を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で配分。全スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - リスク調整
    - apply_sector_cap: セクター集中上限（デフォルト 30%）を既存保有比率に基づき新規候補の除外を行う。unknown セクターは上限対象外。
      - 当日売却予定銘柄を除外してエクスポージャーを計算可能。
      - 価格欠損時の挙動や将来のフォールバック戦略について TODO コメントあり。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数（1.0 / 0.7 / 0.3）。未知のレジームは 1.0 にフォールバック（WARNING）。
  - ポジションサイジング
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算を実装。
      - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct に基づく株数計算。
      - equal/score: ウェイトと portfolio_value, max_utilization を使った割当て。
      - 単元 (lot_size) に基づく丸め処理、per-stock 上限（max_position_pct）や aggregate cap（available_cash に基づくスケールダウン）をサポート。
      - cost_buffer を使って保守的に約定コストを見積もり、スケーリング時に考慮。
      - 将来的な拡張点として銘柄別 lot_size マップの導入を想定（TODO）。
- 戦略（strategy）
  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - research 側で計算した生ファクター（momentum / volatility / value）を統合して正規化（Zスコア）、±3 でクリップ、features テーブルへ UPSERT（トランザクションで日付単位置換）する build_features を実装。
    - ユニバースフィルタ（最低株価、平均売買代金）を適用。
    - DuckDB を利用して prices_daily / raw_financials を参照。
  - シグナル生成 (kabusys.strategy.signal_generator)
    - features と ai_scores を統合して final_score を計算、BUY / SELL シグナルを生成する generate_signals を実装。
    - デフォルト重み（momentum 0.4, value 0.2, volatility 0.15, liquidity 0.15, news 0.10）と閾値（0.60）を実装。ユーザ定義 weights は検証・正規化される。
    - AI スコア（ai_score）はシグモイドで変換、regime_score による Bear 検知を実装（Bear では BUY を抑制）。
    - SELL 判定はストップロス（終値/avg_price -1 < -8%）とスコア低下（final_score < threshold）を実装。未対応のエグジット（トレーリングストップ、時間決済）は未実装として明記。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性を保証。
- 研究用ツール / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/3m/6m、ma200_dev（200日移動平均乖離）を実装。
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio を実装。true_range の NULL 伝播を適切に扱う実装を含む。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算。EPS 欠損時は None。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 件未満なら None）。
    - factor_summary, rank 等の統計ユーティリティを実装（外部依存なし、標準ライブラリのみで動作）。
- バックテスト (kabusys.backtest)
  - simulator:
    - PortfolioSimulator: メモリ内でのポートフォリオ状態管理、SELL を先に、BUY を後に処理する約定ロジック。約定時にスリッページ・手数料を適用するパラメータをサポート。TradeRecord / DailySnapshot のデータモデルを定義。
    - 現時点で SELL は保有全量クローズ（部分利確・部分損切りは非対応）。
  - metrics:
    - calc_metrics: DailySnapshot と TradeRecord から一連の評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を計算。
    - 内部で用いる計算関数（年率化、シャープの算出、ドローダウン、勝率、ペイオフレシオ）を実装。

Fixed
- なし（初回リリース）

Changed
- なし（初回リリース）

Removed
- なし（初回リリース）

Known limitations / Notes
- 一部機能は意図的に未実装・将来拡張予定:
  - ポジションエグジットのトレーリングストップや時間決済は未実装（コードコメントで明記）。
  - ポートフォリオのセクターエクスポージャー計算で price が欠損 (0.0) の場合、過少見積もりとなり除外が緩くなる可能性がある（TODO にて将来のフォールバック価格案を検討）。
  - ファクターパッケージでは PBR や配当利回り等は現バージョンでは未実装。
  - 単元株 (lot_size) は現時点でコールサイトが一律で渡す想定。将来的には銘柄別 lot_map を受け取る設計を想定。
- DB 操作は DuckDB に依存（duckdb パッケージが必要）。外部ネットワーク/API への依存は戦略・研究モジュールで原則排除している。
- トランザクション中の例外時に ROLLBACK を試み、失敗すると WARNING を出力する安全処理を含む。

Public API / 主要な公開関数
- kabusys.config.settings — 環境設定取得用オブジェクト
- kabusys.portfolio.select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.strategy.build_features, generate_signals
- kabusys.research.calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.backtest.PortfolioSimulator, calc_metrics

移行 / 利用上の注意
- .env 自動ロードはプロジェクトルート検出に依存します。配布後やテスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- Settings の env / log_level は有効な値でないと ValueError を投げます。CI / デプロイ時に正しい環境変数設定を確認してください。
- DuckDB スキーマ（prices_daily, features, ai_scores, positions, raw_financials, signals 等）を事前に用意してください。機能はこれらのテーブルを参照します。

今後の予定（例示）
- 銘柄別単元サイズ対応（lot_map）
- 価格欠損時のフォールバックロジック（前日終値や取得原価の使用）
- トレーリングストップや時間決済などの追加エグジット条件
- 追加ファクター（PBR、配当利回り等）の実装

----- 
本リリースはプロジェクト初期の機能を幅広く揃えたもので、研究（research）→特徴量作成（feature_engineering）→シグナル生成（signal_generator）→ポートフォリオ構築（portfolio）→約定/バックテスト（backtest）という主要なワークフローを一貫して実行できる構成になっています。