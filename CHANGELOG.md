CHANGELOG
=========

すべての重要な変更点をここに記録します。本ファイルは "Keep a Changelog" のフォーマットに準拠しています。

フォーマット:
- Added: 新機能
- Changed: 変更点（互換性のある変更）
- Deprecated: 非推奨
- Removed: 削除
- Fixed: バグ修正
- Security: セキュリティ修正

[Unreleased]
------------

（現在未リリースの変更はここに記載します）

0.1.0 - 2026-04-18
-----------------

初回リリース。KabuSys の基本機能群（設定管理、起動スクリプト、実行・監視系、ポートフォリオ構築ユーティリティ、ツール類、ユーティリティ関数）を収録します。

Added
- パッケージ全体
  - 初期バージョンを追加（__version__ = "0.1.0"）。
  - モジュール構成: data/、strategy/、execution/、monitoring/ などを想定したエクスポートを用意。

- 設定管理
  - kabusys.config
    - .env の自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - 高度な .env パーサ実装:
      - export 前置、シングル/ダブルクォート対応、バックスラッシュエスケープ、インラインコメントの扱い。
      - override / protected（OS 環境変数保護）オプション付きのファイル読み込み。
    - Settings クラスを提供し、環境変数経由の設定値をプロパティとして参照可能に。
    - 各種設定値（DB パス、KABUSYS_ENV、ログレベル、Paper Trading 用設定等）と妥当性チェックを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- 起動・検証 CLI
  - kabusys.config_setup
    - 対話式ウィザードで .env を生成/更新する CLI。
    - デフォルト値・選択肢・シークレット入力・既存 .env の読み込みをサポート。
  - kabusys.validate_config
    - .env および config/*.yaml の事前検証ツール。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML のパース検証（PyYAML が存在する場合）、本番環境向けガードを実装。
    - --strict オプションで警告を失敗として扱うモードを提供。

- 実行・監視ランチャー
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離して MockBrokerClient を利用する設計（BrokerClientFactory に基づく）。
    - プロセス優先度を high に設定して実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理（data/execution.pid）により外部からの停止制御を可能に。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の組み立てを行う。RiskManager のデフォルト設定をコード内で定義（max_position_pct 等）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視用 DB は常に本番想定）。
    - 停止フラグ（data/stop_requested.flag）で安全にループを終了。

- データベース / 初期化
  - 監視テーブルの初期化を起動時に行う init_monitoring_db 呼び出し（冪等性を想定）を両スクリプトで実施。
  - DuckDB 接続（duckdb パスのデフォルト）を起動時に開く。

- ログ・プロセス管理ユーティリティ
  - kabusys.utils.logging_setup
    - 統一的なログ設定 helper を提供。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフォールバックを実装。
    - 環境変数 LOG_LEVEL / LOG_DIR と引数優先のレベル解決。
  - kabusys.utils.process_priority
    - Windows / POSIX を吸収するプロセス優先度設定。
    - set_process_priority(level)：「high」「normal」「low」をサポート（psutil を利用）。AccessDenied 等は警告を出して継続。
    - set_cpu_affinity(cpu_count)：最初の N コアにプロセスをピン止め（未指定は何もしない）。例外時は警告を出して継続。

- ポートフォリオ構築ロジック（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates（スコア降順ソート、タイブレークルールあり）
    - calc_equal_weights（等分配）
    - calc_score_weights（スコア正規化、全スコアが 0 の場合は等金額にフォールバック）
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap（セクター集中上限チェック。既存保有時価を考慮し、上限を超えたセクターの新規候補を除外）
    - calc_regime_multiplier（市場レジームに応じた資金乗数: bull/neutral/bear をサポート、未知値はログ出力して 1.0 を返す）
  - kabusys.portfolio.position_sizing
    - calc_position_sizes：allocation_method（"risk_based" / "equal" / "score"）に従い、ロット丸め（lot_size）や per-stock 上限、aggregate cap（available_cash でスケーリング）を実装。
    - cost_buffer を用いた保守的なコスト見積りと、端数処理（残差に基づく追加配分ロジック）を含む。

- 研究・ファクター計算
  - kabusys.research.factor_research
    - DuckDB を利用したモメンタム、MA、ATR、出来高等の指標計算の方針と初期実装。関数 calc_momentum の構成・定数を定義（ただし実装が途中の箇所あり）。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading 検証レポート生成 CLI。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を SQLite のログテーブルから集計し判定（PASS/FAIL）を出力。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH（または data/paper_trading.db）。

Changed
- （初回リリースのため該当なし）

Fixed
- ロギングの堅牢化:
  - ログディレクトリ作成失敗やファイルハンドラ生成失敗時にコンソール出力のみで安全に続行するよう改善。
- 環境値の堅牢性:
  - MONITOR_POLL_INTERVAL の不正値に対するフォールバック実装（0 以下や文字列等で ValueError を避け、警告を出して既定値を使用）。
- DB 初期化の冪等性を想定した呼び出し（起動時に監視テーブルの存在を保証する目的の init_monitoring_db を両スクリプトで実行）。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 機密情報は .env に格納する設計。config_setup の出力コメントに「.env を絶対に Git にコミットしないこと」を明記。

Notes / Known issues
- 一部未実装 / TODO:
  - portfolio.position_sizing: 将来的に銘柄別 lot_size をサポートする旨の TODO コメントあり。
  - risk_adjustment.apply_sector_cap: price が欠損 (0.0) の場合にエクスポージャーが過少推定される可能性。フォールバック価格利用は未実装。
  - research.factor_research.calc_momentum の実装が途中（ファイル末尾が途中で切れている）。
- 監視系の仕様:
  - run_monitoring は監視用でも本番 sqlite_path を参照する設計（環境によらず本番監視 DB を利用する点は意図的）。
- 実行系の仕様:
  - paper_trading モードは paper_sqlite_path に記録し本番 DB と分離するが、設定ミスにより同じパスを指定すると分離が失効する可能性あり（ドキュメント参照推奨）。
- 外部依存:
  - process_priority と CPU affinity の操作には psutil が必要。権限不足や未対応環境では警告を出してスキップする。

Acknowledgements
- 本 CHANGELOG は提供されたソースコードから機能と振る舞いを推測して作成しています。詳細な意図や実装方針はリポジトリのドキュメント（README、設計書）や実装者にご確認ください。