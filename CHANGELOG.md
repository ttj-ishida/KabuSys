# Changelog

すべての重要な変更は「Keep a Changelog」形式に従って記録します。  
このファイルは人間が読める形式でのリリース履歴を目的としています。

値の解釈:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除
- Security: セキュリティ関連

## [Unreleased]

## [0.1.0] - 2026-04-18
初回公開リリース。

### Added
- 基本パッケージ情報
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 実行系 / エンジン周り
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を "high" に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合は paper trading 用の専用 SQLite (デフォルト: data/paper_trading.db) を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - RiskManager のデフォルトパラメータ（例: max_position_pct, max_utilization, rate_limit_per_sec 等）を提供。
    - 実行エンジンはスレッドで run_session を実行。停止はプロジェクトルート下の data/stop_requested.flag によるフラグ検出で行う。
    - PID ファイルの経路 (data/execution.pid) をサポート。

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用（監視データは本番 DB パスに記録）。
    - 停止フラグ (project_root/data/stop_requested.flag) による安全なシャットダウン検出。
    - init_monitoring_db により監視用テーブルの存在を保証。

- 設定管理
  - config.py: 環境変数 / .env ローディングと Settings クラスを追加。
    - プロジェクトルート自動検出 (.git または pyproject.toml を基準) により .env/.env.local を自動ロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - 独自の .env パーサー: export プレフィックス、クォート済み値（エスケープ含む）、インラインコメント取り扱い等をサポート。
    - Settings: 各種設定プロパティを提供（J-Quants トークン、kabu API、DuckDB/SQLite パス、paper trading 設定、監視閾値、実行環境判定など）。
    - PAPER_FILL_MODE の検証（有効値: "instant"|"partial"|"never"|"reject"）。
    - KABUSYS_ENV と LOG_LEVEL の入力検証を実装（許可値のチェック）。

  - config_setup.py: 対話式 .env 作成 / 更新ウィザードを追加。
    - 各設定項目に対する問い合わせ、デフォルト・選択肢、シークレットマスク表示を提供。
    - 最終確認後に .env を安全に書き込むテンプレート機能を実装。

  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証。
    - DUCKDB/SQLITE のパスや config/*.yaml の存在（および PyYAML が利用可能な場合はパースチェック）を実施。
    - `--strict` モードで警告をエラー扱いにできる。

- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同スコアは signal_rank 小さい方優先）で選択。
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア正規化配分（スコア合計が 0 の場合は等金額にフォールバック）

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別上限の適用（既存保有比率が上限を超える場合、新規候補を除外）。
      - "unknown" セクターは上限適用対象外。
      - sell_codes を除外してエクスポージャー計算可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピングと未知レジームのフォールバック）を提供。

  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数の算出ロジックを実装。
      - allocation_method に "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）を考慮。
      - cost_buffer を用いた保守的コスト見積りと残余配分ロジックを実装。

- データ・解析
  - research/factor_research.py（骨格実装）
    - モメンタム等のファクター計算ロジックの骨組み（DuckDB を使った prices_daily 参照を想定）。
    - 定数 (horizon/MA/ATR など) と calc_momentum のインターフェースを用意（実装の続きを拡張予定）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
      - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）をルートロガーに設定。
      - 既存ハンドラをクリアして二重出力を防止。
      - LOG_LEVEL / LOG_DIR の解決順の制御、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ動作。
  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定と CPU affinity 設定を追加。
    - Windows / POSIX(nice) のラップ、権限不足などの失敗は警告でスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
      - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、遅延（avg/max/P95）を算出。
      - 閾値を定義して PASS/FAIL 判定を出力。
      - CLI 引数: --from / --to / --db、環境変数 PAPER_TRADING_SQLITE_PATH を優先的に参照。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Notes / Migration
- .env は絶対にリポジトリにコミットしないこと（config_setup.py のヘッダにも注記あり）。
- 自動 .env ロードはプロジェクトルート検出に依存する（.git または pyproject.toml が必要）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視プロセスは監視用途の SQLite を「本番用の sqlite_path」を使用します。paper_trading の場合でも監視データは production sqlite_path に記録されます（設計上の注意）。
- 実行エンジン（ExecutionEngine）は paper_trading モードで DB を分離します（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。

---

この CHANGELOG はコードベースから推測して生成しています。実際のリリースノートを作成する際は、リリース作業やコミット履歴に基づいて適宜更新してください。