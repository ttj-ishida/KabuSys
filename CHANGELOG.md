# Changelog

すべての重要な変更履歴を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-26
初回リリース

### Added
- パッケージ初期バージョンを追加
  - kabusys パッケージ v0.1.0 を導入。

- 環境変数 / 設定管理
  - 自動 .env ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml に基づく）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 高度な .env パーサ実装:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート文字列のバックスラッシュエスケープ対応。
    - クォートなし値のインラインコメント処理（`#` の直前が空白／タブの場合にコメントとみなす）。
  - Settings クラスを提供:
    - 必須値取得（_require によるエラー送出）。
    - J-Quants / kabuステーション / Slack / DB（DuckDB / SQLite）の設定プロパティ。
    - 環境（development / paper_trading / live）とログレベルの検証。
    - is_live/is_paper/is_dev ヘルパー。

- ポートフォリオ構築 (kabusys.portfolio)
  - 候補選定:
    - select_candidates: score 降順、同点は signal_rank 昇順で上位 N を選択。
  - 重み計算:
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額へフォールバック、警告ログ）。
  - リスク調整:
    - apply_sector_cap: セクター集中制限（既存保有比率が閾値を超えるセクターの新規候補除外）。"unknown" セクターは対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull:1.0 / neutral:0.7 / bear:0.3）。未知レジームは 1.0 にフォールバック（警告ログ）。
  - ポジションサイジング:
    - calc_position_sizes: allocation_method に応じた株数算出（risk_based / equal / score）。
    - risk_based: 損切り率 stop_loss_pct と risk_pct に基づく算出。
    - max_position_pct / max_utilization による per-position と aggregate の上限管理。
    - lot_size（単元株）で丸め、cost_buffer を用いた保守的コスト見積り。
    - aggregate cap 超過時のスケールダウンと余剰分の lot 単位での追加配分ロジック（端数処理に再現性あり）。
    - 未取得価格や非正の価格はスキップし、ログ出力。

- 戦略（feature engineering / signal generation）
  - feature_engineering.build_features:
    - research モジュールの生ファクターを統合して features テーブルへ UPSERT（冪等操作）。
    - ユニバースフィルタ: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）および ±3 でクリップ。
    - DuckDB トランザクション（BEGIN/DELETE/INSERT/COMMIT）で日付単位の置換を実現。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して final_score を算出。
    - コンポーネントスコア算出ルーチン: momentum / value / volatility / liquidity（シグモイド変換等）。
    - AI ニューススコアを統合（未登録は中立扱い）。
    - weights の検証・マージ・正規化（未知キーや非数値は無視、合計が 1 になるようリスケール）。
    - Bear レジーム検知（AI の regime_score 平均が負かつサンプル数 >= 3）時は BUY シグナル抑制。
    - BUY シグナル閾値（デフォルト 0.60）以上を BUY、SELL はエグジット条件（ストップロス -8%、score 低下）で生成。
    - SELL 優先ポリシー（SELL 対象を BUY から除外しランクを再付与）。
    - signals テーブルへの日付単位置換で冪等性を担保。
    - 価格欠損や features 未登録時に警告ログを出力し安全に処理。

- リサーチ（research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率の計算（true range の NULL 伝播を厳密に管理）。
    - calc_value: raw_financials の最新財務データと株価を組み合わせて PER / ROE を算出（EPS が 0 の場合は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括 SQL 取得。
    - calc_ic: スピアマンのランク相関（IC）を計算（有効レコードが 3 件未満なら None）。
    - rank: 同順位は平均ランクにする実装（比較前に round(..., 12) を行うことで浮動小数誤差の影響を低減）。
    - factor_summary: count/mean/std/min/max/median の統計サマリー。
  - research パッケージの公開 API を整備。

- バックテスト（backtest）
  - metrics.calc_metrics: DailySnapshot と TradeRecord から評価指標を一括計算し BacktestMetrics を返す。
    - 指標: CAGR, Sharpe Ratio（無リスク金利=0）, Max Drawdown, Win Rate, Payoff Ratio, Total Trades。
  - simulator.PortfolioSimulator:
    - メモリ内ポートフォリオ管理（cash, positions, cost_basis, history, trades）。
    - execute_orders: SELL を先に処理し、BUY を後で処理（資金確保）。SELL は保有全量クローズ（部分利確非対応）。
    - スリッページ（BUY は +、SELL は -）および手数料率を考慮。TradeRecord として約定を記録。
    - DailySnapshot / TradeRecord の dataclass を提供。

- ロギング / エラーハンドリング
  - 多数の箇所でログ出力（info/debug/warning）を追加し、データ欠損時に安全にフォールバックする設計。
  - DB 書き込み時のトランザクションの失敗時は ROLLBACK を試み、失敗ログを出力して例外を再送出。

### Changed
- 初版リリースのため、変更履歴は該当なし（新規導入）。

### Fixed
- 初版リリースのため、修正履歴は該当なし。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### Notes / Known limitations / TODO
- apply_sector_cap:
  - price が欠損（0.0）の場合にセクターエクスポージャーが過小見積りされる可能性がある。将来的に前日終値や取得原価をフォールバック価格として使う拡張を検討中（TODO コメントあり）。
- calc_position_sizes:
  - 現状 lot_size は全銘柄共通で扱う。将来的に銘柄毎の lot_map（個別単元）へ拡張する予定（TODO コメントあり）。
- signal_generator:
  - トレーリングストップや時間決済等の一部エグジット条件は未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- simulator:
  - SELL は全量クローズのみ対応（部分利確/部分損切り非対応）。
- 一部ユーティリティ（kabusys.data.stats.zscore_normalize や Slack/Execution 層の実装）は本リリースでは外部モジュールや別パッケージに依存（コードベース内に参照ありが定義は別ファイル／未提示の可能性あり）。

----
この CHANGELOG はコードベース（src/ 以下）の実装内容から推測して作成しています。仕様書（PortfolioConstruction.md, StrategyModel.md 等）に基づく設計注釈や TODO コメントも反映しています。