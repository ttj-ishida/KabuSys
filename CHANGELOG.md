# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム（KabuSys）のコアライブラリを提供します。以下は主要な追加点・仕様および既知の制限事項です。

### 追加（Added）
- パッケージ初期化
  - kabusys パッケージのバージョンを "0.1.0" として公開。
  - __all__ に data, strategy, execution, monitoring を含め公開インターフェースを準備。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml から探索）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env / .env.local の読み込み順序・上書きポリシー（OS 環境変数を protected として保護）。
  - 複数の .env 構文をサポート:
    - コメント行、export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメント（スペース前の # のみ）等の取り扱い。
  - Settings クラスを提供（必須環境変数の検査を含むプロパティ群）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の取得。
    - DUCKDB_PATH / SQLITE_PATH / KABU_API_BASE_URL 等のデフォルト値処理。
    - KABUSYS_ENV 値検証（development/paper_trading/live）とログレベル検証。

- 研究（research）モジュール
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR, 相対ATR（atr_pct）, 20日平均売買代金(avg_turnover), 出来高比(volume_ratio) を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務データを使用）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: ファクター列の基本統計（count, mean, std, min, max, median）を計算。
    - rank: 同順位は平均ランクを割り当てるランク付けユーティリティ。
  - research パッケージで主要関数を再公開（zscore_normalize を含む）。

- 特徴量エンジニアリング（strategy.feature_engineering）
  - build_features(conn, target_date):
    - research モジュールで計算した生ファクターを取得。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定列の Z スコア正規化（zscore_normalize を利用）および ±3 でクリップ。
    - 日付単位で features テーブルへトランザクションによる置換（DELETE + bulk INSERT）で冪等性を確保。
    - prices_daily を参照して target_date 以前の最新価格を利用（休場日対応）。

- シグナル生成（strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を組合せ、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - コンポーネント値は欠損時に中立値 0.5 で補完。
    - final_score を重み付きに合算（デフォルト重みを定義、ユーザー重みは検証・正規化して融合）。
    - Bear レジーム検出：ai_scores の regime_score 平均が負の場合に BUY シグナルを抑制。
    - BUY シグナル閾値（デフォルト 0.60）超の銘柄を BUY として登録。SELL シグナルは保有ポジションに対してエグジット条件（ストップロス -8% / final_score の閾値割れ）で生成。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクは再付与。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。
    - 不正な重みはログで警告し無視する実装。

- バックテスト（backtest）
  - simulator:
    - PortfolioSimulator: BUY/SELL 約定ロジック、スリッページ・手数料適用、ポジション・平均取得単価管理、mark_to_market による DailySnapshot 記録、TradeRecord の蓄積。
    - BUY は始値に slippage を加えて約定、資金不足時に株数を再計算して調整。SELL は保有全量をクローズ。
  - metrics:
    - calc_metrics / BacktestMetrics: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades の計算。
  - engine:
    - run_backtest(conn, start_date, end_date, ...):
      - 本番 DB から start_date-300日〜end_date の必要テーブルをインメモリ DuckDB にコピーし、バックテスト用接続を構築（signals / positions 等の汚染を防止）。
      - 日次ループで前日シグナルの約定 → positions 書き戻し → 時価評価 → generate_signals（bt_conn を用いて）→ 発注リスト組立て（ポジションサイジング）を実施。
      - _build_backtest_conn、_fetch_open_prices/_fetch_close_prices、_write_positions、_read_day_signals 等の補助関数を提供。
    - run_backtest の戻り値は BacktestResult(history, trades, metrics)。

- トランザクション・エラーハンドリング
  - features / signals のテーブル書き換えは BEGIN/COMMIT を行い、例外時は ROLLBACK を試みログ記録する実装。

### 変更（Changed）
- 初回リリースのため該当なし。

### 修正（Fixed）
- 初回リリースのため該当なし（ただし各モジュールで入力検証・欠損値処理・数値の有限チェック等の堅牢化を実装）。

### 既知の制限・未実装（Known issues / Not implemented）
- signal_generator のエグジット条件について、ドキュメントにあるトレーリングストップ（peak_price に基づく -10%）および時間決済（保有 60 営業日超）については未実装。positions テーブルに peak_price / entry_date 情報が必要。
- calc_value では PBR・配当利回り等は未実装。
- features テーブルへは avg_turnover はフィルタ用途にのみ使用され、features に保存されない（設計上の意図）。
- market_value は positions テーブル挿入時に NULL を許容し、シミュレーション内評価では参照しない。
- research.feature_exploration は pandas 等外部ライブラリに依存せず純粋 Python + DuckDB で実装しているため、大規模データでのパフォーマンスはワークロード次第。
- 自動 .env 読み込みはプロジェクトルートの特定に依存する（.git または pyproject.toml が存在しない場合は自動ロードをスキップ）。

### セキュリティ（Security）
- 初回リリースのため既知のセキュリティ脆弱性はなし。ただし機密情報は環境変数（例: API トークン）で管理することを推奨。Settings._require は未設定時に ValueError を投げるため、起動前に必要な環境変数を設定してください。

---

将来的なリリースでは以下を検討しています：
- エグジットルール（トレーリングストップ / 時間決済）の実装
- 追加ファクター（PBR・配当利回り等）の導入
- パフォーマンス最適化（大規模データセット向け）
- execution 層との統合テストおよび実運用向けの安全機構強化

もし詳細な差分（コミット単位）や特定ファイルごとの変更履歴が必要であれば、該当コミットログや Git の差分を提供してください。