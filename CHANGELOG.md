# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

全般的な方針：
- モジュールは可能な限り純粋関数／DB非依存の設計を採用しています（ポートフォリオ構築・バックテスト等はメモリ内計算）。
- 戻り値や副作用は明確にし、欠損データに対する安全策（None チェック、ログ出力、フォールバック）を多用しています。
- DuckDB を用いた分析・シグナル生成フローを想定しています（strategy/research 層）。

## [Unreleased]

（今後の変更をここに記載します）

---

## [0.1.0] - 2026-03-26

初回リリース。日本株自動売買システムのコア機能群を実装しました。以下は主要な追加点・設計上の注意点です。

### 追加
- パッケージ基本情報
  - src/kabusys/__init__.py にバージョン情報と公開モジュールを追加 (version: 0.1.0)。

- 環境設定管理
  - src/kabusys/config.py
    - プロジェクトルート自動検出（.git または pyproject.toml）による .env 自動読み込みを実装。
    - .env ファイルのパース機能を実装（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ対応）。
    - OS 環境変数保護（protected set）と .env.local の上書きルールを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
    - Settings クラスを実装し、J-Quants / kabu / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の設定プロパティを提供。値検証（有効な env 値・ログレベル）を行う。

- ポートフォリオ構築・配分
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順（スコア同点時は signal_rank 小さい方優先）で候補を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額へフォールバックし WARNING 出力）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいた株数算出。
    - 単元（lot_size）での丸め、1株当たり上限、max_utilization・aggregate cap によるスケーリング、cost_buffer を用いた保守的コスト推定。
    - aggregate スケーリング時に残差（fractional remainder）を考慮して lot 単位で追加配分する再現性のあるアルゴリズムを実装。
    - price 欠損・非正値に対するログとスキップ処理を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクターエクスポージャーを計算し、max_sector_pct を超過しているセクターの新規候補を除外（sell 対象はエクスポージャー計算から除外可能）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数を実装。未知レジームはフォールバックして 1.0。bear は 0.3（注記あり）。

- 戦略（特徴量計算・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - build_features: research 層のファクターを取り込み、ユニバースフィルタ（最小株価/最小売買代金）、Z スコア正規化（指定列）、±3 でのクリップを行い、DuckDB の features テーブルへ日付単位で置換（トランザクション・ロールバック対応）して保存。
    - ユニバース条件や Z スコア対象列は定数化（_MIN_PRICE/_MIN_TURNOVER/_NORM_COLS）。
  - src/kabusys/strategy/signal_generator.py
    - generate_signals: features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付きで final_score を算出。
    - weights の入力検証と既定値（StrategyModel.md に準拠）を実装、合計が 1.0 でない場合は正規化。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル閾値）により BUY シグナルを抑制。
    - BUY: threshold（デフォルト 0.60）超で BUY シグナル生成（ランク付け）。
    - SELL: ストップロス（終値 / avg_price - 1 < -8%）および final_score 低下によるエグジット判定を実装。価格欠損時は SELL 判定をスキップし警告を出力。
    - signals テーブルへの日付単位置換（トランザクション・ロールバック対応）。

- リサーチ（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（200 日未満は None）を計算する SQL 実装。
    - calc_volatility: ATR20 / atr_pct、20日平均売買代金、出来高比率を計算する SQL 実装（true_range の NULL 伝播制御）。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を算出（EPS=0 の場合は None）。price と財務データ結合処理を実装。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得（1 クエリ）。horizons の検証あり。
    - calc_ic: factor と将来リターンの Spearman ランク相関（IC）計算（有効レコード < 3 の場合は None）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）・基本統計量（count/mean/std/min/max/median）を算出するユーティリティ。

- バックテスト基盤
  - src/kabusys/backtest/simulator.py
    - DailySnapshot / TradeRecord の dataclass 定義。
    - PortfolioSimulator: 初期現金を元にメモリ内でポートフォリオ状態を管理し、SELL→BUY の順で約定処理を行う execute_orders を実装。スリッページ・手数料モデル、全量売却の扱い、トレード記録の作成を行う。
  - src/kabusys/backtest/metrics.py
    - バックテスト指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を実装。日次スナップショットとトレードリストから算出。

- パッケージエクスポート整理
  - strategy / research / portfolio パッケージの __init__.py にて主要関数を公開。

### 変更（設計上の注記）
- 多くの関数は「DB 参照なし（メモリ内）」あるいは「DuckDB 接続を受け取る」形で境界を明確化（execution 層や外部 API への直接依存を排除）。
- トランザクション（BEGIN/COMMIT/ROLLBACK）を用いた日付単位の置換で冪等性と原子性を確保。
- 欠損データ（価格・財務データ等）に対する挙動を明文化：多くの場所で欠損時は該当処理をスキップしログ出力。

### 既知の制限・TODO（今後の改善候補）
- apply_sector_cap: price_map に 0.0 が含まれる場合にエクスポージャーが過少見積りされる懸念があり、前日終値や取得原価等のフォールバック価格の導入を検討中（TODO コメントあり）。
- position_sizing: lot_size を銘柄ごとに異なる値にする拡張（stocks マスタからの lot_map 受け取り）は未実装。
- signal_generator のエグジット条件
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）や時間決済（保有 60 営業日超）など、いくつかの条件は未実装。
- calc_value: PBR・配当利回り等の指標は現バージョンで未実装。
- strategy.feature_engineering と signal_generator は ai_scores / raw_financials 等のテーブル構造に依存するため、スキーマ整備とデータ投入フローが前提。
- execution 層（kabu やブローカー API との実トレード連携）は本リリースでの実装対象外（execution パッケージは存在するが実装ファイルは含まれていません）。

### 修正
- 初回公開のため該当なし（実装ベースの初期リリース）。

### セキュリティ
- 環境変数の読み込みで OS 環境を保護する仕組み（protected set）を導入。ただし .env に機密情報を含める場合はファイル管理に注意してください。

---

貢献・バグ報告・提案は issue を通じてお寄せください。今後はテストカバレッジの拡充、per-stock lot 対応、実行層との統合、追加のエグジット条件やリスク管理機能の実装を計画しています。