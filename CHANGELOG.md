# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新: Unreleased

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

### Added
- 初期リリースを追加。
- コア起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離する設計。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
    - 停止制御: project/data/stop_requested.flag を検出するとエンジンを停止・起動中止する。
    - 実行時 PID を data/execution.pid に書き込む設定をサポート（設定経由）。
    - BrokerClientFactory によるブローカークライアントの抽象化を導入（モック／実ブローカーの切り替え）。
    - RiskManager のデフォルト設定値を提供（max_position_pct 等）。初期ポートフォリオ値は broker.get_available_cash() から取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトへフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定管理
  - config.py
    - Settings クラスを実装し、環境変数からの設定取得を集約。
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env / .env.local の読み込み順と保護キー（OS 環境変数の保護）に対応。
    - 各種プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の検証（"instant"|"partial"|"never"|"reject"）を実装。
    - KABUSYS_ENV と LOG_LEVEL の検証を実装（有効値を限定）。

  - config_setup.py
    - .env 初期作成・更新を対話式で支援するウィザードを実装。
    - 主要な環境項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL など）を対話的に設定可能。
    - 既存 .env の読み込み・マスク表示、保存前の確認を実装。
    - 保存時に .env ファイルのテンプレートヘッダ（コミット禁止の注記など）を出力。

  - 設定検証 CLI
    - validate_config.py を実装。
    - 必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）存在チェック、プレースホルダ値の警告、KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装。
    - DUCKDB/SQLITE のパス親ディレクトリの存在チェック（警告）。
    - config/*.yaml の存在確認と、PyYAML が存在する場合は YAML パース検証を実行。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict モードで警告を FAIL 扱いにできる。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率配分を計算。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: 同一セクター集中を検出し、新規候補から除外する機能（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に応じて投下資金乗数を返す（未定義は 1.0 にフォールバックして警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数決定、単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash に基づくスケールダウン）、cost_buffer（スリッページ等の保守的見積り）対応。
    - risk_based では stop_loss_pct / risk_pct に基づく株数決定、等。

- 研究・ファクター計算
  - research.factor_research
    - StrategyModel に基づくファクター計算モジュールを追加（モメンタム、バリュー、ボラティリティ、流動性等を計画）。
    - DuckDB 接続を受け prices_daily / raw_financials を参照して計算する方針。モメンタム計算の実装が開始されている（target_date 基準の各種リターン、MA200 乖離等）。

- ツール
  - tools.paper_verification_report
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）。
    - デフォルト閾値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ (--from / --to) と --db オプションをサポート。PAPER_TRADING_SQLITE_PATH 環境変数も使用可能。
    - P95 計算ユーティリティを実装。

- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup
    - setup_logging 関数を実装。
    - ルートロガーをクリアしてから StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップし stdout のみで継続。
    - 同一プロセス内での二重ハンドラ設定を防止。
  - utils.process_priority
    - set_process_priority(level) 実装（"high"|"normal"|"low"）。
    - Windows 用の priority class / POSIX の nice 値を抽象化して設定。
    - set_cpu_affinity(cpu_count) 実装（最初の N コアに固定）。アクセス権限や未サポート OS では警告を出してスキップ。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

---

メジャー／マイナー／パッチの付け方:
- 現バージョンは初期公開版として 0.1.0 を設定しています。API（関数シグネチャ）や設定項目に後方互換性のない変更が入る場合はメジャー番号を更新してください。