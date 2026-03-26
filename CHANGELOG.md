# Changelog

すべての変更は Keep a Changelog のフォーマットに従っています。  
このファイルは、コードベースから推測できる実装内容・設計方針を元に作成した初期リリース向けの変更履歴です。

全般:
- パッケージ名: kabusys
- 初期バージョン: 0.1.0
- リリース日: 2026-03-26

## [Unreleased]

## [0.1.0] - 2026-03-26
初期公開リリース。日本株自動売買システムのコアライブラリ群を実装しました。以下は主要な追加機能・振る舞いの概要です。

### 追加 (Added)
- 全体
  - パッケージ初期化 (src/kabusys/__init__.py): version を "0.1.0" に設定し、主要サブパッケージを公開 (data, strategy, execution, monitoring)。
- 環境設定 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数の読み込みロジックを実装。
    - プロジェクトルートを .git または pyproject.toml で探索して自動で .env/.env.local を読み込む（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理（クォートあり/なしでの挙動差）に対応。
    - .env.local は .env の上書きとして読み込まれる（ただし OS 環境変数は保護され上書きされない）。
  - Settings クラスを提供し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や、パス設定（DuckDB/SQLite）、環境モード（development/paper_trading/live）・ログレベルの検証ロジックを提供。
- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N 件を選出（同点時は signal_rank 昇順でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分を実装。全銘柄のスコアが 0 の場合は等配分にフォールバックして WARNING を出力。
  - risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、1セクター上限 (デフォルト 30%) を超過しているセクターの新規候補を除外。unknown セクターは除外対象としない。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックし警告を出力。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算を実装。リスクベースの計算（risk_pct / stop_loss_pct）、単元株（lot_size）丸め、1銘柄上限・全体利用率上限・手数料/スリッページ想定(cost_buffer)を考慮した aggregate cap スケールダウンと残差配分ロジックを実装。
- 戦略 (src/kabusys/strategy/)
  - feature_engineering.build_features: research モジュールが算出した生ファクターを統合し、ユニバースフィルタ（最低株価/最低売買代金）、Zスコア正規化（指定列）・±3クリップを行った上で features テーブルに日付単位で置換（冪等）で書き込む処理を実装。DuckDB 接続を受け取る。
  - signal_generator.generate_signals: features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付けして final_score を算出。Bear レジームでは BUY を抑制。SELL はストップロス／スコア低下条件で判定。signals テーブルへ日付単位で置換（冪等）で書き込む処理を実装。
    - weights の受け付け/検証（デフォルト重みへのフォールバック、合計を 1.0 に正規化）。
    - AI スコアが欠けている場合は中立値（0.5）で補完。
    - features 空の場合は BUY を生成せず SELL 判定のみ実施。
- リサーチ (src/kabusys/research/)
  - factor_research: momentum / volatility / value のファクター計算を実装（prices_daily/raw_financials を参照）。200日 MA・ATR 等のウィンドウ処理やデータ不足時の None 返却を含む。
  - feature_exploration: 将来リターン calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（平均ランク処理）を実装。外部依存は使用せず純粋に Python と DuckDB で算出。
- バックテスト (src/kabusys/backtest/)
  - simulator
    - PortfolioSimulator: メモリ上でのポートフォリオ状態管理、SELL を先に処理してから BUY を処理する擬似約定ロジック、スリッページ（BUY:+、SELL:-）・手数料率・単元指定（lot_size）をサポート。TradeRecord / DailySnapshot 型を定義。
    - SELL は保有全量をクローズする設計（部分利確は現バージョンでは未対応）。
  - metrics
    - calc_metrics: DailySnapshot と TradeRecord から各種評価指標（CAGR, Sharpe Ratio, Max Drawdown, win rate, payoff ratio, total trades）を計算するユーティリティを実装。

### 変更 (Changed)
- 設計上の注記（コード内ドキュメント）:
  - research/strategy/backtest モジュールは DB や外部発注 API に依存しない設計（DuckDB と生データのみ参照）で、ルックアヘッドを避けるため target_date 時点のデータのみ使用する方針を明記。
  - ロギングを多数の箇所に追加し、異常系での警告・デバッグ情報を出力するようにした（欠損価格、features 未存在、weights 不正値等）。

### 修正 (Fixed)
- スポット修正／安全策:
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に等配分へフォールバックしログ出力。
  - position_sizing: price 欠損や 0 の価格を安全にスキップする挙動を追加してクラッシュを回避。
  - _generate_sell_signals: 価格が欠損する場合は SELL 判定をスキップし警告ログを出す仕様により誤クローズを防止。
  - generate_signals: ai_scores のサンプル不足や未知の weights キー/無効値を検出して除外、合計 1.0 で再スケールするロジックを実装。

### 既知の制限・注意事項 (Notes / Known limitations)
- 部分利確・トレーリングストップは未実装（signal_generator 内でも未実装としてコメントあり）。SELL は現状「保有全量をクローズ」。
- position_sizing で price が欠損（0.0）の場合、エクスポージャー算出が過少になる可能性がある旨の TODO コメントあり（将来的に前日終値などのフォールバックを検討）。
- calc_regime_multiplier の bear=0.3 は追加セーフガードとして設計されているが、generate_signals は bear レジーム時にそもそも BUY を生成しない設計。multiplier は主に中間局面 (neutral 等) の資金制限向け。
- 実行層（execution）やモニタリング（monitoring）パッケージはパブリック API として名前は公開されているが、今回のスナップショットでは具体的実装が不足しているファイルがある可能性あり（例: execution/__init__.py は空）。
- 一部 docstring に TODO が残っており、将来的な仕様拡張（銘柄別 lot_size、価格フォールバック、部分利確等）が想定されている。
- ソースの一部（ファイル末尾）が切れている/未記載の可能性があるため、実運用前に追加のレビュー・テストが必要。

### セキュリティ (Security)
- 環境変数の取り扱いに関する基本的な保護（OS 環境変数優先、.env.local による上書き制御）を実装。ただし機密情報の管理（Vault 等）の導入は想定外。

---

参照:
- 各モジュール内の docstring / コメントは設計思想・制約・将来の TODO を詳細に説明しています。実運用前にドキュメントとテストを整備することを推奨します。