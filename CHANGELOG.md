CHANGELOG
=========

このファイルは Keep a Changelog の様式に準拠して作成されています。  
以下は、提供されたコードベースの内容から推測して作成した変更履歴です（記載は実装内容に基づく推測です）。

フォーマット
-----------
各リリースは日付付きで記載します。セクションは Added / Changed / Fixed / Deprecated / Removed / Security を使用します。

Unreleased
----------
（なし）

0.1.0 - 2026-04-18
------------------

Added
- 基本的な CLI / ランタイムスクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV に応じて本番 / ペーパートレードを切り替え、専用の SQLite（ペーパートレード時）と DuckDB を使用して実行環境を構築します。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
- 環境設定関連 CLI を追加
  - config_setup.py: 対話式ウィザードで .env ファイルの初期作成 / 更新を支援。秘密値はマスク表示、デフォルト・選択肢の指定、.env の書き出し機能を提供。
  - validate_config.py: .env や config/*.yaml の事前検証用 CLI。必須環境変数・パスの存在チェックや、YAML パーサ利用時は YAML ファイルのパース検証を行う。--strict オプションで警告を失敗扱いにできる。
- 設定管理モジュールを追加（config.py）
  - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）。.env と .env.local の読み込み順や OS 環境変数の保護を実装。
  - 環境値のパース（クォート対応、export プレフィックス、インラインコメント取り扱い等）を実装。
  - Settings クラスを提供し、各種設定値（DB パス、KABUSYS_ENV, PAPER_FILL_MODE, PID ファイルパス、監視閾値等）をプロパティとして取得可能に。
- ペーパートレード支援ツールを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite の集計レポートを生成する CLI。稼働率／注文成功率／送信率／レイテンシ（P95）などを判定し PASS/FAIL で出力。日付範囲・DB パスの指定が可能。
- ポートフォリオ関連モジュールを追加（pure function）
  - portfolio/portfolio_builder.py: 候補選定・等配分・スコア加重配分関数（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier（未知レジームはフォールバック）。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score の配分方式）、単元（lot_size）丸め、aggregate スケーリング等を実装。
- リサーチ（ファクター計算）
  - research/factor_research.py: DuckDB 上の prices_daily 等を用いてモメンタム／ボラティリティ等のファクターを計算する関数群（calc_momentum, calc_volatility 等）。200日移動平均、ATR、出来高等を算出。
- ユーティリティ
  - utils/process_priority.py: Windows / POSIX の差分を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS）と CPU affinity を設定する関数 set_process_priority / set_cpu_affinity。権限不足や未サポート環境で安全にスキップする実装。
- パッケージメタ
  - __init__.py に __version__ = "0.1.0" を追加。

Changed
- run_execution / run_monitoring の起動時にプロセス優先度を "high" に設定するように（最初に実行）して、実行中の優先度を明示的に向上させる。
- run_execution: Paper Trading モード（KABUSYS_ENV=paper_trading）は専用の paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離するように。
- run_monitoring: Monitoring は環境にかかわらず本番 sqlite_path を使用する（監視データは本番 DB に格納する想定）。
- .env 読み込み順を OS 環境 > .env.local（override）> .env（デフォルト）とし、OS 環境変数は保護（上書き禁止）される仕様を採用。
- .env パーシングの強化: シングル／ダブルクォートの値とバックスラッシュエスケープ、export KEY=val 形式、インラインコメントの扱いなどに対応。
- validate_config: PyYAML がインストールされていない場合は YAML 検証をスキップして警告を出す。KABUSYS_ENV=live の場合に本番向けの追加警告（LINE トークン未設定 / KILL_FLAG_CLEAR_ON_START の危険性等）を出力するように。
- paper_verification_report: P95（P95レイテンシ）の計算を追加。データが無い場合に N/A を表示する耐性を追加。

Fixed
- 環境変数の不正値に対する耐性を追加
  - MONITOR_POLL_INTERVAL の不正（非数や 0 以下）はログに警告を出しデフォルト（60 秒）にフォールバックするように（run_monitoring）。
  - Settings.paper_fill_mode の不正値検出時に明確な ValueError を送出するように。
  - Settings.env / log_level の不正値時に ValueError を送出するチェックを実装。
- calc_score_weights: 全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックして警告を出すように（ゼロ除算回避）。
- process_priority と CPU affinity の設定で権限不足や未サポート API 例外をキャッチして警告を出し、プロセスを継続できるように改善。
- run_monitoring のポーリングループで check_once() の例外を捕捉し、例外発生時もループを継続して次のポーリングを行うようにして安定化（例外時はスタックトレースをログ出力）。
- run_execution のスレッド制御で停止フラグ検知時に Engine.stop() を呼んで安全に停止する処理を追加。起動前に停止フラグが既に立っている場合は起動をスキップする。

Notes / Behaviour details（実装から推測）
- 停止フラグ / PID ファイル
  - プロジェクト内 data/ 以下に stop_requested.flag や execution.pid などのファイルを置いて、外部からプロセス停止要求や PID 管理を行う設計になっている。
  - run_monitoring/run_execution はこのファイルを監視して graceful shutdown を行う。
- DB 接続
  - run_* スクリプトは SQLite（監視・ペーパー）と DuckDB（分析）を併用する設計。起動時に monitoring 用テーブルの初期化（init_monitoring_db）を行う（冪等）。
- ポジションサイズ決定
  - position_sizing は lot_size による丸め、1 銘柄上限（max_position_pct）、資金総枠（max_utilization/available_cash）に基づくスケーリングを実装。cost_buffer を用いて手数料・スリッページを保守的に見積もる。
- セクター制限
  - apply_sector_cap は既存保有のセクター暴露を計算し、上限を超えるセクターの新規候補を除外する。コードが sector_map にない場合は "unknown" として扱い、上限判定の対象外（除外しない）にする。

Deprecated
- （なし）

Removed
- （なし）

Security
- 設定ウィザードおよび .env の取り扱いに関する注意点を README 等で明示することを推奨（.env は決して git にコミットしない旨の文言が .env テンプレート内に含まれている）。

Acknowledgements / 今後の改善点（推奨）
- stock 毎の lot_size を外部マスタから取得できるよう拡張する（現状はグローバル lot_size）。
- position_sizing の price 欠損時のフォールバック（前日終値や取得原価）を実装して評価の過少見積りを防ぐ TODO コメントあり。
- monitor/checker ロジックのユニットテストと e2e テストを整備して運用安定性を高める。
- validate_config の YAML 検証を CI で有効化し、config/*.yaml の正当性を自動検出する。

--- 
この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴やリリース手順に合わせて内容・日付を調整してください。