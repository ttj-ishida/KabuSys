CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」仕様に従って記載しています。  
フォーマット: バージョン見出し → カテゴリ（Added / Changed / Fixed / Removed / Known issues / Notes）

0.1.0 - 2026-03-26
------------------

Added
- 初回公開リリース。パッケージ名: kabusys、バージョン 0.1.0。
- 基本パッケージ構成を実装:
  - kabusys.__init__ に __version__ と公開モジュール一覧を定義。
  - モジュール群: config, data（部分的）, portfolio, strategy, research, backtest, execution（スケルトン）などを含む設計を導入。
- 環境設定管理 (kabusys.config):
  - .env / .env.local の自動読み込みをプロジェクトルート（.git または pyproject.toml）から行う機能を追加。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装（コメント、export プレフィックス、クォート＋バックスラッシュエスケープ対応）。
  - Settings クラスに各種必須/任意設定プロパティを実装（J-Quants, kabu API, Slack, DB パス, 環境モード/ログレベル判定 等）。未設定時は ValueError を送出する必須取得メソッドを提供。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装（development / paper_trading / live、DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- ポートフォリオ構築（kabusys.portfolio）:
  - portfolio_builder: 候補選択(select_candidates)、等配分(calc_equal_weights)、スコア重み配分(calc_score_weights)を実装。全スコアが 0 の場合は等配分へフォールバックし警告を出力。
  - risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに基づく投下資金倍率 calc_regime_multiplier（bull/neutral/bear マップ）を実装。未知レジームは警告の上 1.0 へフォールバック。
  - position_sizing: allocation_method に応じた株数計算 calc_position_sizes を実装（risk_based / equal / score）。単元株（lot_size）単位で丸め、max_position_pct・max_utilization・cost_buffer を考慮した aggregate cap スケーリングを行う。
- 戦略（kabusys.strategy）:
  - feature_engineering.build_features: research からの生ファクターを統合、ユニバースフィルタ（最低株価・最低売買代金）、Z スコア正規化（クリップ ±3）、DuckDB に対する日付単位の UPSERT（DELETE + INSERT）を実装。
  - signal_generator.generate_signals: features と ai_scores を統合し momentum/value/volatility/liquidity/news コンポーネントで final_score を算出。重みの検証・正規化、Bear レジームでの BUY 抑制、SELL のエグジット条件（ストップロス・スコア低下）を実装。signals テーブルへの冪等書き込み（DELETE → INSERT）を行う。
  - 未登録の AI スコアは中立（0.5 補完）扱い、features に存在しない保有銘柄は final_score=0 と見なして SELL 判定。
  - SELL 優先ポリシー: SELL 対象は BUY 候補から除外し、BUY のランクを再付与。
- リサーチ（kabusys.research）:
  - factor_research: momentum, volatility, value のファクター計算を実装（DuckDB SQL ベース）。ma200, atr_20, avg_turnover 等を算出。
  - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（Spearman）の算出(calc_ic)、factor_summary、ランク付けユーティリティ(rank) を実装。外部依存ライブラリなしで標準ライブラリ + DuckDB による実装。
- バックテスト（kabusys.backtest）:
  - metrics.calc_metrics: DailySnapshot と TradeRecord から各種指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を計算。
  - simulator.PortfolioSimulator: 擬似約定・ポートフォリオ状態管理を実装。SELL を先に処理し（保有全量クローズ）、その後 BUY を処理。スリッページ（BUY:+、SELL:-）・手数料モデル・lot_size の考慮、TradeRecord と日次スナップショット履歴の保持を行う。
- ロギングとエラーハンドリング:
  - 各モジュールで適切な logger を使用し、警告・デバッグ情報を出力（例: price 欠損時のスキップ通知、weights の無効値スキップ、DB トランザクション失敗時の ROLLBACK 警告等）。

Changed
- （初版のため変更履歴なし）

Fixed
- （初版のため修正履歴なし）

Removed
- （初版のため削除履歴なし）

Known issues / Notes
- 環境変数ロード:
  - .env ファイル読み込み時に I/O エラーが発生した場合は warnings.warn で通知して処理を継続します。
  - 自動ロードはプロジェクトルートが見つからない場合スキップされるため、配布後に期待される動作をすることを意識してください。
  - .env の上書きロジック: OS 環境変数は protected として .env/.env.local の上書き対象外（ただし .env.local は override=True で上書き試み）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。
- apply_sector_cap:
  - sector_map に存在しないコードは "unknown" とし、セクター上限の適用対象外（除外しない）。price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りになる可能性がある旨コメントあり（将来的にフォールバック価格の検討）。
- calc_score_weights:
  - 全銘柄のスコア合計が 0 の場合、等金額配分にフォールバックして警告を出す。
- signal_generator:
  - Bear レジームでは generate_signals が BUY を抑制する設計（StrategyModel に準拠）。Bear 判定は ai_scores の regime_score 平均を用い、サンプル数が 3 未満なら Bear とみなさない。
  - SELL のエグジット条件としてトレーリングストップや時間決済（保有日数による決済）は未実装（positions テーブルに peak_price / entry_date の情報が必要）。
- position_sizing:
  - price が欠損・非正数の場合はその銘柄はスキップする（ログ出力）。
  - aggregate cap のスケーリングは lot_size 単位で再配分するアルゴリズムを採用。端数処理や再配分における安定化ロジックを実装済みだが、将来的な微調整が想定される。
- backtest.simulator:
  - SELL は保有全量をクローズする仕様（現状は部分利確 / 部分損切りに対応していない）。
  - TradeRecord.realized_pnl の計算ロジックは SELL 時にのみ設定される想定。BUY 手数料は cash から別途減算済みで TradeRecord の realized_pnl に含めない設計。
- 汎用:
  - DuckDB を想定した SQL 実装が多く含まれる。利用時はテーブルスキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を整備する必要があります。
  - 一部に TODO コメントあり（例: 銘柄別 lot_size のサポート、価格フォールバック、未実装のエグジット条件など）。
- 互換性 / Breaking changes:
  - 本リリースは初版のため、後続バージョンで public API（関数名／シグネチャ／期待する dict フィールド名等）に互換性のない変更を行う可能性があります。外部からは関数呼び出しやテーブル構造を固定化して利用することを推奨します。

開発者向けメモ
- テスト容易化のため Settings の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- DuckDB 接続を受け取る関数群は副作用を持たない（テスト用に in-memory DB を用いることでユニットテストが容易）。
- ロギングは各モジュールで適切に出力されるため、実行時ログレベルを LOG_LEVEL 環境変数で調整してください。

--- 
（注）この CHANGELOG は提供されたソースコードから実装内容を推測して作成したものです。実際のリリースノートは運用ポリシーに合わせて調整してください。