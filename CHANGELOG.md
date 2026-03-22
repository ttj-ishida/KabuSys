CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルは、提供されたコードベースの内容から実装された機能・設計決定・既知の制約を推測して作成しています。

フォーマット:
- Unreleased: 今後の変更（この配布では空）
- 各リリースは日付付きで記載

Unreleased
----------
（なし）

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージ初期リリース（kabusys 0.1.0）。
- 全体構成
  - パッケージルートを定義（src/kabusys/__init__.py に __version__="0.1.0"）。
  - モジュール群: data, strategy, execution, monitoring（execution は空の初期化）。
- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート検出: __file__ を基点に .git または pyproject.toml を探索して自動的に .env/.env.local を読み込む。
  - .env パーサ: export プレフィックス、シングル／ダブルクォート内のエスケープ、インラインコメント処理、コメントや空行のスキップなどに対応。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の取得を型付きプロパティで行う。未設定の必須環境変数は例外を投げる。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- 研究（research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離（ma200_dev）。移動平均はウィンドウサイズで不足する場合は None を返す。
    - Volatility: 20日 ATR（atr_20）, 相対 ATR（atr_pct）, 20日平均売買代金（avg_turnover）, volume_ratio（当日出来高 / 20日平均）。
    - Value: 最新財務データ（raw_financials）から PER（株価/EPS）と ROE を計算。EPS が 0/欠損のときは PER を None に。
    - SQL + DuckDB ベースで実装（pandas 等の外部依存を使わない方針）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（デフォルト horizon=[1,5,21]、複数ホライズン同時取得）。
    - IC 計算 calc_ic（Spearman の ρ をランクで計算、サンプル不足時は None）。
    - ランク関数 rank（同順位は平均ランク、丸めで ties 検出を安定化）。
    - factor_summary：count/mean/std/min/max/median を算出。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - 研究環境で計算された raw ファクターを読み込み、ユニバースフィルタ（最低株価、20日平均売買代金）を適用。
  - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
  - features テーブルへ日付単位の置換（DELETE + bulk INSERT をトランザクションで実行し冪等性を確保）。
  - ユニバース基準: 最低株価 = 300 円、最低平均売買代金 = 5 億円。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
  - コンポーネント計算ロジック:
    - momentum: momentum_20, momentum_60, ma200_dev のシグモイド平均。
    - value: PER に基づくスコア（PER=20 -> 0.5、PER→0 -> 1.0、PER→∞ -> 0.0 の近似）。
    - volatility: atr_pct の Z スコアを反転してシグモイド変換（低ボラ = 高スコア）。
    - liquidity: volume_ratio をシグモイド変換。
    - news: ai_score をシグモイド変換、未登録は中立補完。
  - 最終スコア final_score は重み付き合算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザ指定 weights を受け、未知キーや不正値は無視、合計が 1.0 になるよう再スケール。
  - Bear レジーム判定: ai_scores の regime_score の平均が負で、かつ十分なサンプル（デフォルト 3 件）あれば Bear と判定し BUY を抑制。
  - BUY シグナルは閾値（デフォルト 0.60）以上を採用、SELL は保有ポジションに対するストップロス（-8%）またはスコア低下で判定。
  - SELL 判定時、価格欠損や positions / features の欠如に対するログ警告と安全なフォールバックを実装。
  - signals テーブルへ日付単位の置換（トランザクションで冪等）。
- バックテストフレームワーク（src/kabusys/backtest/*）
  - ポートフォリオシミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator: メモリ内で cash・positions・cost_basis を管理し、execute_orders でシグナルを約定（SELL 優先、SELL は全量クローズ、部分利確未対応）。
    - スリッページと手数料モデル: BUY は始値*(1+slippage), SELL は始値*(1-slippage)、手数料は約定金額×commission_rate。
    - commission の再計算で資金不足対応、平均取得単価の更新、TradeRecord の記録。
    - mark_to_market で終値評価の DailySnapshot を記録。終値欠損は 0 評価して警告ログ。
  - メトリクス（src/kabusys/backtest/metrics.py）
    - BacktestMetrics データクラス（CAGR, Sharpe, MaxDrawdown, Win rate, Payoff ratio, total trades）。
    - calc_metrics と内部計算関数（CAGR、シャープレシオ（252日基準で年次化）、最大ドローダウン、勝率、ペイオフ比）。
  - バックテストエンジン（src/kabusys/backtest/engine.py）
    - run_backtest: 本番 DuckDB から必要データをインメモリ DuckDB にコピーして日次シミュレーションを実行。
    - _build_backtest_conn: prices_daily, features, ai_scores, market_regime を日付範囲でコピー。market_calendar は全件コピー。コピー失敗は警告ログでスキップ。
    - 日次処理ループ:
      - 前日シグナルを当日の始値で約定
      - positions を DB に書き戻し（generate_signals の SELL 判定に必要）
      - 終値で時価評価・スナップショット記録
      - generate_signals を当日（trading_day）で実行して翌日発注リストを作成
      - 買い資金配分は max_position_pct と現金/保有比率を考慮して算出
    - DB 読み書きは日付単位の置換（DELETE + INSERT）で冪等性を確保。
- パッケージエクスポート（__all__）
  - backtest パッケージは run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics を公開。
  - strategy パッケージは build_features, generate_signals を公開。
  - research パッケージは calc_momentum/calc_volatility/calc_value/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank を公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （リリース現時点で明示的な修正履歴は無し。実装内で欠損やエッジケースに対する警告ログや保護を多数追加。）

Deprecated
- （なし）

Removed
- （なし）

Security
- 環境変数読み込み時に OS 環境変数を保護する仕組み（.env 読み込み時の protected set）を実装。デフォルトで既存の OS 環境変数が上書きされないよう制御。

Known issues / Notes（既知の制約・未実装）
- execution モジュールはパッケージに存在するが実装ファイルは空（発注 API 連携層は未実装）。
- signal_generator 側で想定しているエグジット条件の一部（トレーリングストップ、時間決済）は未実装。これらは positions テーブルに peak_price / entry_date 等が必要との注記あり。
- generate_signals の Bear 判定は regime_score のサンプル数に依存。サンプル不足時は誤判定を防ぐため Bear とみなさない。
- calc_forward_returns の日付スキャンは calendar 日数にバッファを掛ける設計だが、極端に欠落したデータや短い時系列では期待どおりの結果を返さない可能性がある。
- zscore_normalize 実装（kabusys.data.stats）は本 changelog 作成時点で参照されているが、ここではその詳細実装を明記していない。外部依存は最小限に抑えている設計方針。
- SQLite/DuckDB のパスは環境変数（DUCKDB_PATH/SQLITE_PATH）で指定可能。未設定時は data/ 以下にデフォルトを利用。
- 一部の SQL は DuckDB のウィンドウ関数等に依存しており、他の DB エンジンでそのまま動作する保証はない。

開発者向けメモ
- 設定の自動読み込みはパッケージ読み込み時に行われるため、ユニットテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを抑止すると良い。
- DB 書き込みは日付単位で DELETE → INSERT を実施するため、外部で同日時に並列更新があると競合する可能性あり。実運用での排他制御は要検討。
- ログ出力が各モジュールで充実しているため、デバッグや運用時の障害解析に役立つ。

ライセンス／著作権
- 本 CHANGELOG は提供されたコード内容の推測に基づき作成されています。実際のコミット履歴や作者の意図とは異なる場合があります。