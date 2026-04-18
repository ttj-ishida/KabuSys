CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

フォーマットの指針:
- 変更は大分類（Added / Changed / Fixed / Deprecated / Security）で整理します。
- 各バージョンごとに日時を併記します（可能な場合）。

Unreleased
----------

- （今後のリリースに向けたプレースホルダ）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本パッケージ初期実装を追加（バージョン: 0.1.0）。
- 環境設定 / ロード関連
  - .env の自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を基準）。
  - .env ファイルのパース機能を実装（export 形式、シングル/ダブルクォート、行末コメントなどに対応）。
  - Settings クラスを実装し、環境変数経由でアプリ設定を提供（J-Quants / kabu API / DB パス / 監視閾値 等）。
  - config_setup CLI（対話式ウィザード）を実装し .env の初期生成・更新を支援。
  - validate_config CLI を実装し、起動前に必須環境変数や config/*.yaml を検証できるようにした（--strict オプションあり）。
- 実行エントリ / ランタイム制御
  - run_execution スクリプトを実装。
    - ExecutionEngine 起動フロー（プロセス優先度設定、DB 接続、BrokerClientFactory によるブローカ生成、依存コンポーネント組み立て、スレッドでの engine.run_session 実行）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB（data/paper_trading.db）を使用して本番 DB と分離する設計。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組み。
    - execution.pid ファイルパス管理をサポート（Settings 経由で指定可能）。
  - run_monitoring スクリプトを実装。
    - SystemMonitor の初期化・ポーリングループ実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 監視は設定に関わらず本番 sqlite_path を使用する仕様（監視用 DB として固定）。
    - 停止フラグ検知でループ終了、リソース（sqlite/duckdb 接続）を確実にクローズ。
- ロギング / プロセスユーティリティ
  - setup_logging を実装。
    - stdout ストリームハンドラと日次ローテートするファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR を環境変数から解決可能。
  - process_priority ユーティリティを実装（psutil による Windows / POSIX の差分吸収）。
    - set_process_priority(level) で優先度を "high"/"normal"/"low" に設定（権限不足時は警告をログ出力してスキップ）。
    - set_cpu_affinity(cpu_count) で最初の N コアにプロセスをピン留め（未指定は変更なし）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナル選定と重み計算（select_candidates / calc_equal_weights / calc_score_weights）。
  - risk_adjustment: セクター集中制限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）。
  - position_sizing: 銘柄ごとの発注株数算出（calc_position_sizes）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer 等のパラメータに対応。
    - 合計予算超過時のスケーリングロジック（端数処理と lot_size 単位での補正）を実装。
    - 設計上の TODO（価格欠損時のフォールバック等）を注記。
- リサーチ / ツール
  - research.factor_research の骨格を追加（DuckDB 接続を受け、Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計）。
    - モメンタム計算（calc_momentum）を含むが、ファイル末尾で実装途中（calc_momentum の実装が途中で切れていることを注記）。
  - tools.paper_verification_report を実装。
    - Paper Trading の検証レポート生成 CLI。
    - 検証指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ 等。
    - デフォルト閾値（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）を定義。期間指定（--from / --to）や DB パス指定（--db / 環境変数）に対応。
    - データ欠如やテーブル未存在時に graceful に N/A / 0 を扱う保護処理を追加。
- 監視データベース初期化
  - monitoring_db.init_monitoring_db を参照する呼び出しを run_* スクリプトに統合し、監視テーブルが存在することを保証（冪等）。
- パッケージ情報
  - パッケージの __version__ を "0.1.0" に設定。
  - モジュールエクスポート（portfolio パッケージの __all__ 等）を整理。

Changed
- N/A （初回リリースのため履歴変更なし）

Fixed
- N/A （初回リリースのためバグ修正履歴なし）

Deprecated
- N/A

Security
- N/A

Known issues / Notes
- research.factor_research.calc_momentum の実装が途中で終わっている（ファイル末尾で切れている）。このため一部ファクター計算が未完成。
- position_sizing.calc_position_sizes 内で price が欠損（0.0）の場合、エクスポージャーが過小見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨を TODO コメントで残している。
- ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソールログのみで継続する設計。運用上はログディレクトリの権限／存在を事前に確認することを推奨。
- process_priority の優先度設定は権限不足や未対応 OS の場合はスキップされ、警告が出力される。
- validate_config は PyYAML 未インストール時に YAML 検証をスキップする（警告出力）。config/*.yaml の構文検査を行うには PyYAML をインストールすること。

導入手順（簡易）
- .env を用意（config_setup.py のウィザードを推奨）。
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を設定。
- SQLite / DuckDB のパス（デフォルト: data/monitoring.db, data/kabusys.duckdb）に対してディレクトリ作成権限を確認。
- 実行:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定検証: python -m kabusys.validate_config
  - .env ウィザード: python -m kabusys.config_setup
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report

ライセンス / その他
- 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして公開する際は、ソース管理のコミット履歴・リリース日・著者情報を反映してください。