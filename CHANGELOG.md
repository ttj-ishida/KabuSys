# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。初回リリース (v0.1.0) の内容をコードベースから推測してまとめています。

全体方針:
- 日付は本パッケージの現在バージョン（src/kabusys/__init__.py の __version__ = "0.1.0"）に対応する初回公開リリースとして記載しています。
- 各項目は実装ファイルやドキュメント文字列から推測した機能・挙動を簡潔にまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-19
### Added
- 基本機能・コアモジュールを追加（初回リリース）。
  - パッケージメタ情報: バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
- 起動スクリプト / 実行エントリを追加。
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離（MockBrokerClient を利用する想定）。
    - 停止制御: data/stop_requested.flag を監視。停止時は engine.stop() により安全に終了。
    - 実行時の PID ファイル (data/execution.pid) を利用。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを開始。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を使用する（監視用 DB 初期化を行う）。
    - 停止制御: data/stop_requested.flag を検出してループ終了。
- 設定・環境変数管理
  - src/kabusys/config.py
    - プロジェクトルートを .git / pyproject.toml から探索して自動で .env をロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
    - .env パーサーは export プレフィックス、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメントの扱いなどをサポート。既存 OS 環境変数は保護して上書きを制御。
    - Settings クラスを提供し、各種設定（J-Quants トークン、kabuAPI パスワード、DB パス、PAPER_FILL_MODE の検証、KABUSYS_ENV の検証、ログレベルやしきい値など）をプロパティとして取得可能。
- 設定支援 CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 等の項目を対話で設定し .env に保存可能。
- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env や config/*.yaml の存在・基本検証を行う CLI。
    - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML があれば）などを実施。
    - --strict オプションで警告も失敗扱いにできる。
- ロギングユーティリティ
  - src/kabusys/utils/logging_setup.py
    - setup_logging() を提供。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR 解決ロジックを実装。ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
- プロセス優先度・アフィニティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX に対応した優先度設定を行う（psutil を利用）。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定する機能を追加。権限不足や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築ユーティリティ
  - src/kabusys/portfolio/*
    - portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア全てが 0 の場合は等金額にフォールバックして警告を出す。
    - risk_adjustment.py: セクター集中制限を実施する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加（未知レジームは 1.0 でフォールバック）。
    - position_sizing.py: 株数決定ロジックを実装。allocation_method ("risk_based" / "equal" / "score") に対応、lot_size（単元株）で丸め、aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer（手数料・スリッページ見積り）等を考慮した安全なサイズ計算を実装。
- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - SQLite の paper trading DB から稼働率、注文成功率/送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポートを出力する CLI を追加。
    - 日付フィルタ（--from/--to）や DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。P95 計算や閾値による PASS/FAIL 判定（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms など）を実装。
- リサーチ・ファクター計算（骨格）
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム / MA / ATR / ボリューム等の定義と定数）。（実装の一部は継続中）
- DB 初期化呼び出し
  - 監視／実行起動時に監視テーブルを確実に作成する init_monitoring_db 呼び出しを行うことで冪等性を確保。

### Changed
- （初回リリースにつき適用なし）

### Fixed
- （初回リリースにつき適用なし）

### Security
- 環境変数の取り扱いに関する注意:
  - .env は絶対にリポジトリにコミットしない旨を config_setup.py が明記。
  - Settings._require() は必須 env 未設定時に ValueError を発生させ、起動前に設定漏れが検出できるようにしている。

### Notes / Operational guidance
- 停止フラグ:
  - data/stop_requested.flag を作ることで監視ループや実行エンジンを外部から安全に停止可能。
- Kill Switch:
  - 設定 KILL_FLAG_CLEAR_ON_START のデフォルトは 0（本番安全設定）。validate_config では本番（KABUSYS_ENV=live）でこの値が 1 の場合に警告を出す。
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテートで出力。ログディレクトリ作成に失敗してもコンソール出力は継続される。
- Paper Trading 分離:
  - paper_trading 環境では paper_sqlite_path を使い本番データと完全に分離する設計。

---

（注）この CHANGELOG は与えられたコードベースの内容および docstring/コメントから推測して作成しています。実際のリリースノートに使用する場合は必要に応じて詳細や日付、作者、マイナーな実装差分などを追記してください。