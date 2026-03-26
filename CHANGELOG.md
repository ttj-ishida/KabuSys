# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

なお、本 CHANGELOG は提示されたコードベースの内容から機能・仕様を推測して作成しています。

## [0.1.0] - 2026-03-26

### 追加 (Added)
- パッケージ初回公開相当のリリース。主なモジュールと機能を追加。
- 基本情報
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装。読み込み優先度は OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルのパースロジックを実装（コメント行、export プレフィクス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応）。
  - 読み込みに失敗した際の警告発行ロジックを追加。
  - Settings クラスを提供し、必須環境変数取得（_require）・既定値・検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）を実装。
  - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）を Path オブジェクトで取得するユーティリティを追加。
- ポートフォリオ構築 (src/kabusys/portfolio/)
  - 銘柄選定: select_candidates — スコア降順、同点は signal_rank でタイブレーク。上位 N を返す。
  - 配分重み:
    - calc_equal_weights — 等金額配分。
    - calc_score_weights — スコア加重配分。全銘柄スコアが 0 の場合は等配分にフォールバックし警告を出力。
  - リスク調整:
    - apply_sector_cap — セクター集中制限（既存保有のセクター比率が上限を超える場合、新規候補を除外）。"unknown" セクターは上限を適用しない。
    - calc_regime_multiplier — 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知のレジームは警告を出して 1.0 にフォールバック）。
  - 株数決定・単元丸め: calc_position_sizes — allocation_method (risk_based / equal / score) に対応。lot_size, cost_buffer, max_position_pct, max_utilization を考慮した per-position / aggregate キャップ処理を実装。aggregate 超過時のスケーリングと残差処理（lot 単位で再配分）。
- ストラテジー (src/kabusys/strategy/)
  - 特徴量作成: build_features — research モジュールから取得した生ファクターをマージし、ユニバースフィルタ（最低株価・平均売買代金）を適用、数値ファクターを Z スコア正規化して ±3 でクリップし、features テーブルへ日付単位で UPSERT（トランザクション）する処理を実装。
  - シグナル生成: generate_signals — features と ai_scores を統合してコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出、重み付き合算で final_score を計算。Bear レジーム判定により BUY を抑制。BUY/SELL シグナルを生成し signals テーブルへ日付単位で置換（トランザクション）。
    - ウェイトのマージ・検証（既定値へのフォールバック、合計が 1 になるよう再スケール）。
    - SELL 条件としてストップロス（終値に対する損失閾値）とスコア低下を実装。
- リサーチ（研究） (src/kabusys/research/)
  - ファクター計算群:
    - calc_momentum — mom_1m / mom_3m / mom_6m / ma200_dev の計算。
    - calc_volatility — ATR（atr_20 / atr_pct）、avg_turnover、volume_ratio の計算。
    - calc_value — per / roe の計算（raw_financials から当該日以前の最新財務データを参照）。
  - 特徴量探索:
    - calc_forward_returns — 与えられたホライズンに対する将来リターンを一括で計算する SQL 実装。
    - calc_ic — ファクター値と将来リターンの Spearman ランク相関（IC）を計算。
    - factor_summary — 各カラムの基本統計量（count/mean/std/min/max/median）を算出。
    - rank — 同順位平均ランクを返すユーティリティ（丸めによる ties の扱いを工夫）。
  - research パッケージから主要関数をエクスポート。
- バックテスト (src/kabusys/backtest/)
  - PortfolioSimulator — 擬似約定ロジック（SELL を先に処理、BUY は指定株数で約定）、スリッページ率・手数料率を適用した約定価格および TradeRecord の生成。メモリ内で positions / cost_basis / history / trades を管理。
  - データクラス: DailySnapshot, TradeRecord。
  - 評価指標: calc_metrics — CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティ。
- ロギング・エラーハンドリング
  - 各モジュールに適切なログ出力（info/debug/warning）を追加。トランザクション失敗時の ROLLBACK トライと警告出力を実装。
- 型アノテーションとドキュメンテーション
  - 関数に型ヒント、モジュールにドキュメンテーション文字列と設計方針を追加。README 相当の設計参照（StrategyModel.md 等）に従った実装注釈あり。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 廃止 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

### 既知の制約・今後の改善点（注意事項）
- config._find_project_root は __file__ の親ディレクトリから .git / pyproject.toml を探索するため、配布後の環境や unusual packaging によっては自動 .env ロードがスキップされる可能性がある点に注意。
- .env のパースではクォート内のエスケープに対応するが、すべての shell の振る舞いを再現しているわけではない。
- apply_sector_cap は price_map に 0.0 がある場合にエクスポージャーを過少見積もりする旨の TODO を含む。前日終値や取得原価でのフォールバックは未実装。
- calc_position_sizes:
  - lot_size の将来的な銘柄個別対応（stocks マスタを用いた拡張）は TODO。
  - allocation_method のうち risk_based は部分的に実装されているが、細かいエッジケースの取り扱いは今後のテストで調整が必要。
- signal_generator:
  - SELL の高度な条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date 等が必要）。
  - Bear レジームでは generate_signals が BUY を生成しない設計（明示された仕様）。
- backtest.PortfolioSimulator の実装途中（ファイル末尾が切れている可能性あり）。部分的に実装済みの関数があるため、実運用前に未完部分の確認が必要。
- external API（kabu API、Slack、J-Quants 等）への接続・実行層は本リリースでは直接含まれておらず、execution パッケージはプレースホルダとなっている（src/kabusys/execution/__init__.py は空）。

---

今後のリリースでは、上記の TODO / 未実装事項の対応、より多くのテストや型チェック、単元ごとの lot_size 対応、実行（execution）層の実装、そして運用向けの堅牢化（エラー回復・監視・メトリクス拡張）を予定しています。