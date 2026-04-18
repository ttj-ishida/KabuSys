# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このプロジェクトのバージョンは src/kabusys/__init__.py の __version__ に準拠します。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初期リリースとして、システム全体のコアユーティリティ・実行スクリプト・ポートフォリオ構築・検証ツール群を追加。
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成し、ExecutionEngine をバックグラウンドスレッドで実行。停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 実行用 PID ファイルを data/execution.pid に保存する設計（_EXECUTION_PID）。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバックし、警告を出力。
    - 監視は環境に関係なく本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。例外発生時はログに出力して次ポーリングへ継続。

- 設定・検証
  - Settings クラスによる環境変数アクセスラッパを追加（src/kabusys/config.py）。
    - .env/.env.local の自動ロード機能（プロジェクトルート検出）と、ロード無効化用環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env ファイルの高度なパース（export プレフィックス対応、クォート・エスケープ・インラインコメント処理）。
    - 各種設定プロパティ（J-Quants トークン、kabu API 設定、DB パス、監視しきい値、環境判定プロパティ等）を提供。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式に .env を生成・更新するウィザード。既存 .env の読み込み、シークレットマスク、保存確認を実装。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在確認および（PyYAML があれば）パース検証、live 環境固有のガードチェックを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収して優先度（high/normal/low）を設定。権限不足等の例外は警告ログでスキップ。
    - CPU affinity を最初の N コアに固定する関数も提供。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算を追加（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順、タイブレークは signal_rank 小さい方を優先。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分（全スコア 0 の場合は等配分へフォールバック）。
  - セクター集中制限・レジーム乗数を追加（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有・価格情報からセクター別エクスポージャを算出し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear および未知レジームのフォールバック）を実装。
  - 株数決定・リスク制限ロジックを追加（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method として "risk_based", "equal", "score" をサポート。
    - risk_based: 許容リスク率・損切り率からポジションサイズを算出。
    - equal/score: 重みから各ポジションの割当を算出。lot_size（単元株）で丸め、1銘柄上限・aggregate cap（available_cash）を考慮し、必要に応じスケールダウンと残差分のロット調整を実施。
    - cost_buffer により手数料/スリッページを保守的に見積もる。
  - portfolio パッケージのエクスポートを追加（src/kabusys/portfolio/__init__.py）。

- 解析・検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（デフォルト: data/paper_trading.db）から system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）を算出。
    - デフォルト閾値を設定（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）し、Pass/Fail 判定を行う。
    - --from / --to / --db オプションをサポート。
    - レポート生成時にテーブル欠如（OperationalError）を考慮してフォールバックして表示。

- 研究モジュール（部分実装）
  - ファクター計算モジュールの骨組みを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 等の計算方針・定数を定義。
    - calc_momentum のインターフェイスとドキュメントを追加（DuckDB 接続を受け取り prices_daily を参照）。※ソースファイルは途中で切れている箇所があり、関数本文の完全実装は今後の作業。

### Changed
- N/A（初期リリースのため既存機能の変更なし）。

### Fixed
- N/A

### Security
- N/A

### Notes / Implementation details
- デフォルトのファイルパスはコード内で明記:
  - DuckDB: data/kabusys.duckdb
  - SQLite (監視用): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
  - PID / stop flag: data/execution.pid / data/stop_requested.flag
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行うため、CWD に依存しない構成になっている。
- monitor / execution の起動フローには共通の安全措置（プロセス優先度設定、停止フラグ検知、DB 初期化 / クローズ、例外ログ）が含まれる。
- 一部モジュール（monitoring_db や ExecutionEngine の詳細実装、strategy や data パッケージの完全実装）はこの変更一覧に含まれるファイル参照から存在を伺わせるが、本リリースでは該当ファイルの実装内容により挙動が決まる点に注意。

もし CHANGELOG に追加・修正したい点（例えばリリース日・バージョン番号の変更、抜けている機能の追記など）があれば教えてください。