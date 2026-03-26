# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  
リリース日はリポジトリに含まれる __version__（src/kabusys/__init__.py）に基づき記載しています。

## [0.1.0] - 2026-03-26

初回リリース — 基本的な自動売買フレームワークと付随ユーティリティ群を実装。

### 追加
- パッケージ基本情報
  - src/kabusys/__init__.py にてバージョン管理（__version__ = "0.1.0"）と公開モジュールを定義。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env / .env.local ファイルの自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - export KEY=val 形式やクォート付き値、行末コメントのパース（エスケープ対応）を備えた .env パーサを実装。
    - settings オブジェクトを提供し、J-Quants / kabuAPI / Slack / DB パス / 環境種別・ログレベル等のプロパティを提供。未設定必須変数は ValueError で明示的にエラーを返す。
    - KABU_SYS 環境（KABUSYS_ENV）と LOG_LEVEL の入力値検証を実装（許容値チェック）。

- ポートフォリオ構築（Portfolio construction）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順かつタイブレークでソートして上位 N を選択。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア比率に応じた重み計算。全スコアが 0 の場合は等金額へフォールバック（WARNING 出力）。

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。
    - リスクベースのポジション算出、per-position 上限（max_position_pct）、aggregate cap（available_cash によるスケーリング）、単元（lot_size）丸め、cost_buffer を用いた保守的コスト見積りを実装。
    - aggregate スケール時の残差処理で lot_size 単位の追加配分アルゴリズムを実装。
    - 将来拡張用のコメント（銘柄別 lot_size への拡張 TODO）。

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクターエクスポージャーを計算し、1 セクターの上限（max_sector_pct）を超過しているセクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未定義レジームは警告とともに 1.0 にフォールバック）。

  - src/kabusys/portfolio/__init__.py
    - 上記の公開 API をエクスポート。

- 戦略（feature engineering / signal generation）
  - src/kabusys/strategy/feature_engineering.py
    - research 側で計算した生ファクターをマージ・ユニバースフィルタ（最低株価・平均売買代金）適用・Z スコア正規化・±3 クリップし、features テーブルへ日付単位の UPSERT を行う。DuckDB を利用。
    - 計算は target_date 時点のデータのみを使用（ルックアヘッド防止）。
    - トランザクション（BEGIN/COMMIT/ROLLBACK）による原子性を確保。

  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して各銘柄の final_score を計算（momentum/value/volatility/liquidity/news の重み付け）。
    - デフォルト重みと閾値（default threshold=0.60）を実装。ユーザ重みは検証・正規化してマージ。
    - Bear レジーム検知時は BUY シグナルを抑制（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）。
    - SELL（エグジット）判定を実装（ストップロス・スコア低下）。価格欠損時や features 未登録の保有銘柄に対するログ警告を追加。
    - signals テーブルへの日付単位の置換（トランザクション）を実装。

- リサーチ・ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン・MA200 乖離率を DuckDB 上の SQL で計算。
    - calc_volatility: ATR（20日）、相対 ATR（atr_pct）、平均売買代金、出来高比率を計算（NULL の取り扱いに注意）。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS 欠損時は None）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）に対する将来リターンをまとめて取得するクエリ。
    - calc_ic: スピアマンのランク相関による IC 計算（有効レコードが 3 未満の場合 None を返す）。
    - factor_summary, rank: 基本統計量とランク関数を提供（外部依存なし、標準ライブラリのみ）。

  - src/kabusys/research/__init__.py にて主要関数をエクスポート。

- データ統計ユーティリティ
  - 既存モジュール kabusys.data.stats の zscore_normalize を利用する設計（他モジュールからインポートして使用）。

- バックテスト（シミュレーション & メトリクス）
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator: メモリ内でポートフォリオ状態・約定処理を管理。SELL を先に処理してから BUY を処理するポリシーを実装。スリッページ・手数料モデルを反映した約定を想定（TradeRecord にスリッページ反映済み price, commission を記録）。
    - DailySnapshot / TradeRecord の dataclass を定義。

  - src/kabusys/backtest/metrics.py
    - calc_metrics: history（DailySnapshot リスト）と trades（TradeRecord リスト）から BacktestMetrics（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio, total_trades）を計算。
    - 内部に各指標計算ルーチンを実装（年次化などの前提を明記）。

### 変更
- N/A（初回リリースのため過去の変更は無し）

### 修正
- N/A（初回リリースのため過去の修正は無し）

### 既知の未実装 / TODO（注意事項）
- position_sizing: 銘柄ごとの単元 (lot_size) を銘柄マスタから受け取る拡張は TODO（現在はグローバルな lot_size を使用）。
- risk_adjustment.apply_sector_cap: 価格欠損（price_map に 0.0/未存在）の扱いによりセクターエクスポージャーが過少評価される可能性があり、前日終値や取得原価をフォールバックする拡張を検討中（TODO コメントあり）。
- signal_generator._generate_sell_signals: トレーリングストップや時間決済（保有 60 営業日超）など一部エグジット条件は未実装（positions テーブルに peak_price / entry_date が必要）。
- feature_engineering では PER 等の一部ファクターを features テーブルに保存するが、PBR・配当利回り等はいまだ未実装。
- calc_regime_multiplier: 未知のレジーム値に対しては 1.0 をフォールバック（警告ログ）。

### 破壊的変更
- なし

### セキュリティ
- なし

---

今後のリリースでは、ユニットテストの追加、外部 API（kabuステーション）との統合レイヤー、銘柄別単元対応、さらなるエグジット戦略（トレーリングストップ等）や実約定を想定した execution 層の実装を予定しています。