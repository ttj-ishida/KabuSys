CHANGELOG.md

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

なお、この CHANGELOG はコードベースの内容から推測して作成しています。

Unreleased
---------

- (なし)

[0.1.0] - 2026-03-26
-------------------

Added
- 初回リリース。日本株自動売買ライブラリ "KabuSys" のコア機能を実装。
  - パッケージ初期化
    - kabusys.__version__ = "0.1.0"
    - パッケージエクスポート: data, strategy, execution, monitoring
  - 環境設定管理 (kabusys.config)
    - .env / .env.local 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - .env パーサ実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント処理に対応）
    - 必須値取得用 _require() と Settings クラスを提供
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等の既定値・検証ロジックを実装
      - 環境 (development / paper_trading / live) とログレベルのバリデーション
  - ポートフォリオ構築 (kabusys.portfolio)
    - ポートフォリオ候補選定・重み (portfolio_builder.py)
      - select_candidates(buy_signals, max_positions): スコア降順で候補選定、同点時は signal_rank でタイブレーク
      - calc_equal_weights(candidates): 等金額配分
      - calc_score_weights(candidates): スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）
    - リスク調整 (risk_adjustment.py)
      - apply_sector_cap(...): セクター集中上限チェック（max_sector_pct）と候補除外、"unknown" セクターは除外対象外
      - calc_regime_multiplier(regime): 市場レジームに基づく投下資金乗数（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）
    - ポジションサイズ計算 (position_sizing.py)
      - calc_position_sizes(...): allocation_method に応じた発注株数算出
        - risk_based（リスク許容率 + stop_loss に基づく）、equal / score（重みベース）
        - 1 銘柄上限、aggregate cap（available_cash）でのスケールダウン処理
        - lot_size 単位で丸め、cost_buffer を考慮して保守的にコスト見積もり
        - 価格欠損や price<=0 の際のスキップ処理
  - 戦略 (kabusys.strategy)
    - 特徴量エンジニアリング (feature_engineering.py)
      - build_features(conn, target_date): research モジュールの生ファクターを集約、ユニバースフィルタ（最低株価・流動性）、Z スコア正規化（±3 でクリップ）、features テーブルへ日付単位の置換（トランザクション）を実装
      - DuckDB を前提に prices_daily / raw_financials を参照
    - シグナル生成 (signal_generator.py)
      - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換
      - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）
      - AI スコア処理（未登録時は中立）、重みのバリデーションと合計 1.0 再スケール
      - Bear レジーム判定による BUY 抑制（ai_scores の regime_score を平均して負なら Bear。ただしサンプル閾値あり）
      - エグジット判定（ストップロス、スコア低下）実装。price 欠損時の SELL 判定スキップとログ出力
  - リサーチ (kabusys.research)
    - ファクター計算 (factor_research.py)
      - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev を計算（200 日未満は None）
      - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR に十分なデータがない場合は None）
      - calc_value(conn, target_date): price と直近の財務データから PER, ROE を計算（EPS=0/欠損時は PER=None）
    - 探索・解析ユーティリティ (feature_exploration.py)
      - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 指定ホライズンの将来リターンを一括取得
      - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンの IC（ランク相関）計算（有効レコード 3 未満は None）
      - factor_summary(records, columns): 各カラムの基本統計量（count/mean/std/min/max/median）
      - rank(values): 同順位は平均ランクとするランク付けユーティリティ
  - バックテスト (kabusys.backtest)
    - シミュレータ (simulator.py)
      - PortfolioSimulator: メモリ内ポートフォリオ管理・擬似約定ロジック
        - execute_orders(signals, open_prices, slippage_rate, commission_rate, ...): SELL を先に処理し全量クローズ、BUY は指定 shares を実行。スリッページ（BUY:+、SELL:-）・手数料反映、TradeRecord / DailySnapshot の収集
    - メトリクス (metrics.py)
      - calc_metrics(history, trades) → BacktestMetrics: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades を計算するユーティリティ群

Changed
- (初回リリースのため該当なし)

Fixed
- (初回リリースのため該当なし)

Removed
- (初回リリースのため該当なし)

Security
- (なし)

Notes / Known limitations
- .env 読み込み
  - .env/.env.local の読み込みはプロジェクトルート検出に依存。ルートが見つからない場合は自動ロードをスキップする。
  - override の扱いや protected keys（OS 環境変数保護）に注意。
- feature_engineering / signal_generator / factor_research は DuckDB のテーブル構造（prices_daily, raw_financials, features, ai_scores, positions, signals など）に依存するため、スキーマが一致しない場合は動作しない。
- apply_sector_cap: price の欠損（0.0）によりセクターエクスポージャーが過小評価される可能性があり、将来的にフォールバック価格導入が想定されている。
- signal_generator:
  - 一部のエグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - features が空の場合は BUY は発生せず、SELL 判定のみ実施される。
- position_sizing の将来拡張案: 銘柄別 lot_size（stocks マスタ）を受け取る設計に変更予定。
- calc_regime_multiplier は未知レジームで警告を出し 1.0 にフォールバックする。
- generate_signals の weights は不正値（負値・非数など）を除外し、合計を 1.0 に正規化する。

Authors / Contributors
- コードコメントに基づき作成（CHANGELOG はコードベースから推測して作成）。

References
- ドキュメント参照箇所（コード中コメント）
  - PortfolioConstruction.md, StrategyModel.md, UniverseDefinition.md, BacktestFramework.md など設計ドキュメントを前提に実装されています。