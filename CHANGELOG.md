CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

v0.1.0 - 2026-03-22
-------------------

初回リリース。日本株自動売買システム "KabuSys" のコア機能群を実装しました。
大まかな設計方針として、発注 API や本番口座へ直接アクセスしない研究・シミュレーション中心のモジュール構成、DuckDB をデータ基盤として利用、外部解析ライブラリ（pandas 等）への依存を避ける実装が反映されています。

Added
- パッケージ基礎
  - pakage 基点の __version__ を 0.1.0 に設定。公開モジュールを __all__ で定義。
- 環境設定管理 (kabusys.config)
  - .env / .env.local / OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック: __file__ を起点に .git または pyproject.toml を探索することで CWD に依存しない動作を実現。
  - .env 解析器の強化:
    - コメント行・空行の無視、export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュによるエスケープ処理に対応。
    - クォートなしの値に対するインラインコメント判定（直前が空白/タブの # をコメントと判定）。
  - 読み込み優先順位の実装: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書き保護。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テスト等で利用可能）。
  - Settings クラスを提供し、必須環境変数取得（_require）、型変換、バリデーション（KABUSYS_ENV, LOG_LEVEL の許容値）を実装。
  - デフォルト設定値: KABU_API_BASE_URL、データベースパス（DUCKDB_PATH / SQLITE_PATH）など。
- 研究用ファクター計算 (kabusys.research)
  - factor_research モジュール:
    - モメンタム (1M/3M/6M)、200日移動平均乖離率 (ma200_dev) を計算する calc_momentum。
    - 20日 ATR（atr_20）および相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算する calc_volatility。
    - raw_financials から直近財務データを取得して PER / ROE を計算する calc_value。
    - DuckDB のウィンドウ関数を用いた効率的な SQL ベースの実装。データ不足時は None を返す扱い。
  - feature_exploration モジュール:
    - 将来リターン計算 calc_forward_returns（horizons デフォルト [1,5,21]、入力検証あり）。
    - ランク相関（Spearman ρ）による IC 計算 calc_ic（欠損除外、サンプル数閾値を設ける）。
    - ランク付けユーティリティ rank（同順位は平均ランクを割当、丸め処理で ties 検出の安定化）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
  - research パッケージ初期化で主要 API をエクスポート。
  - 外部ライブラリに依存しない実装（標準ライブラリ + duckdb）。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で計算した生ファクターを取り込み、正規化・合成して features テーブルへ UPSERT（日付単位の置換）する build_features を実装。
  - ユニバースフィルタ実装（最低株価 300 円、20 日平均売買代金 5 億円）。
  - Zスコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 でのクリッピング。
  - トランザクションによる日付単位の置換（BEGIN/COMMIT/ROLLBACK）で原子性を保証。ROLLBACK 失敗時に警告ログ。
  - ルックアヘッドバイアス防止のため target_date 時点のデータのみ参照。
- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）から最終スコア final_score を計算して BUY/SELL シグナルを生成する generate_signals を実装。
  - デフォルト重みと閾値を実装（デフォルト weights: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、threshold=0.60）。
  - weights 引数の検証・マージ・再スケール機能（未知キー・非数値・負値は無視、合計が1でないときは正規化）。
  - AI スコア（ai_scores テーブル）を利用した Bear レジーム判定（レジームスコア平均が負の場合に BUY を抑制、最低サンプル数チェックあり）。
  - コンポーネントスコアの計算ユーティリティ（シグモイド変換、欠損は中立値 0.5 で補完）。
  - SELL 条件（実装済）:
    - ストップロス（終値/avg_price - 1 < -8%）
    - スコア低下（final_score < threshold）
    - 価格欠損時は SELL 判定をスキップして警告
    - features に存在しない保有銘柄は score=0.0 として SELL 判定（警告ログ）
  - 日付単位の signals テーブル置換（トランザクション処理）。
- バックテストフレームワーク (kabusys.backtest)
  - simulator モジュール:
    - PortfolioSimulator によるメモリ内ポートフォリオ管理、BUY/SELL の擬似約定ロジックを実装（完全クローズ方式、部分利確非対応）。
    - スリッページ（BUY は +, SELL は -）、手数料、約定株数端数処理（floor）を実装。
    - mark_to_market による終値評価と DailySnapshot 生成（終値がない場合は 0 評価で警告）。
    - TradeRecord に realized_pnl の記録（SELL 時）。
  - metrics モジュール:
    - バックテスト指標計算（CAGR, Sharpe Ratio, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 各指標の公称的実装とエッジケース処理（サンプル不足・分母ゼロ対策）。
  - engine モジュール:
    - run_backtest による日次ループ実装。
    - 本番 DB から必要データ（price/features/ai_scores/market_regime 等）を指定期間でインメモリ DuckDB にコピーする _build_backtest_conn（market_calendar は全件コピー）。
    - signals の読み取り・書き込み、positions テーブルへのシミュレータ保有情報の書き戻し（_write_positions）を含む一連のフロー。
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20。
    - コピー処理やテーブル操作で発生した例外はログに WARN を出してスキップする堅牢化。
- パッケージ公開 API の整理
  - strategy, research, backtest パッケージの __init__ で主要関数/クラスをエクスポート。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Notes / Implementation decisions
- ルックアヘッドバイアス防止のため、すべての戦略 / 研究用関数は target_date 時点（および以前のデータ）に限定してデータ参照する設計です。
- 外部解析ライブラリへの依存を避け、DuckDB と標準ライブラリで実装することで軽量かつ配布性の高い設計としています。
- DB 書き込み操作は日付単位の置換（DELETE + bulk INSERT）を行い、トランザクションで原子性を保証しています。失敗時は ROLLBACK を試み、失敗ログを出力します。
- 一部ユーティリティ（zscore_normalize 等）は kabusys.data.stats に実装されていることを前提としています。

今後の予定（想定）
- PBR・配当利回りなどバリュー指標の追加。
- トレーリングストップや時間決済など、SELL 条件の拡張（現在はコメントで未実装と明記）。
- ポジションの部分利確 / 部分損切り、より柔軟なサイジングロジックの導入。
- 単体テスト・統合テストの追加と自動化（現在はコード上に挙動の説明とログが中心）。

---- 

この CHANGELOG はコードから推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は適宜差し替えてください。