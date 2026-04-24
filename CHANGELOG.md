# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
このファイルはコードベースの内容から推測して作成しています。

現在のバージョン: 0.1.0

## [Unreleased]

- なし（初期公開リリース相当の内容を 0.1.0 に記載しています）。
- 注: 一部モジュール（research/factor_research の calc_momentum 等）は開発中／未完の箇所が見られます。今後のリリースで完成・改善される予定です。

## [0.1.0] - 2026-04-24

最初の公開リリース（推測）。自動売買システム KabuSys のコアユーティリティ群と CLI をまとめた初期版。

### Added

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ開始スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
    - 停止制御に data/stop_requested.flag を使用。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を利用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、ExecutionEngine の起動・監視・停止処理（stop flag / PID ファイル対応）を実装。

- 設定・環境管理
  - config.py
    - Settings クラスを導入し、環境変数から一元的に設定を取得。
    - .env の自動読み込み機能（プロジェクトルート検出 .git / pyproject.toml を基準）。
    - .env の行パースで export 形式・クォート・インラインコメント等に対応する堅牢な実装。
    - paper_trading 用設定（paper_sqlite_path, paper_fill_mode）や監視閾値、PID/KILL フラグ等のプロパティを追加。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を追加。シークレットはマスク表示。
  - validate_config.py
    - 起動前に .env および config/*.yaml の設定整合性を検査する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、PyYAML が無ければ警告を出す等の検証ロジックを実装。
    - --strict フラグで警告を FAIL 扱いにできる。

- モジュール群
  - portfolio
    - portfolio_builder.py
      - 候補選定（select_candidates）と配分重み（等金額 calc_equal_weights、スコア加重 calc_score_weights）を実装。
    - risk_adjustment.py
      - セクター集中上限の適用（apply_sector_cap）とレジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
      - 未知レジーム時はフォールバック挙動を実装（警告ロギング）。
    - position_sizing.py
      - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
      - lot_size（単元株）丸め、1銘柄上限・aggregate cap、費用バッファ（cost_buffer）を考慮したスケーリングロジックを実装。
  - research
    - factor_research.py
      - モメンタム・ボラティリティ等のファクター計算モジュール骨子を追加。
      - DuckDB を使い prices_daily / raw_financials を参照して定量ファクターを算出する設計。※一部関数は実装途上。
  - monitoring
    - monitoring_db 初期化ユーティリティ（init_monitoring_db）を使用して監視用テーブルの冪等初期化を実装（各スクリプトで利用）。
  - execution（概要）
    - OrderRepository, OrderManager, Reconciler, RiskManager, ExecutionEngine 等のコンポーネントを想定した組み立てを実装（起動スクリプトでの組合せにより動作）。
    - RiskConfig のデフォルト値を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。初期ポートフォリオ値は broker.get_available_cash() から取得。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化ユーティリティを追加。
    - stdout 出力の StreamHandler と日次ローテート（TimedRotatingFileHandler）を root ロガーにセット。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ローテーション保持日数は 30 日。
  - utils/process_priority.py
    - プロセス優先度設定（Windows と POSIX の差分吸収）と CPU affinity 設定ユーティリティを追加。
    - 標準的なレベル ("high"/"normal"/"low") をサポート。権限不足等の失敗は警告としてスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。閾値は定数で定義（例: 稼働率 >= 99% 等）。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）に対応。

### Changed

- ログ出力の一貫化
  - すべての主要起動スクリプトから setup_logging を呼び出して統一的なログ管理を行う設計に統一。

- .env 自動読み込みの挙動
  - プロジェクトルートが検出できない場合は自動ロードをスキップ（配布後の環境で安全に動作）。

### Fixed / Robustness improvements

- MONITOR_POLL_INTERVAL の不正値対策
  - 非正の値や整数変換に失敗した場合は警告を出しデフォルト値にフォールバックする実装を追加（run_monitoring.py）。
- ログディレクトリ作成失敗時のフォールバック
  - ディレクトリ作成に失敗した場合はファイルハンドラを使用せず、コンソール出力のみで継続するようにして起動失敗を回避。
- プロセス優先度設定の例外ハンドリング強化
  - 権限不足や非対応 OS の場合は警告を出して処理をスキップする安全な実装。

### Known issues / Notes

- research/factor_research.py の一部関数（calc_momentum 等）は実装が途中のように見えます（ファイル終端で中断）。今後未完成部分の実装が必要です。
- position_sizing の価格欠損（price が 0.0）の扱いに関する TODO コメントあり（フォールバック価格の導入検討）。
- 一部の外部依存（psutil, duckdb, PyYAML 等）が存在するため、環境によってはインストールが必要です。validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出します。
- 本 CHANGELOG はコード内容から推測して作成したため、実際の変更履歴と差異がある可能性があります。

---

この CHANGELOG は Keep a Changelog のセクション（Unreleased / バージョン毎の追加・変更・修正）に従っています。必要であれば、各コミットや実際のリリースノートに合わせて日付や内容を更新してください。