CHANGELOG
=========

すべての注目すべき変更を記載します。本ドキュメントは "Keep a Changelog" の形式に準拠しています。

0.1.0 — 2026-04-17
------------------

Added
- 初期リリース。本リポジトリの核となる機能群を追加。
- 環境/設定管理
  - kabusys.config: .env 自動読み込み機能（プロジェクトルートの .env / .env.local）を実装。プロジェクトルートは .git または pyproject.toml により検出。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - Settings クラス: 各種環境変数（J-Quants・kabu API・DB パス・監視閾値・実行環境など）をプロパティとして提供し、値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を行う。
  - kabusys.config_setup: 対話式ウィザードで .env を初期作成/更新する CLI を追加（選択肢、シークレット扱い、デフォルト値などをサポート）。
  - kabusys.validate_config: 起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL、DB パス、config/*.yaml の存在とパース検証（PyYAML がない場合は警告）などを検証。--strict オプションで警告を失敗扱いにできる。

- 実行/監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を high に設定（utils.process_priority 経由）。
    - paper_trading 環境時は専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離。MockBrokerClient の使用を想定したブローカーファクトリ連携。
    - 停止用フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポート。バックグラウンドスレッドで engine.run_session を実行し、停止フラグ検知で安全に停止。
    - RiskManager の初期設定例（max_position_pct、max_utilization、rate_limit_per_sec 等）を組み込み、initial_portfolio_value は broker.get_available_cash() を参照。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視データの一元化）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、例外時はログを出して次ポーリングに継続。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - kabusys.portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選別（タイブレークに signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。全スコアが 0 の場合は等金額にフォールバックして警告。
  - kabusys.portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック。既存保有比率が max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームは 1.0 にフォールバックして警告）。
  - kabusys.portfolio.position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算を実装。
      - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate 上限（available_cash）を適用。
      - cost_buffer を考慮した保守的見積り、aggregate cap 超過時のスケーリング（小数端数の再配分アルゴリズム）を実装。
      - 価格欠損時のスキップとログ出力。

- 研究・ファクター計算
  - kabusys.research.factor_research:
    - calc_momentum: DuckDB の prices_daily を用いて 1m/3m/6m リターンと 200 日移動平均乖離率を計算。必要行数不足の場合は None を返す設計。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。true_range の NULL 伝播を制御して精度を担保。
    - DuckDB 接続を受け、SQL + Python で実行。外部 API に依存しない設計。

- ユーティリティ
  - kabusys.utils.process_priority:
    - set_process_priority(level): Windows/Linux/macOS の差分を吸収し、カレントプロセスの優先度を設定。権限不足や未対応 OS の場合は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にピンニングするユーティリティ（利用環境によりスキップ可能）。不正な引数で ValueError を送出。

- ツール
  - kabusys.tools.paper_verification_report:
    - Paper Trading 用検証レポート生成スクリプトを追加。期間指定（--from/--to）や DB 指定（--db）に対応。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、閾値（稼働率 >= 99%、注文成功率 >= 90% 等）に基づく PASS/FAIL 判定を出力。
    - P95 計算、欠損データのハンドリング、SQL クエリのフォールバックを含む堅牢な実装。

Changed
- N/A（初期リリース）

Fixed
- N/A（初期リリース）

Deprecated
- N/A（初期リリース）

Removed
- N/A（初期リリース）

Security
- N/A（初期リリース）

Notes / 注意事項
- paper_trading 環境では DB を完全分離（デフォルト data/paper_trading.db）。本番 DB を上書きしないよう注意してください。
- .env ファイルは機密情報（API トークン等）を含むため、絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- process priority / CPU affinity の設定は権限により失敗する場合があり、その場合は警告ログを出してスキップします。
- run_monitoring は監視用 DB に本番 sqlite_path を常に使用します。テスト目的で監視を分離したい場合は適切にパスを差し替えてください。
- レジーム乗数・セクター上限・リスクパラメータ等はコード内デフォルトを提供していますが、実運用では config ファイルや環境変数での調整を推奨します。

リリースノートはコードから推測して作成しています。実際の仕様や運用ルールと差異がある場合は適宜修正してください。