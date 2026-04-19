CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。  
バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
-------------------

Added
- 基本的な自動売買フレームワークを実装（初回リリース）。
  - パッケージ化: kabusys モジュールを提供（src/kabusys/__init__.py に version=0.1.0）。
- 起動スクリプト / ランタイム
  - run_execution.py: 実行エンジン起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - ExecutionEngine をスレッドで起動・監視し、data/stop_requested.flag による外部停止をサポート。
    - 実行中の PID を data/execution.pid に記録する仕組み（ExecutionEngine 側で pid_file を使用）。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: システム監視ポーリングループの起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path（デフォルト: data/monitoring.db）を参照して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py: .env の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
    - .env/.env.local の読み込み順序や、OS 環境変数保護（上書き禁止）の挙動を提供。
    - 各種設定プロパティを提供（J-Quants / kabuステーション / DB パス / paper_trading 切替 / 監視しきい値 / 環境フラグ等）。
    - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 必須項目・任意項目を案内し、.env ファイルへ書き込み。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在および YAML パース（PyYAML が利用可能な場合）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定する共通関数 setup_logging を提供。
    - LOG_DIR / LOG_LEVEL の環境変数や引数からの上書きをサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py:
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収する形でプロセス優先度（high/normal/low）を設定する set_process_priority を提供。
    - CPU affinity を設定する set_cpu_affinity を提供（psutil ベース、失敗時は警告ログを出す）。
- ポートフォリオ構成（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - セクター集中を抑制する apply_sector_cap（既存保有を考慮して候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - allocation_method ("risk_based", "equal", "score") に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、総投下資金（aggregate cap）に応じたスケーリングを行うロジックを実装。
    - cost_buffer を考慮した保守的見積もりと、余剰キャッシュによる再配分（fractional remainder に基づく lot 単位での追加）を実装。
- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨子を実装（モメンタム / MA / ATR / ボリューム等の定義、DuckDB を用いた計算を想定）。（注: 一部ファイル末尾で実装が未完の箇所あり）
- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率（filled/created）、送信率（sent/created）、P95 レイテンシ等を集計して PASS/FAIL を判定する閾値を設定（例: uptime >= 99%、fill_rate >= 90% 等）。
    - 日付フィルタ (--from / --to) と DB パス指定 (--db / 環境変数 PAPER_TRADING_SQLITE_PATH) をサポート。
- 監視データベース初期化
  - monitoring.monitoring_db.init_monitoring_db が run_* スクリプトから呼ばれ、監視用テーブルの存在を保証（冪等的初期化）。

Changed
- n/a（初回リリース）

Fixed
- n/a（初回リリース）

Security
- n/a

Deprecated
- n/a

Removed
- n/a

Breaking Changes
- なし（初回リリースのため後方互換性に関する変更は存在しません）。

Notes / 実装上の注意
- .env 自動ロードはデフォルトで有効だが、テスト環境等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能。
- run_monitoring は MONITOR_POLL_INTERVAL の値が不正（0 や文字列等）であればデフォルト 60 秒にフォールバックする。
- process_priority / set_cpu_affinity は psutil に依存し、権限不足や未サポート OS ではログ警告を出してスキップします。
- portfolio 等の関数群は純粋関数（副作用なし）として設計され、DB 参照は行いません。テスト容易性を重視。
- research/factor_research の一部関数はファイル末端で未完となっているため、ファクター計算の完全実装は今後の作業項目です。

作者
- KabuSys 開発チーム

---