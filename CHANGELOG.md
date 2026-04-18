CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

現在のバージョン
----------------
- 0.1.0 - 2026-04-18

Unreleased
----------
（なし）

0.1.0 - 2026-04-18
------------------

Added
- 初回リリース: KabuSys v0.1.0 を公開。
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- 設定管理
  - Settings クラス（src/kabusys/config.py）を追加。環境変数経由の設定取得、型変換、妥当性検査を提供。
  - 自動 .env ロード機能を実装（プロジェクトルート検出：.git / pyproject.toml を基準）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化に対応。
  - .env の対話式ウィザード（src/kabusys/config_setup.py）を追加。シークレット入力、デフォルト表示、.env 書き出し機能を提供。
  - 環境設定検証 CLI（src/kabusys/validate_config.py）を追加。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検査、DB パス・config/*.yaml の存在/パース確認、--strict モードをサポート。
- 実行 / 監視用スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を行う。
    - 停止フラグ（data/stop_requested.flag）の検知、pid ファイル管理、スレッドでの実行監視を実装。
  - 監視ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時は警告してデフォルトへフォールバック。
    - SystemMonitor を用いた単回チェック check_once のループ実行、停止フラグ検知、DB 接続（monitoring は環境にかかわらず本番 sqlite_path を使用）。
- データベース / 分析
  - DuckDB / SQLite の利用を想定した接続処理を各スクリプトで統一的に組み込み（duckdb, sqlite3 の利用）。
  - 監視テーブル初期化用の init_monitoring_db を参照して監視テーブルの冪等初期化を実施（run_execution/run_monitoring で呼び出し）。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、同点時 tie-break）、calc_equal_weights、calc_score_weights（スコア全て 0 の場合は等金額にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮して同一セクターの新規候補を除外）、calc_regime_multiplier（bull/neutral/bear に応じた乗数と未知レジームのフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：allocation_method（"risk_based"/"equal"/"score"）に対応。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer を考慮したスケールダウンと残余配分ロジックを実装。
- 研究用モジュール
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）の骨組みを追加。DuckDB 接続を受け取り momentum 等のファクターを計算する設計（モジュール内に定数と calc_momentum の仕様記述あり）。
- ツール
  - Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）を追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL 判定する CLI（--from/--to/--db オプション）。
    - 各指標の閾値（稼働率 99% 等）および P95 計算実装を含む。
- ユーティリティ
  - ロギングセットアップ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。既存ハンドラは上書きして二重出力を防止。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX(Linux, macOS 等) を吸収して set_process_priority("high"|"normal"|"low") を提供。set_cpu_affinity で最初の N コアへ固定する機能を実装。
  - ログやプロセス優先度設定は起動スクリプトから共通利用。
- ドキュメント的注記
  - 各モジュールに実装方針・注意点（例: apply_sector_cap の price 欠損に関する TODO、calc_regime_multiplier の説明など）を注記。

Changed
- 初回リリースのため "Changed" に該当する過去からの変更は無し。

Fixed / Robustness improvements
- .env のパーサ（src/kabusys/config.py）で以下に対応:
  - export KEY=val 形式、クォート有りの値（バックスラッシュエスケープ対応）、インラインコメントの扱い、クォート無し時のコメント判定ルールを実装し堅牢化。
  - 自動ロード時に既存 OS 環境変数を保護（protected set）して上書き制御を実現。
- validate_config:
  - PyYAML が未インストールでも検証をスキップし、ユーザーに警告する耐障害性を追加。
  - DB パスや config ファイルの親ディレクトリ非存在時に警告を出す。
- ロギング初期化 (logging_setup):
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時にフォールバックしてスタートできるように復旧処理を追加。
- run_monitoring:
  - MONITOR_POLL_INTERVAL の不正値に対する警告とデフォルトフォールバックの実装。
- process_priority:
  - 実行環境によりアクセス拒否や未実装例外が発生した場合に警告を出して安全にスキップするよう改良。

Security
- .env ウィザード（config_setup）ではシークレット項目をマスクして表示。
- README 相当の注意書きとして .env を絶対に Git にコミットしない旨を .env 書き出しヘッダに明記。
- Settings._require により必須環境変数が未設定の場合は起動前に例外で通知。

Notes / Implementation details
- Paper Trading と Live の DB 分離を明確に実装（Settings.paper_sqlite_path / is_paper フラグ、run_execution の分岐）。
- ExecutionEngine 側の RiskConfig 初期化で broker.get_available_cash() を利用するため、BrokerClientFactory 実装（モック含む）を前提としている。
- ポートフォリオ・サイジング・リスク調整関数群は純粋関数として設計され、DB 参照を行わずメモリ内計算のみを行う。

今後の予定（例）
- research.factor_research の完全実装（Momentum 等の SQL 実装完了）。
- 銘柄別 lot_size 対応（stocks マスタからの読み替え）。
- 更なるテストケースと CI ワークフローの追加。

付記
- 本 CHANGELOG は提示されたコードベースから実装内容を推測して作成しています。コードの追加・変更が別ブランチにある場合や、実行時の外部依存（ブローカー API 等）によっては挙動が変わる可能性があります。