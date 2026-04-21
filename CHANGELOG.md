# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号は `src/kabusys/__init__.py` の `__version__` に準拠しています。

## [Unreleased]

なし

## [0.1.0] - 2026-04-21

初回リリース。自動売買システム KabuSys のコアユーティリティ、実行/監視ランナー、設定管理、ポートフォリオ構築ロジック、ペーパートレード検証ツール等を追加。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: `data/paper_trading.db`）を使用し、MockBrokerClient を利用する設計（BrokerClientFactory 経由）。
    - 監視用テーブル初期化（init_monitoring_db）を起動時に行う（冪等）。
    - 実行中の PID を `data/execution.pid` に記録するための pid_file サポート。
    - プロセス停止は `data/stop_requested.flag` によるフラグ検出で行う。
  - run_monitoring.py
    - SystemMonitor ポーリングループの起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出す。
    - Monitoring は環境に関わらず本番用の sqlite_path を使用する（監視データは共通 DB を想定）。
    - 起動時にプロセス優先度を "high" に設定し、stop フラグでループを終了する。

- 設定管理
  - config.py
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）を実装。
    - `.env` および `.env.local` の自動読み込み（OS 環境変数優先、.env.local は上書き）を実装。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 各種環境変数取得用プロパティを備えた `Settings` クラスを追加（J-Quants / kabu API / LINE / DB パス / 監視閾値 / レジーム判定等）。
    - `paper_fill_mode` のバリデーション（有効値: "instant"|"partial"|"never"|"reject"）。
    - `env` / `log_level` の値検証と bool 補助プロパティ（is_live/is_paper/is_dev）。
  - config_setup.py
    - 対話式ウィザードで `.env` を作成・更新する CLI を追加。
    - シークレット項目（トークン等）はマスクして表示。既存値の再利用やデフォルト値の提示に対応。
    - `.env` の読み書きロジックを提供（既存ファイルの読み取り、テンプレートで書き込み）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML 未インストール時はスキップ）等を実装。
    - `--strict` オプションでワーニングを失敗扱いにできる。
    - `live` 環境向けの追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の危険設定の警告）を実装。

- ポートフォリオ構築ライブラリ（メモリ計算のみ）
  - portfolio.portfolio_builder
    - select_candidates: スコア順にシグナルをソートして上位 N を選択。
    - calc_equal_weights: 等配分重み。
    - calc_score_weights: スコア加重（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック。既存保有のセクター比率が上限を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数を計算する主要関数を実装。allocation_method に "risk_based"/"equal"/"score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限 (max_position_pct)、aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積り、残余キャッシュによる端数分配ロジック等を実装。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）から統計を集計して検証レポートを生成するスクリプトを追加。
    - 集計項目: システム稼働率（system_status）、注文成功率・送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（P95 を含む）。
    - デフォルトの判定基準（稼働率 >= 99%、成立率 >=90%、送信率 >=95%、P95 <=200ms）を用いて PASS/FAIL を判定。
    - コマンドラインで期間フィルタ（--from/--to）および DB パス指定（--db）をサポート。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、既定保持 30 日）を設定。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - プロセス優先度設定（Windows / POSIX を吸収）および CPU affinity 固定機能を追加。
    - エラー時は警告を出し設定をスキップする堅牢化を実装。

- research
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム等の定義、calc_momentum の実装開始）。DuckDB を用いた prices_daily テーブル参照想定。

- パッケージ管理
  - src/kabusys/__init__.py にバージョン `0.1.0` を追加。
  - パッケージのエクスポート（portfolio 等）を __all__ で定義。

### Changed
- なし（初回リリースのため変更履歴は無し）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

注意:
- 上記はリポジトリ内のソースコードから推測した変更点・仕様の要約です。実際の動作や外部依存（BrokerClient 実装、SystemMonitor/ExecutionEngine の詳細、config/*.yaml のフォーマット等）はそれぞれの実装に依存します。