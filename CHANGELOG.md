# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
バージョンは semver（MAJOR.MINOR.PATCH）を想定します。

## [0.1.0] - 2026-03-26

初回公開リリース。

### 追加 (Added)
- パッケージ初期構成
  - パッケージメタ情報: kabusys/__init__.py に __version__="0.1.0" を追加。

- 環境変数／設定管理 (src/kabusys/config.py)
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で判定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効にするフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装（export 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応）。
  - 環境変数必須チェック用の _require と Settings クラスを実装。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL, DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）などの既定値を提供。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の値検証メソッドを実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- ポートフォリオ構築・リスク制御 (src/kabusys/portfolio/*.py)
  - 銘柄選定
    - select_candidates: BUY シグナルを score 降順、同点は signal_rank 昇順でタイブレークし上位 N を選択。
  - 重み計算
    - calc_equal_weights: 等金額配分を実装。
    - calc_score_weights: スコア加重配分を実装（全スコアが 0 の場合は等分にフォールバックして WARNING）。
  - リスク調整
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、1 セクターの上限を超える場合に同セクターの新規候補を除外（"unknown" セクターは制限対象外）。
      - sell_codes 引数で当日売却予定銘柄をエクスポージャー計算から除外可能。
      - price 欠損時の挙動に関する TODO コメントあり（将来的に代替価格を検討）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を実装（bull=1.0, neutral=0.7, bear=0.3、未知は 1.0 でフォールバックかつ WARNING）。
  - ポジションサイズ算出
    - calc_position_sizes: allocation_method = "risk_based" / "equal" / "score" をサポート。単元（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金 available_cash 超過時のスケーリング）、cost_buffer（手数料・スリッページ見積り）を実装。残差処理で lot_size 単位の追加配分を行い再現性を確保。

- 特徴量計算（Strategy 用） (src/kabusys/strategy/feature_engineering.py)
  - build_features: research モジュールから得た生ファクターをマージし、ユニバースフィルタ（価格 >= 300 円、20 日平均売買代金 >= 5 億円）を適用、Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップし features テーブルへ日付単位で置換（冪等）して保存。DuckDB を用いたトランザクション処理とエラーハンドリングを実装。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals: features と ai_scores を統合して component スコア（momentum/value/volatility/liquidity/news）を算出し final_score を計算。重みのマージ・検証・正規化ロジックを導入（不正なユーザー指定重みはログでスキップ）。AI スコア未登録銘柄は中立値で補完。
  - Bear レジーム検知（ai_scores の regime_score 集計平均が負かつサンプル数閾値以上）時は BUY シグナルを抑制。
  - SELL シグナル（エグジット）判定:
    - ストップロス（終値/avg_price - 1 < -8%）優先判定。
    - final_score が閾値未満の場合は score_drop。
    - features に存在しない保有銘柄は score=0.0 として SELL 判定（ログ出力）。
  - signals テーブルへの日付単位の置換（冪等）を実装。
  - 未実装の将来拡張点（トレーリングストップ、時間決済）をコメントで明記。

- リサーチ（ファクター計算・探索） (src/kabusys/research/*.py)
  - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA の乖離率）を DuckDB SQL で計算。
  - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、volume_ratio を計算。true_range の NULL 処理に注意。
  - calc_value: raw_financials から最新財務（target_date 以前）を取り、PER / ROE を計算（EPS が 0/欠損の場合は None）。
  - 解析ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: factor_records と forward_returns を結合して Spearman のランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、カラム別の統計要約（count/mean/std/min/max/median）を実装。

- バックテストフレームワーク (src/kabusys/backtest/*.py)
  - metrics: DailySnapshot / TradeRecord からバックテスト指標（CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、total_trades）を計算するユーティリティを実装。
  - simulator: PortfolioSimulator を実装。メモリ内で cash / positions / cost_basis / history / trades を管理。execute_orders は SELL を先に、BUY を後に処理。スリッページ率・手数料率を考慮した約定ロジックおよび TradeRecord を生成。部分約定・単元処理の設計あり（ファイル末尾は一部未表示）。

- モジュール公開インターフェース
  - package の __all__ / 各サブモジュールで公開 API を整理（strategy.build_features, strategy.generate_signals, portfolio.* の主要関数等）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 既知の制約・注意点 (Notes)
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性があり、将来的に前日終値や取得原価でフォールバックする案がコメントに存在。
- signal_generator: トレーリングストップや時間決済などの一部エグジット条件は未実装（コメントで明記）。
- build_features / generate_signals の DB 書き込みは日付単位の置換（DELETE + INSERT）で冪等性を担保しているが、トランザクション中の例外で ROLLBACK を試みる実装がある。DuckDB 接続の例外挙動は実運用での検証が必要。
- .env パーサは多くの一般的ケースに対応しているが、非常に特殊な .env 構文には対応しない可能性あり。

---

このリリースは初期実装をまとめたもので、戦略仕様書（StrategyModel.md / PortfolioConstruction.md 等）に沿った純粋関数群と DuckDB ベースのデータ処理、バックテスト・シミュレーション基盤を提供します。今後のバージョンで実運用向けの堅牢性向上、単体テスト・統合テストの追加、実マーケット接続ロジック（execution 層）等を順次追加予定です。