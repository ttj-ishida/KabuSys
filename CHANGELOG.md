# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: この CHANGELOG はリポジトリ内のコードから推測して自動作成しています。実際のコミット履歴とは異なる可能性があります。

## [Unreleased]

## [0.1.0] - 2026-04-24
初回リリース

### Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py にて定義）
- 環境設定・読み込み
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）
  - .env パーサーを強化:
    - コメント / 空行 / export プレフィックス対応
    - シングル/ダブルクォート中のバックスラッシュエスケープ処理対応
    - クォートなしのインラインコメント判定（直前が空白/タブの場合のみ）
  - OS 環境変数の保護（自動ロード時の上書き制御）
  - Settings クラスを追加して環境変数をプロパティ経由で型変換・検証して提供（例: duckdb/sqlite パス、PAPER_FILL_MODE 検証、KABUSYS_ENV/LOG_LEVEL のバリデーション等）
  - settings インスタンスをエクスポート

- 設定ウィザード CLI
  - config_setup.py を追加し、対話式ウィザードで .env を生成・更新する機能を提供
  - 複数の設定項目を定義（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DBパス、LINE設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）
  - 既存 .env 読み込み・マスク表示・保存確認を実装

- 設定検証 CLI
  - validate_config.py を追加
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML が存在する場合）などを実装
  - --strict オプションで警告も失敗扱いにできる

- ログ設定ユーティリティ
  - utils/logging_setup.py を追加
  - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーにセット
  - ログレベル・ログディレクトリ解決ロジック（引数 > 環境変数 > デフォルト）
  - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続

- プロセス優先度 / CPU affinity ユーティリティ
  - utils/process_priority.py を追加
  - set_process_priority(level) により Windows / POSIX を吸収した優先度設定を実装（"high"/"normal"/"low"）
  - set_cpu_affinity(cpu_count) により最初の N コアにプロセスを固定する機能を追加
  - 権限不足や未対応プラットフォームでは警告を出して安全にスキップ

- 実行（Execution）起動スクリプト
  - run_execution.py を追加
  - 起動時にプロセス優先度を high に設定
  - KABUSYS_ENV が paper_trading の場合、専用の paper DB を使用して本番 DB と分離（settings.paper_sqlite_path）
  - BrokerClientFactory によるブローカークライアント生成をサポート（paper/live に応じたクライアント切替）
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動
  - ExecutionEngine は別スレッドで run_session を実行し、プロジェクトルートの stop flag (data/stop_requested.flag) を検知して安全に停止
  - PID ファイル管理（data/execution.pid）に対応
  - RiskManager のデフォルト設定をコード上に定義（max_position_pct, max_utilization, rate_limit_per_sec 等）

- 監視（Monitoring）起動スクリプト
  - run_monitoring.py を追加
  - 起動時にプロセス優先度を high に設定
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトにフォールバック）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（monitoring 用 DB 初期化を実行）
  - stop flag (data/stop_requested.flag) の存在でループ終了、KeyboardInterrupt に対応
  - check_once() 呼び出しで例外発生時もループ継続（ログに例外を記録）

- 監視 DB 初期化
  - monitoring_db.init_monitoring_db 呼び出しを行い、監視テーブルの存在を保証（冪等）

- Portfolio モジュール
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順（タイブレークに signal_rank）で候補選定
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのエクスポージャー算出、上限超過セクターの候補除外、"unknown" セクターは除外しない）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は警告して 1.0 フォールバック）
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算
    - lot_size（単元）に基づく丸め、max_position_pct による per-stock 上限、available_cash による aggregate cap によるスケールダウンと端数処理（残余キャッシュで優先配分）
    - cost_buffer による保守的見積りをサポート

- 研究（Research）モジュール（部分実装）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（モメンタム、MA200、ATR、出来高系などの計算を行う目的記載、DuckDB 接続を受ける設計）
  - 定数（窓長）と calc_momentum 関数の開始実装（未完の箇所あり）

- ツール: Paper Trading 検証レポート
  - tools/paper_verification_report.py を追加
  - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシなど）を集計してレポート出力
  - Pass/Fail 判定閾値を定義（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200 ms）
  - コマンドライン引数 --from/--to/--db をサポート

### Changed
- なし（初回リリースのため変更履歴はありません）

### Fixed
- なし（初回リリースのため修正履歴はありません）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

補足:
- 多くの機能は DB（SQLite / DuckDB）や外部コンポーネント（kabuステーション / BrokerClient）に依存するため、実行には適切な環境変数設定および外部サービスの用意が必要です。config_setup と validate_config を利用して事前準備を行ってください。
- research/factor_research.py は一部実装が途中で切れていることがソースから推測されます（calc_momentum の実装が途中）。必要に応じて続きを実装してください。