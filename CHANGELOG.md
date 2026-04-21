# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
バージョンは package 内の __version__ を基にしています。

## [0.1.0] - 2026-04-21

### Added
- 初回リリース。KabuSys の基礎機能を多数追加。
- 環境設定・管理
  - Settings クラス（src/kabusys/config.py）を導入。環境変数経由で各種設定（J-Quants / kabuAPI / DB パス / 環境種別 / ログレベル等）を取得可能。
  - .env 自動読み込み機能を搭載:
    - プロジェクトルート（.git または pyproject.toml）を基準に .env, .env.local を読み込み。
    - OS 環境変数を保護する仕組み（上書き禁止）を導入。
    - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースの強化: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - Settings による環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE など）。
  - settings 単一インスタンスをエクスポート。

- 設定関連 CLI
  - 対話式ウィザード (src/kabusys/config_setup.py)
    - python -m kabusys.config_setup で .env の初期作成・更新を対話的に実行可能。
    - シークレット入力表示マスク、選択肢、デフォルト値、保存確認を実装。
  - 設定検証ツール (src/kabusys/validate_config.py)
    - python -m kabusys.validate_config で必須環境変数、DB パス、YAML 設定ファイル等の存在や値を検証。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML が未インストールの場合は YAML 内容検証をスキップし警告する。

- ログ・プロセス管理ユーティリティ
  - ログ設定ユーティリティ (src/kabusys/utils/logging_setup.py)
    - StreamHandler を stdout に設定（cron/TaskScheduler との相性考慮）。
    - TimedRotatingFileHandler による日次ローテーション（デフォルト logs/ 以下、30 日分保持）。
    - 環境変数/引数からログレベル・ログディレクトリを解決。
    - 既存ハンドラのクリーンアップを実装（多重設定防止）。
  - プロセス優先度・CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
    - Windows / POSIX の差分吸収。優先度 (high/normal/low) と CPU affinity 固定機能を提供。
    - 権限不足や未対応環境を許容し、失敗時は警告を出してスキップ。

- 実行エンジン・監視起動スクリプト
  - 実行スクリプト (src/kabusys/run_execution.py)
    - ExecutionEngine 起動ラッパー。PID ファイル管理、停止フラグ（data/stop_requested.flag）監視。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。BrokerClientFactory により paper/live を切り替え。
    - init_monitoring_db を呼び、監視テーブルの存在を保証（冪等）。
    - スレッドで ExecutionEngine を実行し、停止フラグ検知で安全に停止処理を行う。
  - 監視スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用（監視用に統一）。
    - 停止フラグ・KeyboardInterrupt による安全終了、check_once() 内例外はログに記録して次回ループへ継続。

- 監視 DB 初期化（参照）
  - init_monitoring_db を各実行パスで呼ぶことで監視テーブルの存在を保証（冪等処理）。

- ポートフォリオ構築関連（純粋関数）
  - ポートフォリオ候補選定と重み計算 (src/kabusys/portfolio/portfolio_builder.py)
    - select_candidates: スコア降順・タイブレークで signal_rank を使用。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合は等金額にフォールバック。
  - リスク調整 (src/kabusys/portfolio/risk_adjustment.py)
    - apply_sector_cap: セクター集中上限（max_sector_pct）のチェックと候補除外。売却予定銘柄をエクスポージャー計算から除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルトフォールバック含む）。
  - ポジションサイズ算出 (src/kabusys/portfolio/position_sizing.py)
    - risk_based / equal / score の割当方法を実装。
    - 単元株（lot_size）丸め、per-stock と aggregate の上限適用、コストバッファによる保守的見積り、スケーリング時の残差処理を実装。
  - モジュールエクスポート（src/kabusys/portfolio/__init__.py）。

- Paper Trading 検証レポートツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を参照してシステム稼働率、注文成功率、送信率、レジリエンシ指標、レイテンシ（avg/max/P95）を計算・印字。
    - デフォルト閾値を定義（稼働率 99% / 成功率 90% / 送信率 95% / P95 200 ms）。
    - コマンドライン引数 --from / --to / --db をサポート。

- リサーチ（ファクター計算）基盤
  - research/factor_research.py（モメンタム等のファクター計算、DuckDB 接続を想定）を追加（関数設計と定数を含む、calc_momentum 等を実装予定）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Notes / Implementation details
- stop/kill フラグや PID ファイルを用いた外部制御を実装しており、運用時のプロセス管理を考慮。
- duckdb と sqlite3 を併用：分析用は DuckDB、監視・トレードログは SQLite。
- ロギングはコンソール出力を標準としつつファイルローテーションも行うため、デバッグや本番監視の両方に対応。
- 一部の処理で外部依存（psutil, duckdb, PyYAML 等）を必要とするが、存在しない場合は graceful にフォールバック（警告）する実装になっている。

---

将来的なリリースでは、factor_research の完全実装、ExecutionEngine/EngineConfig の詳細、BrokerClient の具体的実装、テストカバレッジ拡張、設定とシークレット管理の改善などを予定しています。