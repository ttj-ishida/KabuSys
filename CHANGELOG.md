CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is formatted for
human readers.

v0.1.0 — 2026-04-24
------------------

Added
- 初期公開: KabuSys バージョン 0.1.0 をリリース。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番データと分離。  
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）をサポート。  
    - BrokerClientFactory 経由で本番/モックブローカーの切り替えを行い、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。  
    - Monitoring は環境にかかわらず本番の sqlite_path を使用することを明示。停止フラグ検知でループを終了。
- 設定管理
  - config.py: 環境変数 / .env の自動ロード機能を実装（ルート検出は .git / pyproject.toml 基準）。  
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。  
    - 複数のユーティリティプロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, 各種しきい値等）。  
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性チェック）。
- 設定ユーティリティ / CLI
  - config_setup: .env 作成・更新の対話式ウィザードを追加。セクション毎に説明を表示し、既存値の読み込み・保存をサポート。
  - validate_config: 起動前検証 CLI を追加。  
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証を行う。  
    - --strict オプションで警告を FAIL 扱い（exit 1）。
- ロギング / 実行環境ユーティリティ
  - utils/logging_setup: ルートロガーの一元設定機能を追加。  
    - stdout 出力用 StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）を設定。ログディレクトリ自動作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。  
    - ログレベル解決順: 関数引数 > LOG_LEVEL 環境変数 > "INFO"。
  - utils/process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを追加。  
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応環境時は警告を出力して安全にフォールバック。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額重み (calc_equal_weights)、スコア重み (calc_score_weights) を実装。スコア全てが 0 の場合のフォールバックと警告を含む。
  - portfolio.risk_adjustment: セクター集中防止 (apply_sector_cap) とレジーム乗数 (calc_regime_multiplier) を実装。未知レジーム時のフォールバック挙動を定義。
  - portfolio.position_sizing: 発注株数算出ロジック (calc_position_sizes) を実装。  
    - risk_based / equal / score の配分方式をサポート。単元株（lot_size）丸め、per-position / aggregate 上限、コストバッファ考慮のスケーリング・端数処理を行う。
  - package エクスポートを整理（__all__ に主要関数を追加）。
- ツール
  - tools/paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。  
    - system_status, trade_logs, risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出し、閾値に基づく PASS/FAIL を出力。  
    - 閾値や日付フィルタ（--from/--to）をサポート。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB を指定可能。
- データ解析（研究用）
  - research/factor_research: ファクター計算モジュールの骨格を追加（モメンタム等の算出方針・定数を定義、calc_momentum の実装開始）。

Changed
- ログ出力の標準出力先を stderr から stdout に変更（logging_setup）。cron やスケジューラでのリダイレクト運用を考慮。
- .env パーサーの動作を強化（config._parse_env_line）：  
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント取り扱いの改善、クォートなしでの '#' コメント判定の細かい扱いを実装。
- run_monitoring: MONITOR_POLL_INTERVAL のパースおよび不正値時のフォールバック挙動を明確化（0 以下や非整数はデフォルト 60 秒にフォールバックして警告）。
- process_priority: Windows / POSIX の定数参照を getattr によるフォールバックで安全化。対応外 OS では警告してスキップ。

Fixed
- 例外や権限不足でプロセス優先度設定が失敗した場合にスキップして継続するようハンドリングを追加（utils/process_priority）。
- ログディレクトリ作成失敗時にプログラムが致命的にならないよう、ファイルハンドラ作成をスキップしてコンソールログのみで継続する挙動を logging_setup に実装。

Notes / Behavior
- 監視（run_monitoring）は明示的に本番 sqlite_path を使用する設計（環境に依存せず監視データを本番 DB に記録する想定）。
- Execution は paper_trading モード時に paper DB を使うことで、本番 DB と完全分離する設計。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされるため、配布後やパッケージ化時でも安全に動作する。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 今回のリリースは主にコア機能と運用ツールの整備を行った初期実装です。研究用モジュール・ファクター計算は継続して実装を進める予定です。

Unreleased
----------
- （今後の予定）factor_research の完全実装、テスト追加、さらに詳細な運用ドキュメント・監視アラートの強化などを予定しています。

ライセンス等の注意
- .env ファイルは秘匿情報を含むため絶対にリポジトリへコミットしないでください（config_setup のヘッダにも注意喚起あり）。
- 本番環境での設定変更は慎重に行ってください（validate_config は本番 guard を含む警告を出力します）。