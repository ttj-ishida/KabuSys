CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。  
日付はリポジトリ内のコードから推測し、初回リリースを 2026-04-24 としています。

Unreleased
----------

（現在なし）

[0.1.0] - 2026-04-24
--------------------

Added
- 初期リリース: KabuSys の主要コンポーネント群を追加。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 専用 SQLite（既定: data/paper_trading.db）に記録。停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。停止フラグを検知して終了。
  - 設定管理
    - config.py: Settings クラスを実装。環境変数の読み取り、値の検証（KABUSYS_ENV, LOG_LEVEL 等）、データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）、紙トレード設定（PAPER_FILL_MODE）などを提供。
    - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml を基準）を探索し .env/.env.local を自動読み込み。OS 環境変数を保護する仕組みを提供。自動読み込み無効化用: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新。シークレットマスク表示や選択肢サポート、生成時のテンプレート出力を提供。
    - validate_config.py: 設定検証 CLI を追加。必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリの存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML が利用可能な場合）。--strict オプションで警告を Fail 扱いにできる。
  - ポートフォリオ構築ライブラリ（純関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコア順）、等金額配分、スコア加重配分を実装。
    - portfolio/position_sizing.py: ポジションサイズ算出ロジックを実装（risk_based / equal / score の割当方式、単元株丸め、aggregate cap のスケーリング、手数料/スリッページ考慮）。
    - portfolio/risk_adjustment.py: セクター上限フィルタ（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。
    - portfolio/__init__.py で公開 API を整備。
  - ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout ストリームハンドラ + 日次ローテーションのファイルハンドラ（logs/<app_name>.log、30日保持）。LOG_DIR/LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度設定（Windows / POSIX）と CPU affinity 設定を追加。権限不足や未対応 OS を考慮して安全にフォールバック。
  - 監視・解析ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し PASS/FAIL 判定を出力。--from/--to/--db オプションをサポート。
  - リサーチ
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム、移動平均乖離、ATR、出来高系などを想定）。（実装は部分的、モジュールの方針と定数定義を含む）
  - パッケージ初期情報
    - src/kabusys/__init__.py: バージョン __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- 環境変数パーサー (.env 読み込み)
  - export KEY=val 形式、クォートされた値中のバックスラッシュエスケープ、インラインコメント処理、クォートなしの # に対するコメント扱い条件などに対応。OS 環境変数を保護する protected 引数を導入（自動読み込み時）。
- プロセス優先度/CPU 固定処理は権限不足やプラットフォーム差分で失敗してもログ警告でスキップするよう安全に実装。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- .env は決して Git にコミットしないようテンプレート・ウィザード側に注意書きを追加（config_setup）。
- 必須シークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を Settings 経由で取得し、未設定時は明示的に ValueError を発生させることで誤動作を防止。

Migration / Upgrade notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。未設定だと起動前にエラーになります。
- KABUSYS_ENV の有効値: development / paper_trading / live。値が無効だと Settings / validate_config でエラー。
- Paper Trading:
  - paper_trading 動作時は PAPER_TRADING_SQLITE_PATH（環境変数）またはデフォルト data/paper_trading.db に DB が作成され、production DB と分離されます。
  - PAPER_FILL_MODE の有効値: "instant" | "partial" | "never" | "reject"。不正値は ValueError。
- Kill Switch:
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると危険（validate_config で警告）。
- ログ:
  - logs/ ディレクトリに書き込めない環境ではファイル出力をスキップして stdout のみで動作します。

参考（主要ファイル）
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/config.py
- src/kabusys/config_setup.py
- src/kabusys/validate_config.py
- src/kabusys/utils/logging_setup.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/research/factor_research.py

-----

この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴やリリースノートとして使う場合は実装者による確認・追記をおすすめします。