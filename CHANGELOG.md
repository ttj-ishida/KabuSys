CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
（日付はコードベース解析時点の推測です）

Unreleased
----------

- なし（次バージョンへ移行予定の変更は現時点で検出されていません）。

[0.1.0] - 2026-04-25
--------------------

初回リリース（コードベースから推測した主な機能・改善点をまとめています）。

Added
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading モード時は専用の SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の実行・停止ロジック（停止フラグ file による制御）。
    - 実行プロセス用の PID ファイル管理（data/execution.pid）。
    - RiskManager のデフォルト設定（最大ポジション比率、利用率、レート制限、サーキットブレーカー等）を導入。
  - run_monitoring.py
    - SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明記。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止処理。
    - check_once() 実行時の例外を捕捉してログ出力しループ継続。

- 設定・ユーティリティ
  - config.py
    - 環境変数/.env の自動ロード機構を追加（プロジェクトルートの検出：.git または pyproject.toml を基準）。
    - .env パースの堅牢化（export プレフィックス対応、クォート内エスケープ、インラインコメント処理など）。
    - Settings クラスを導入し、アプリ設定（パス、閾値、モード判定、Paper Trading の fill モード検証等）をプロパティとして提供。
    - PAPER_FILL_MODE の検証（"instant" / "partial" / "never" / "reject"）。
    - KABUSYS_ENV / LOG_LEVEL 等の検証と便利なフラグ（is_live / is_paper / is_dev）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - デフォルト項目、シークレット入力、既存 .env の読み込み・表示、保存確認などのユーザーインタラクションを提供。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数・パス・config/*.yaml の存在とパース検証、KABUSYS_ENV による追加警告などを実行。
    - --strict オプションで警告も失敗（exit 1）として扱う。
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順、既存ハンドラの安全なクリーンアップを実施。
  - utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS を想定したフォールバック処理あり。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（score 降順、signal_rank によるタイブレーク）、等金額・スコア加重配分を実装。スコア全0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中の上限適用（apply_sector_cap）を実装。既存保有のセクター比率を計算し、上限超過セクターの新規候補を除外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。未知レジームは警告を出してフォールバック。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based", "equal", "score") に基づく株数決定ロジックを実装。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、コストバッファ、スケーリング、残余キャッシュによる端数配分ロジックを搭載。
    - price 欠損時のスキップやログ出力等の堅牢化。

- レポート / ツール
  - tools/paper_verification_report.py
    - Paper Trading 向け検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定（閾値はソース内に定義）。
    - コマンドライン引数で期間（--from / --to）や DB パス（--db）を指定可能。DB が存在しない場合のエラーメッセージを提供。

- リサーチ
  - research/factor_research.py
    - ファクター計算モジュールの骨格（モメンタム、MA、ATR、売買代金等の計算方針）を追加。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。
    - （注）ファイル末尾で calc_momentum の実装開始が見られるが、一部抜けがある（切れている）。

Changed
- ロギングの挙動統一
  - 全起動スクリプトは setup_logging を呼び出して統一的にログ設定を適用するようになった（標準出力 + ファイルローテート）。
- DB の取り扱い
  - 監視関連（monitoring）は環境にかかわらず本番 sqlite_path を使用する設計に明示的に変更。

Fixed / Improved
- .env パース精度向上
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等を正しく処理するよう改善。
- 停止・PID 管理
  - run_execution / run_monitoring に停止フラグファイル検知と安全なシャットダウン処理を追加。ExecutionEngine のスレッド停止処理や接続クローズを確実化。
- 例外耐性
  - monitor.check_once() などで発生した例外をキャッチしてログに残し、次のポーリングへ継続するようにして単発のエラーでプロセスが落ちないように改善。

Known issues / Notes
- research/factor_research.py は現在一部未完成（ファイル末尾で calc_momentum の実装が途中で終わっている）。完全実装は今後の作業が必要。
- position_sizing の価格欠損（price が 0.0 の場合）に関する注記があり、前日終値などフォールバック価格の実装が TODO として残っている。
- プロセス優先度・CPU affinity の設定は OS 権限・プラットフォーム依存で失敗することがある（警告でフォールバックする）。
- ログディレクトリの作成やファイルハンドラの初期化に失敗した場合はコンソール出力のみで継続する設計。

Environment / Configuration highlights
- 主要環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL, LOG_DIR
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - MONITOR_POLL_INTERVAL（監視ループの秒数、デフォルト: 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（自動 .env ロード無効化フラグ）
  - KILL_FLAG_CLEAR_ON_START（本番での取扱いに注意。default 0 推奨）

その他
- パッケージバージョンは __version__ = "0.1.0" に設定されています。
- 今後の改善候補として、ファクター計算の完全実装、価格フォールバック、各種設定の単体テスト追加、monitoring と execution の統合テスト整備が挙げられます。