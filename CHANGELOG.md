CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- 現時点で未リリースの変更はありません。

0.1.0 - 2026-03-26
------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムの基盤実装を追加。
  - パッケージエントリポイント: kabusys (src/kabusys/__init__.py)
    - __version__ = "0.1.0"
    - パブリック API 候補として data, strategy, execution, monitoring を公開。

- 環境設定 / ロード機構 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - OS 環境変数を protected として .env による上書きを防ぐ機構を実装。
  - .env パーサーの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、
      インラインコメントの取り扱い（クォートあり/なしの差異）等を考慮。
  - Settings クラスを提供 (settings インスタンス):
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須設定取得（未設定時は ValueError を送出）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
    - ヘルパー: is_live / is_paper / is_dev。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - position_sizing.py:
    - calc_position_sizes: allocation_method に応じた株数決定ロジックを実装。
      - risk_based / equal / score の各方式に対応。
      - リスクベース計算、stop_loss_pct、max_position_pct、max_utilization、lot_size、cost_buffer を考慮。
      - aggregate cap のスケーリング、lot_size 単位での丸め、残余の端数配分ロジックを実装。
      - 価格欠損や不適合値を安全にスキップ。
  - risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター集中が閾値を超える場合に新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームでのフォールバックとログ警告あり。

- 戦略（特徴量生成 / シグナル） (src/kabusys/strategy/)
  - feature_engineering.py:
    - build_features: research モジュールの生ファクターを取り込み、
      ユニバースフィルタ（最低株価・最低売買代金）、Zスコア正規化（±3クリップ）を適用し、features テーブルへ冪等的に書き込み（トランザクション＋バルク挿入）。
    - DuckDB を利用した SQL ベースの価格取得や UPSERT 実装。
  - signal_generator.py:
    - generate_signals: features と ai_scores を統合して最終スコアを計算、BUY/SELL シグナルを生成して signals テーブルへ冪等的に書き込み。
      - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算。欠損コンポーネントは中立 0.5 で補完。
      - デフォルト重みと閾値（default threshold=0.60）を実装。ユーザー指定の weights は検証・補完・正規化される（無効値は無視）。
      - Bear レジーム検知時は BUY シグナルを抑制（AI の regime_score を集計して判定）。
      - SELL シグナルはストップロス（-8%）およびスコア低下で判定。SELL は BUY より優先され、BUY から除外される。
      - DB トランザクションとエラー時のロールバック保護（ROLLBACK 失敗時は警告ログ）。
      - features が空のときは BUY なしで SELL 判定のみ実行（警告ログ）。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算。データ不足時は None。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播に配慮。
    - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算（EPS が 0/欠損のときは None）。DuckDB SQL ベース。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: ファクターと将来リターンの Spearman の ρ（ランク相関）を計算。サンプル数不足時は None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量を提供。
  - 研究用関数群は外部依存を最小化（pandas 等不使用）、DuckDB のみ使用。

- バックテスト (src/kabusys/backtest/)
  - simulator.py:
    - PortfolioSimulator: 擬似約定・ポートフォリオ状態管理。cash / positions / cost_basis / history / trades を保持。
    - execute_orders: SELL を先、BUY を後で処理。スリッページ率（BUY は +、SELL は -）と手数料率を適用。SELL は現在保有全量をクローズ（部分利確未実装）。
    - TradeRecord / DailySnapshot のデータクラス定義。
  - metrics.py:
    - calc_metrics: DailySnapshot と TradeRecord から CFA 指標群（CAGR、Sharpe、最大ドローダウン、勝率、Payoff Ratio、総トレード数）を計算。
    - 各指標は欠損やゼロ除算を回避する堅牢な実装。

- 共通 / その他
  - ロギングを適切に挿入（デバッグ・警告・情報ログ）。
  - DuckDB 接続を受ける関数はトランザクションとエラー処理を考慮。
  - 多くの純粋関数化（DB 参照を限定）によりユニットテスト容易性を意識した設計。
  - README 相当の設計ドキュメントへの参照（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等）をコメントで明示。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし（実装中に意図的に安全弁・フォールバック処理を多数追加）。

Deprecated
- なし。

Removed
- なし。

Security
- 環境変数の自動ロードはデフォルトで有効だが、テストや CI のために KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

Notes / Known issues
- position_sizing / apply_sector_cap などで価格情報が欠損（0.0 や None）の場合、保守的なスキップや注釈付きログにより誤判定を抑止しているが、将来的に前日終値や取得原価によるフォールバック実装を検討している（TODO コメントあり）。
- simulator の SELL は現状で「保有全量クローズ」の実装。部分利確やトレーリングストップ等は未実装。
- feature_engineering と signal_generator は DuckDB のテーブルスキーマ（features, ai_scores, signals, positions, prices_daily, raw_financials 等）に依存する。データスキーマの整合性が前提。
- 一部の処理で引数検証やログ出力は行っているが、外部 API 連携（kabu API / Slack 等）の実行部分は本版では薄く、今後 execution 層・monitoring 層で補完予定。

Authors
- 実装コメント・ドキュメントに設計参照が豊富に含まれています。詳細は各モジュールの docstring を参照してください。

License
- リポジトリに明示されているライセンスに従ってください（本 CHANGELOG はコードから推測して作成しています）。