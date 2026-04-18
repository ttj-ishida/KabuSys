# Changelog

すべての変更は「Keep a Changelog」規約に準拠しています。  
語彙: Added = 新規追加、Changed = 変更、Fixed = 修正、Deprecated = 廃止、Removed = 削除、Security = セキュリティ対応。

## [0.1.0] - 2026-04-18
初回リリース

### Added
- コアアプリケーション初期実装を追加。
  - パッケージ名: kabusys、バージョン: 0.1.0
- 実行・監視の起動スクリプトを追加。
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI ロジック（スレッド実行、停止フラグ監視、PID ファイル管理）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と分離（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory によるブローカークライアント生成をサポート（paper/live に応じた実装を想定）。
    - 初期 RiskManager コンフィグのデフォルト値を用意（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB を統一）。
- 環境設定・検証ツールを追加。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期生成 / 更新する機能。
    - 複数の設定項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML がない場合は YAML 検証をスキップして警告を出力。
- 環境変数・設定管理モジュールを追加。
  - src/kabusys/config.py
    - .env / .env.local の自動ロード（プロジェクトルートが検出できる場合、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサは export プレフィックス、クォート、インラインコメント等に対応。
    - 各種プロパティ（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, 閾値等）を提供。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- ロギング・プロセスユーティリティを追加。
  - src/kabusys/utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / app_name を解決してハンドラを構成。ログディレクトリ作成失敗時はコンソール出力のみで継続。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度設定（Windows / POSIX を抽象化）、および CPU affinity 設定ユーティリティ。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足等は警告でスキップ。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ計算）。
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates（スコア降順で上位 N を選択）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化配分、全スコアが 0 の場合は等重でフォールバック）
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（セクター別集中制限、"unknown" セクターは上限対象外）
    - calc_regime_multiplier（market_regime による投下資金乗数: bull=1.0, neutral=0.7, bear=0.3、未知レジームはフォールバック 1.0）
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes（risk_based / equal / score の配分方式をサポート）
    - lot_size（単元株丸め）、stop_loss_pct に基づくリスクベース算出、per-position / aggregate cap、cost_buffer を考慮したスケーリングと再配分ロジックを実装
- Paper Trading の検証レポートツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite を解析し、稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力。
    - デフォルトの Pass/Fail 基準を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - 日付範囲フィルタ (--from / --to) をサポート。
- データ分析・リサーチ用モジュール（ファクター計算）を追加（実装の一部）。
  - src/kabusys/research/factor_research.py
    - モメンタム、移動平均乖離、ATR、流動性等の計算を想定した関数群（DuckDB 接続前提）。注: 実装は途中ファイル末尾で継続予定。
- パッケージ初期化ファイルを追加。
  - src/kabusys/__init__.py — __version__ = "0.1.0"

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 実装上の挙動
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われるため、CWD に依存せずパッケージ配布後も安定して動作する。
- .env の自動ロードは OS 環境変数を上書きしない（.env.local は override=True で読み込まれるが、protected セットにより OS 環境変数は保持される）。
- run_monitoring のポーリング間隔:
  - デフォルト 60 秒。MONITOR_POLL_INTERVAL に不正な値（0 以下や非整数）が設定された場合は警告を出してデフォルトにフォールバックする。
- run_execution / run_monitoring は起動時に set_process_priority("high") を呼び出して可能な範囲でプロセス優先度を上げる（権限不足などは警告でスキップ）。
- Logging: ハンドラは既存のルートハンドラをクリアしてから設定するため、二重ログ記録を防ぐ。
- Portfolio / Position sizing:
  - lot_size（単元）で丸め処理を行い、aggregate cap を超えた場合はスケールダウンして残差を lot 単位で再配分するアルゴリズムを実装。
  - price が欠損（0 または None）の場合は該当銘柄をスキップする挙動。
- Paper Trading の検証レポートはテーブルが存在しない場合でも例外を吸収して空レポート（N/A 表示）を返すように耐性を持たせている。

### Known limitations / TODO
- research/factor_research.py はファイル末尾で途中（start_da ...）になっており、完全実装が必要。
- position_sizing の価格欠損時の扱いについて注記（price が欠損するとエクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格を導入することを検討）。
- BrokerClientFactory / ExecutionEngine 等の具体的なブローカー実装は外部依存（Mock / 実ブローカー実装が必要）。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）や YAML の詳細検証ルールは今後整備予定。

--- 

今後のリリースでは以下を予定しています（例）:
- factor_research の完成、データパイプラインとの統合
- テストカバレッジ拡張と CI 設定
- ExecutionEngine の詳細なフェイルセーフ・リカバリ機構の強化
- モニタリングアラート（LINE 通知等）の統合と運用監視強化