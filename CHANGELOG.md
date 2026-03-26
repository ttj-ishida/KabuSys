# CHANGELOG

すべての重要な変更履歴をこのファイルに記載します。  
このプロジェクトは Keep a Changelog のフォーマットに準拠します。  

最新版: 0.1.0 (初回リリース)

## [0.1.0] - 2026-03-26
初回リリース。プロジェクトのコア機能（設定管理、ポートフォリオ構築、戦略・研究モジュール、バックテスト基盤など）を実装。

### 追加 (Added)
- パッケージ初期化
  - package version: 0.1.0
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring 等）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env パースで export プレフィックス、クォート、エスケープ、インラインコメント（条件付き）に対応する独自ロジックを実装。
    - .env 読み込み時に OS 環境変数を保護する機能（protected keys）。
  - Settings クラスを提供し、以下のプロパティを取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許容）
    - LOG_LEVEL の検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev の補助プロパティ

- ポートフォリオ構成 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルを score 降順でソートし上位 N を選択（同点時の tie-breaker も考慮）。
    - calc_equal_weights: 等金額配分の重みを計算。
    - calc_score_weights: スコア比率に基づく重み計算。全スコアが 0 の場合は等金額配分にフォールバック（WARNING ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中リスクを評価して、新規候補を除外するロジックを実装（sell 予定銘柄は除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告ログを出力。
  - position_sizing:
    - calc_position_sizes:
      - allocation_method: "risk_based", "equal", "score" をサポート。
      - risk_based: 許容リスク率 (risk_pct)、stop_loss_pct に基づいて株数を算出。
      - equal/score: weight に基づき per-position と aggregate の上限を適用。
      - 単元株（lot_size）で丸め処理を実装（現在は単一 lot_size を前提）。
      - aggregate cap の超過時にはスケールダウンと残差分を考慮した再配分アルゴリズムを実装（lot 単位で再配分）。
      - cost_buffer により手数料・スリッページを見積もって安全側で判定できるように実装。
      - 価格が取得できない銘柄はスキップ（ログ出力）。

- 戦略 (kabusys.strategy)
  - feature_engineering.build_features:
    - research の生ファクター (calc_momentum / calc_volatility / calc_value) を統合。
    - ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 >= 5e8）を適用。
    - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - DuckDB を用いた日付単位の置換（DELETE -> INSERT）で features テーブルへ UPSERT（トランザクションで原子性を保証）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み: momentum 0.40 / value 0.20 / volatility 0.15 / liquidity 0.15 / news 0.10。合計が 1.0 になるように補正するロジックを実装。
    - BUY 閾値デフォルト 0.60。Bear レジーム判定時は BUY を抑制（Bear 判定は ai_scores の regime_score 平均を使用、サンプル数閾値あり）。
    - 欠損コンポーネントは中立(0.5)で補完して不当な降格を防止。
    - SELL シグナル生成 (stop_loss: -8% / score_drop: final_score < threshold) を実装。SELL 優先で BUY から除外。
    - signals テーブルへ日付単位の置換で書き込み（トランザクションで原子性を保証）。
    - ログを用いた各種警告（features 空、価格欠損、weights 不正値など）。

- リサーチ (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev を計算（200 日未満は None）。
    - calc_volatility: ATR(20)/atr_pct/avg_turnover/volume_ratio を計算、データ不足時の扱いを定義。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（EPS が 0/欠損なら PER は None）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一度の SQL クエリで取得。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - factor_summary: 指定カラムの基本統計量（count/mean/std/min/max/median）を算出。
    - rank: ties を平均ランクで処理するランク変換ユーティリティ。
  - すべて DuckDB を前提にし、外部依存を増やさない設計。

- バックテスト (kabusys.backtest)
  - metrics.calc_metrics:
    - DailySnapshot と TradeRecord から各種評価指標を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
  - simulator.PortfolioSimulator:
    - メモリ内でのポートフォリオ状態管理（cash, positions, cost_basis, history, trades）。
    - execute_orders: SELL を先、BUY を後に処理（SELL は保有全量クローズ）。スリッページ・手数料の適用。lot_size に対応。
    - TradeRecord/DailySnapshot のデータ型を定義。

- モジュールレベルの __all__ エクスポートを整備（strategy/research/portfolio 等）。

### 変更 (Changed)
- 初回リリースのため「変更」は該当なし（初期実装）。

### 修正 (Fixed)
- 初回リリースのため「修正」は該当なし。

### 既知の制約 / 注意点 (Known issues / Notes)
- .env パーサは一般的なケースに対応しているが、すべての .env フォーマットを網羅するわけではない。特に複雑な改行を含む値などは想定外の振る舞いをする可能性がある。
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少評価され、ブロックが外れる可能性あり。将来的に前日終値や取得原価によるフォールバックを検討している。
- position_sizing:
  - 銘柄別の lot_size をまだサポートしていない（全銘柄共通の lot_size を想定）。将来的に銘柄毎 lot_map で拡張予定。
  - price が取得できない場合は当該銘柄をスキップする挙動のため、データ欠損があると保有候補が減る。
- signal_generator:
  - Bear レジームでは generate_signals が BUY を抑制する設計。なお、StrategyModel の仕様に基づき Bear レジームのもとで基本的に BUY シグナルは生成されない想定。
  - SELL の追加条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- Backtest:
  - PortfolioSimulator の SELL は現状「保有全量クローズ」のみで、部分利確・部分損切りは未対応。
- ロギング:
  - 各所で警告/デバッグログを出力する設計のため、運用時は LOG_LEVEL を適切に設定することを推奨。

### 開発 TODO（今後の予定・改善点）
- 銘柄別 lot_size のサポート（stocks マスタからの読み込み）。
- apply_sector_cap の価格フォールバック戦略を導入（前日終値や取得原価の使用）。
- signal_generator にトレーリングストップや保有期間を考慮した時間決済を追加。
- execution 層の実装強化（kabu ステーション API ラッパー、注文投げの安全性向上）。
- monitoring モジュールの実装（Slack 通知やメトリクスの収集）。

---

過去の変更はここに順次追加していきます。バージョンアップ時はこの CHANGELOG を更新してください。