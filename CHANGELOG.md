# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
リリースバージョンはパッケージ内の __version__（0.1.0）に基づきます。

## [0.1.0] - 2026-03-22

初期公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージとエントリポイントを追加（__version__ = 0.1.0）。
  - パッケージの public API を __all__ で整理（data, strategy, execution, monitoring 等）。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。  
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト等で利用）。
  - .env パーサを実装:
    - export プレフィックス対応、コメント行スキップ。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォート無し時の inline コメント解析（直前が空白またはタブの場合に # をコメントと認識）。
    - 読み込み失敗時は警告を発行。
  - 環境設定ラッパー Settings を提供。主なプロパティ:
    - jquants_refresh_token（JQUANTS_REFRESH_TOKEN 必須）
    - kabu_api_password（KABU_API_PASSWORD 必須）
    - kabu_api_base_url（デフォルト http://localhost:18080/kabusapi）
    - slack_bot_token, slack_channel_id（必須）
    - duckdb_path（デフォルト data/kabusys.duckdb）、sqlite_path（デフォルト data/monitoring.db）
    - env（KABUSYS_ENV のバリデーション: development / paper_trading / live）
    - log_level（LOG_LEVEL のバリデーション: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev ヘルパー
- 戦略関連（kabusys.strategy）
  - feature_engineering.build_features
    - research モジュールのファクター（calc_momentum, calc_volatility, calc_value）を統合して features テーブルへ保存。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値を抑制。
    - 日付単位の削除→挿入（トランザクション + バルク挿入）により冪等性を保証。ロールバック時に警告ログ。
  - signal_generator.generate_signals
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を持ち、ユーザ提供の weights を検証・マージ・再スケール。
    - AI スコアが無い銘柄は中立（0.5）で補完。
    - Bear レジーム検知（ai_scores の regime_score の平均が負且つサンプル数閾値を満たす場合）で BUY を抑制。
    - BUY 判定は閾値（デフォルト 0.60）以上の銘柄。SELL 判定はストップロス（-8%）またはスコア低下を採用。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）、signals テーブルへ日付単位の置換（トランザクション）。
    - 重みの入力値検証や NaN/Inf 対応、無効キーのスキップにより堅牢化。
- リサーチ関連（kabusys.research）
  - factor_research:
    - calc_momentum（1/3/6 ヶ月相当のリターン、MA200 乖離率）
    - calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）
    - calc_value（最新の raw_financials と価格から PER / ROE）
    - 実装は DuckDB の SQL を主体としており prices_daily / raw_financials のみ参照。
  - feature_exploration:
    - calc_forward_returns（指定基準日から複数ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman ランク相関の実装、同順位は平均ランクで処理）
    - factor_summary（各カラムの count/mean/std/min/max/median）
    - rank ユーティリティ（同順位処理は round(v, 12) での丸めを考慮）
  - research パッケージの __all__ を整理。
  - pandas 等に依存せず標準ライブラリ + DuckDB のみで実装。
- バックテスト（kabusys.backtest）
  - simulator:
    - DailySnapshot / TradeRecord データクラス
    - PortfolioSimulator: BUY/SELL の擬似約定、スリッページ（割合指定）と手数料モデルを適用。
    - SELL は保有全量クローズ、BUY は割当額に基づき株数を切り捨て、手数料を考慮した再計算ロジックを実装。
    - mark_to_market で終値評価、終値欠損時は 0 で評価して警告ログ。
  - metrics:
    - calc_metrics（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades）
    - 各メトリクスの独立関数を実装（境界ケースで 0 を返す安全な実装）。
  - engine:
    - run_backtest: 本番 DB から必要テーブルをインメモリ DuckDB にコピーして日次シミュレーションを実行。
    - _build_backtest_conn: date 範囲でテーブルをフィルタしてコピー、market_calendar は全件コピー。
    - シミュレーションループ:
      1. 前日シグナルを当日始値で約定（SELL→BUY の順）
      2. positions テーブルにシミュレータの保有状態を書き戻し（generate_signals の SELL 判定に必要）
      3. 終値で時価評価・履歴記録
      4. generate_signals を呼び出して翌日シグナル生成
      5. ポジションサイジング（max_position_pct 等のパラメータ）
    - run_backtest のデフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20
    - DB 書き戻し・読み取り時に例外を捕捉してログ出力する実装

### 仕様・設計上の注意 (Notes)
- 外部 API や実口座への操作は本実装では行いません。全ての研究・戦略・バックテストロジックは DuckDB と標準ライブラリ内で完結します。
- DB スキーマに依存するテーブル（最低限必要なもの）:
  - prices_daily, features, raw_financials, ai_scores, positions, signals, market_calendar, market_regime
  - run_backtest は本番 DB からこれらをコピーする前提です。schema 初期化関数 init_schema(":memory:") を利用。
- 環境変数の必須項目（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これら未設定時は Settings がエラー（ValueError）を投げます。
- 安全・冪等性:
  - features / signals / positions 等への書き込みは「date ごとに DELETE -> INSERT」方式で原子性を確保（トランザクション）。例外発生時は ROLLBACK を試行し、ロールバック失敗時は警告ログ。
- デフォルトの戦略挙動:
  - Z スコアは ±3 でクリップして外れ値影響を抑制。
  - AI スコアの欠損は中立（0.5）で補完。
  - Bear レジーム検知により BUY が抑制される場合があります（regime_score の平均が負且つサンプル数閾値を満たす場合）。
- 実装上未完・保留の機能（既存コード内に注記あり）
  - _generate_sell_signals 内で言及されている条件のうち、トレーリングストップ（peak_price に依存）と時間決済（保有 60 営業日超）などはいずれも未実装。必要な追加カラム（positions に peak_price / entry_date 等）が未整備。
  - calc_value では PBR・配当利回りは未実装。
  - positions テーブルへ書き戻す際、market_value は NULL を挿入（nullable）。
- ロギング:
  - 多くの関数で debug/info/warning ログを出力するため、LOG_LEVEL の設定により出力制御可能。
- テスト性:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により .env の自動読み込みを無効化でき、ユニットテストで環境を制御しやすくしています。
  - 外部ライブラリ（pandas 等）に依存していないため、軽量なテスト環境構築が可能。

### 既知の制約 / 制限 (Known issues)
- 一部の売買ロジックは簡略化（例: SELL は常に保有全量をクローズ、部分利確は非対応）。
- 実データの欠損（価格や財務データ）がある場合、多くの指標で None を返す仕様。これを踏まえた上での補完ロジック（中立値 0.5 等）を採用していますが、その影響を評価してください。
- バックテストではシグナル生成・ポジション反映のタイミングや資金管理ロジックが本番と差が出ないよう注意が必要です（市場実行の遅延等は再現しない）。

---

今後の予定（例）
- トレーリングストップ・時間決済の実装（positions テーブルに peak_price / entry_date を保存する仕組みの追加）。
- PBR / 配当利回りなどバリューファクターの拡張。
- execution 層（kabuステーション連携）と monitoring / Slack 通知の実装・接続テスト。