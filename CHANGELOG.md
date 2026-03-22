# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-22

初回公開リリース。

### 追加
- パッケージ全体
  - パッケージ名を kabusys として初期実装を追加。__version__ を "0.1.0" に設定。
  - モジュール構成: data, strategy, execution, monitoring を公開モジュールとする設計。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルまたは既存の OS 環境変数からの自動ロード機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）に基づくため CWD に依存しない。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - Settings クラスを追加:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL のデフォルト値とバリデーションを提供。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- 研究・ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER を計算（EPS が 0 または欠損のときは None）。
    - DuckDB を使用した SQL ベースの実装で、prices_daily / raw_financials テーブルを参照。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（IC）を計算するユーティリティを追加（最小サンプル数チェックあり）。
    - factor_summary: 各ファクターに対する count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクとするランク付けユーティリティを追加。
  - research パッケージの __all__ を整備し、zscore_normalize（data.stats）との統合を提供。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 関数を実装:
    - research の calc_momentum / calc_volatility / calc_value を呼び出して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラム（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を z スコア正規化し ±3 でクリップ。
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT を用いて原子性を確保）。
    - target_date 時点のデータのみを使用することでルックアヘッドバイアスを回避。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 関数を実装:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - コンポーネントごとに欠損値は中立 0.5 で補完。
    - final_score を重み付き合算（デフォルト重みを実装）し、閾値（デフォルト 0.60）を超える銘柄に BUY シグナルを生成。
    - AI による market regime 集計で Bear 相場を判定し Bear 時は BUY を抑制。
    - エグジット（SELL）判定を _generate_sell_signals で実装（ストップロス -8%、final_score が閾値未満など）。
    - signals テーブルへ日付単位で置換（原子性確保）。
    - weights 引数の検証（未知キーや無効値を無視、合計が 1 に再スケール）を実装。

- バックテストフレームワーク (kabusys.backtest)
  - simulator モジュール:
    - PortfolioSimulator を実装（メモリ内ポジション管理、約定ロジック、スリッページ・手数料反映）。
    - execute_orders: SELL を先に、BUY を後に処理。BUY は alloc に基づいて株数を算出し、手数料込みで調整。SELL は保有全量をクローズ。
    - mark_to_market: 終値で時価評価し DailySnapshot を記録（終値欠損時は 0 評価で WARNING）。
    - TradeRecord / DailySnapshot dataclass を定義。
  - metrics モジュール:
    - バックテスト評価指標を計算する calc_metrics を実装（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio, total trades）。
    - 各内部関数を個別に実装（年次化、標準偏差計算、ドローダウン計算など）。データ不足時の安全なデフォルトを導入。
  - engine モジュール:
    - run_backtest を実装:
      - production DB からインメモリ DuckDB へ必要テーブルをコピー（signals/positions を汚染しない）。
      - 日次ループで open で約定 → positions 書き戻し → 終値評価 → signal 生成 → ポジションサイジング → 次日の約定準備 を実行。
      - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20。
      - get_trading_days（data.calendar_management）と generate_signals を組み合わせてバックテストを実行。
    - バックテスト用のコピー範囲（start_date - 300日 から end_date）や market_calendar の全件コピー処理を実装。

### 変更
- （初版のため該当なし）

### 修正
- （初版のため該当なし）

### 既知の制限・未実装事項（ドキュメント）
- signal_generator の SELL 条件で説明されている一部条件は未実装:
  - トレーリングストップ（peak_price の管理が positions テーブルに未実装）
  - 時間ベース決済（保有 60 営業日超過）
- calc_value は PBR や配当利回りを現バージョンでは算出しない。
- execution パッケージの実装は現状空（発注 API 実行層は分離設計）。
- 外部モジュールへの依存:
  - data.stats.zscore_normalize が存在する前提で使用している（data パッケージの実装が必要）。
- 一部 SQL クエリは DuckDB 固有のウィンドウ関数や ROW_NUMBER を使用しており、互換性に注意。

### 互換性と移行
- 初回リリースのため互換性の破壊は該当なし。今後のリリースで API 変更がある場合はメジャーバージョンで管理予定。

### セキュリティ
- 環境変数の自動ロード機能は OS 環境変数を保護するため protected set を導入。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってテスト環境等で自動ロードを無効化可能。

---

（上記はコードベースから推測して作成した CHANGELOG です。実際のリリースノートにはユースケースや既知のバグ、パフォーマンス考慮事項を適宜追記してください。）