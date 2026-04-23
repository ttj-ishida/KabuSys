CHANGELOG
=========

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

リリース履歴
-----------

### [0.1.0] - 2026-04-23

Initial release — 基本機能の実装

#### Added
- 全体
  - KabuSys パッケージの初期バージョンを追加。パッケージバージョンは src/kabusys/__init__.py にて 0.1.0 として設定。
  - DuckDB / SQLite を用いたデータ処理基盤の導入（設定可能なパスを環境変数で指定可能）。

- 設定管理
  - 環境変数・.env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み。
    - OS 環境変数を保護する仕組み（.env.local の override 等）。
    - 必須環境変数取得ヘルパー _require()、各種プロパティ（DB パス、KABUSYS_ENV、ログレベルなど）を提供。
    - PAPER_FILL_MODE に対するバリデーションと paper_trading 用 SQLite パスのプロパティを実装。
  - 対話式設定ウィザード（.env 生成/更新）を追加（src/kabusys/config_setup.py）。
    - クライアント向けウィザードで主要な環境変数を対話的に設定可能。
    - .env の読み書き機能、既存値の再利用、シークレットマスキング等に対応。

- 設定検証
  - 起動前に .env および config/*.yaml の整合性を検証する CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルチェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パースチェック（PyYAML が存在する場合）など。
    - --strict オプションで警告をエラー扱いにできる。

- 実行関連
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を高に設定。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite を使用して本番 DB と分離（MockBrokerClient を利用する想定）。
    - BrokerClientFactory を利用したブローカー抽象／OrderManager、OrderRepository、RiskManager、Reconciler、ExecutionEngine の組み立てと起動ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）に対応。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番用途の sqlite_path を使用する設計。
    - SystemMonitor の check_once を周期的に実行し、停止フラグ検知で安全終了。

- ポートフォリオ構築（純粋関数）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順で上位 N を選択、同点時は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分。スコアが全て 0 の場合のフォールバック警告。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率を基に新規候補を除外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマッピングと未知値のフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: risk_based / equal / score の allocation_method をサポート。単元株（lot_size）、max_position_pct、max_utilization、cost_buffer、aggregate cap（スケーリング）などを実装。残余キャッシュに基づく再配分ロジックを備える。

- ユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（daily, 30日保持）をルートロガーに統一設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - LOG_LEVEL / LOG_DIR の優先解決ルールを提供。
  - プロセス優先度・CPU affinity 設定（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収してプロセス優先度設定、CPU affinity 設定（psutil 使用）を提供。許可エラー等は警告でスキップ。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - paper_trading の SQLite ログから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計してレポート出力。
    - 閾値を定義し PASS/FAIL 判定を行う（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms など）。
    - --from / --to / --db オプションにより期間・DB を指定可能。

- リサーチ（未完）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）の骨格を追加。
    - Momentum（1M/3M/6M、MA200 乖離率）、ATR、ボリューム系、Value 指標等の設計方針と定数を定義。DuckDB を用いた計算を想定。
    - 実装が途中で切れている（今後追加予定）。

#### Changed
- 初回リリースのため該当なし。

#### Fixed
- 初回リリースのため該当なし。

#### Deprecated
- 初回リリースのため該当なし。

セキュリティ・重要な注意点
------------------------
- .env ファイルは絶対にリポジトリにコミットしないこと（config_setup がヘッダに警告を記載）。
- KABUSYS_ENV=live の場合、LINE 通知設定や Kill Switch（KILL_FLAG_CLEAR_ON_START）の設定に注意するよう validate_config に警告ロジックを実装。
- プロセス優先度や CPU affinity の設定は権限不足で失敗する場合があり、その場合は警告で継続される設計。

設定（主要な環境変数とデフォルト）
---------------------------------
- KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: logs/（ログファイルの保存先）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト 60 秒（run_monitoring）
- PAPER_FILL_MODE: paper_trading の振る舞い（instant / partial / never / reject）。デフォルト instant
- KILL_FLAG_CLEAR_ON_START: 起動時の Kill Flag 自動クリア（0/1）。デフォルト 0

CLI / 実行例
------------
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

既知の制限 / TODO
-----------------
- research.factor_research モジュールは実装途中。ファクター計算ロジックの追加が必要。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別単元対応を検討）。
- apply_sector_cap の価格欠損時のフォールバック（前日終値等）の実装は未完（TODO コメントあり）。
- 一部の機能は外部依存（psutil, duckdb, PyYAML）により挙動が変化するため、デプロイ時に依存パッケージを確認すること。

ライセンスや貢献方法等についてはリポジトリのドキュメントを参照してください。