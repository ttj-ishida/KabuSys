# Changelog

すべての重要な変更履歴をここに記載します。本ファイルは Keep a Changelog の形式に準拠しています。  

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

## [0.1.0] - 2026-03-26

初回リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを実装。公開 API として data / strategy / execution / monitoring 等をエクスポートするように設定（src/kabusys/__init__.py）。
  - バージョン番号を 0.1.0 として設定。

- 環境設定・ロード (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env パーサを独自実装（export プレフィックス対応、シングル/ダブルクォート処理、インラインコメントの扱い、無効行スキップ）。
  - .env の読み込み順序は OS 環境変数 > .env.local > .env（.env.local は override）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途）。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス 等の設定をプロパティ経由で取得可能。必須キー未設定時は ValueError を投げる `_require()` を採用。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。is_live / is_paper / is_dev のユーティリティプロパティあり。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - 候補選定と重み算出（portfolio_builder.py）
    - select_candidates: BUY シグナルをスコア降順、同スコア時は signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率に応じた配分。全スコアが 0 のときは等配分にフォールバック（警告を出力）。
  - リスク調整（risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター露出が閾値を超える場合、新規候補を除外するロジック（sell_codes により当日売却予定銘柄を除外可能）。"unknown" セクターは上限適用除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - 株数決定・単元処理（position_sizing.py）
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。
    - risk_based: 許容リスク率 / 損切り率からベース株数を決定。単元（lot_size）で丸め。
    - equal/score: 重みと max_utilization を用いた配分、per-position 上限（max_position_pct）を考慮。
    - aggregate cap: 全銘柄の投資総額が available_cash を超える場合にスケールダウンし、小数端数を lot_size 単位で再配分するアルゴリズムを実装。cost_buffer による保守的コスト見積りをサポート。
    - 将来的な拡張点として銘柄別 lot_size のサポートを想定（TODO コメントあり）。

- 戦略（strategy）
  - 特徴量生成（src/kabusys/strategy/feature_engineering.py）
    - research モジュールの生ファクター（momentum / volatility / value）を取得し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定列を Z スコア正規化し ±3 でクリップ。DuckDB を用いた features テーブルへの日付単位アップサート（トランザクションで原子性保証）。
    - ユニバース閾値（デフォルト: price >= 300 円、20日平均売買代金 >= 5 億円）を採用。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features テーブルと ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付き合算で final_score を計算（デフォルト重みを実装）。
    - final_score の閾値（デフォルト 0.60）以上で BUY シグナルを生成。Bear レジーム検出時は BUY を抑制（Bear は AI レジームスコア平均が負かつサンプル数閾値を満たす場合）。
    - SELL（エグジット）判定ロジックを実装（ストップロス -8% とスコア低下）。SELL 優先ポリシーにより SELL 対象は BUY から除外し、BUY は再ランク付け。
    - signals テーブルへの日付単位置換をトランザクションで実行（冪等）。
    - weights のユーザ指定は妥当性チェックと正規化を行う。

- リサーチ（src/kabusys/research/）
  - factor_research.py: momentum / volatility / value の計算を実装（DuckDB を使用）。
    - mom_1m/3m/6m、ma200_dev / atr_20 / atr_pct / avg_turnover / volume_ratio / per / roe を算出。
  - feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ファクタ統計サマリー（factor_summary）、rank ユーティリティを実装。
    - calc_forward_returns は複数ホライズンをサポートし、SQL で効率的に取得。
    - calc_ic はランク相関を正しく扱うため平均ランクでの ties 処理を実装。
  - research パッケージの公開 API を整備（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。

- バックテスト（src/kabusys/backtest/）
  - simulator.py: PortfolioSimulator を実装。メモリ内でポートフォリオ状態（cash / positions / cost_basis）と履歴（DailySnapshot / TradeRecord）を管理。
    - execute_orders は SELL を先に処理、次に BUY を処理するフローを実装。SELL は現状「保有全量クローズ」のみ（部分利確・部分損切りは非対応）。
    - スリッページ（BUY は +、SELL は -）と手数料率を考慮した約定処理、TradeRecord の記録。
  - metrics.py: バックテスト評価指標計算（CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / total_trades）を実装。入力は DailySnapshot と TradeRecord のみ。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

注意・既知の制限／TODO（コード内コメントより）
- apply_sector_cap: price_map に価格が欠損（0.0）だとセクター露出が過少見積りされてしまう恐れがあるため、将来的に前日終値や取得原価のフォールバックを検討する旨コメントあり。
- position_sizing: 銘柄別の lot_size 対応は未実装（将来的な拡張予定）。
- signal_generator の SELL 条件: トレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date 情報が必要）。
- PortfolioSimulator の SELL は保有全量クローズのみ（部分売りは未対応）。

もし変更点の粒度（コミット単位）や過去のバージョン履歴が存在する場合は、それに基づいた詳細なセクション分け（Fixed / Changed / Removed 等）を作成できます。必要であれば既存の Git 履歴から自動生成するテンプレートも作成します。