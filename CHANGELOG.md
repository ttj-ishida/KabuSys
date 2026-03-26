# Changelog

すべての重要な変更は Keep a Changelog 規約に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在の公開バージョン: 0.1.0）

## [0.1.0] - 2026-03-26

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基礎モジュールを追加。
  - パッケージルート: kabusys (バージョン 0.1.0)
- 環境設定・読み込み
  - kabusys.config:
    - .env / .env.local を自動読み込み（読み込み順: OS 環境変数 > .env.local > .env）。
    - プロジェクトルートの自動検出: .git または pyproject.toml を起点に探索（カレントワーキングディレクトリに依存しない実装）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - _parse_env_line により以下をサポート・耐性を強化:
      - export KEY=val 形式の対応
      - シングル/ダブルクォート内でのバックスラッシュエスケープ対応
      - インラインコメント処理（クォートなしの場合は直前がスペース/タブでコメントと判断）
    - 環境変数アクセス用 Settings クラスを提供（必須変数取得時の検証・エラー報告を含む）。
    - KABUSYS_ENV / LOG_LEVEL の許容値チェック（不正値で ValueError を送出）。
    - データベースパス用プロパティ（DUCKDB_PATH, SQLITE_PATH）を提供。
- ポートフォリオ構築
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: スコア降順・タイブレークロジックで候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0.0 の場合は等配分へフォールバックし WARNING を出力）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく株数計算。
    - risk_based: 許容リスク率と損切り率から基礎株数を算出。
    - equal/score: weight に従った配分、per-position 上限・単元株切り捨て処理。
    - aggregate cap: 投下合計が available_cash を超える場合のスケーリングと端数分配アルゴリズム（lot_size 単位での安定した再配分）。
    - cost_buffer による保守的コスト見積り対応（スリッページ・手数料を考慮）。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクターごとの既存保有比率を計算して上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す（未知レジームはフォールバックで 1.0、警告ログ）。
- 戦略（Feature engineering / Signal generation）
  - kabusys.strategy.feature_engineering:
    - build_features: research モジュールのファクターを取得し、ユニバースフィルタ・Z スコア正規化（±3 でクリップ）を適用して features テーブルへ日付単位アップサート（トランザクションによる原子性を担保）。
    - ユニバースフィルタ: 最低株価・最低平均売買代金の閾値を適用。
    - 価格取得は target_date 以前の最新価格を参照（休場日対応）。
  - kabusys.strategy.signal_generator:
    - generate_signals: features と ai_scores を統合して最終スコアを計算、BUY/SELL シグナルを作成して signals テーブルへ日付単位で置換。
    - コンポーネントスコア: momentum/value/volatility/liquidity/news を計算するユーティリティ実装（欠損コンポーネントは中立 0.5 で補完）。
    - AI スコア未登録時は中立補完、レジーム判定（_is_bear_regime）により Bear 時は BUY を抑制。
    - SELL（エグジット）判定: ストップロス（-8%）とスコア低下を実装。価格欠落時は SELL 判定をスキップして警告。
    - weights 入力の検証と正規化、無効値はスキップしてデフォルトにフォールバック。
    - DB 操作はトランザクションで行い、ROLLBACK の失敗は警告ログを出す保護処理を実装。
- リサーチ / ファクター計算
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（データ不足は None を返す）。
    - calc_volatility: 20日 ATR / atr_pct、平均売買代金、volume_ratio を計算（データ不足対応）。
    - calc_value: latest 財務データ（raw_financials）と prices_daily を結合して PER/ROE を計算。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21）に対する将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効サンプル数 3 未満は None）。
    - factor_summary, rank: 基本統計量・ランク変換ユーティリティを提供（外部ライブラリに依存しない実装）。
- バックテスト
  - kabusys.backtest.simulator:
    - PortfolioSimulator: メモリ内での擬似約定とポートフォリオ状態管理を実装。SELL を先に処理してから BUY を処理（資金確保のため）。スリッページ・手数料モデル、lot_size を考慮。
    - DailySnapshot / TradeRecord のデータクラスを提供。
  - kabusys.backtest.metrics:
    - calc_metrics: history（DailySnapshot）と trades（TradeRecord）から CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算する関数を提供。

Changed
- （該当なし：初回リリースのため変更履歴なし）

Fixed
- .env 読み込みの堅牢化:
  - ファイルが開けない場合は警告を出して読み込み失敗を無害に扱う。
  - OS 環境変数を protected として .env/.env.local の上書きを防止。
- DB 書き込み処理の原子性:
  - build_features / generate_signals で日付単位の削除→挿入をトランザクションで実行。例外時は ROLLBACK を試行し、失敗時は警告ログ。
- 各種数値欠損・異常値への耐性を強化:
  - NaN/Inf のチェックや価格欠損時のスキップ・警告。
  - calc_score_weights で合計スコアが 0 の場合のフォールバック実装。
  - generate_signals で無効な weights 値のスキップと再スケールを実装。
  - _generate_sell_signals で価格が取得できない場合は SELL 判定全体をスキップして警告。

Security
- （該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Notes / TODO
- position_sizing.calc_position_sizes:
  - lot_size は現状全銘柄共通。将来的に銘柄別単元対応（stocks マスタからの lot_map 受け取り）を検討中。
- apply_sector_cap:
  - price_map に価格欠損（0.0）がある場合、エクスポージャーが過少見積りされてブロックが回避される可能性あり。前日終値や取得原価によるフォールバックを将来検討。
- signal_generator:
  - トレーリングストップや時間決済などの一部エグジット条件は未実装（positions テーブルに peak_price / entry_date 情報が必要）。

---

この CHANGELOG は、ソースコード内の関数・振る舞い・ログ記述・ドキュメント文字列から推測して作成しています。機能追加や振る舞いの詳細は実際の API ドキュメント・設計書（PortfolioConstruction.md / StrategyModel.md / BacktestFramework.md 等）を併せて参照してください。