# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。  

## [Unreleased]
- 今後の変更点をここに記載します。

## [0.1.0] - 2026-04-18
初回リリース。リポジトリに含まれる主要機能と CLI/ユーティリティをまとめて追加。

### Added
- 基本情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV による挙動分岐（paper_trading の場合は専用 DB と MockBrokerClient を利用）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御にデータディレクトリ内の stop_requested.flag を利用し、PID ファイル管理に対応。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立ててスレッドで実行。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了。

- 設定管理
  - config.py: 環境変数・設定読み込みモジュールを追加。
    - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env のパースは export 形式・クォート・エスケープ・インラインコメントなどを考慮。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、閾値、環境種別判定等）をプロパティとして取得。値検証（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を実装。
    - settings = Settings() グローバルインスタンスを提供。

- 設定ユーティリティ / CLI
  - config_setup: .env ファイル作成・更新の対話式ウィザードを追加。
    - J-Quants / kabu API / DB パス / LINE 設定など主要項目を対話入力で生成。
    - シークレット入力のマスク表示、デフォルト/既存値の再利用、保存確認をサポート。
  - validate_config: 起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース（PyYAML があれば内容検証）を実施。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構成ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N 件を選定（signal_rank によりタイブレーク）。
    - calc_equal_weights: 等金額配分の重みを算出。
    - calc_score_weights: スコア加重配分を算出（全てスコアが 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクターごとの既存保有比率を評価し、上限を超えるセクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返却（未知レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: weight / candidates / リスク指標などに基づき発注株数を算出。
      - risk_based と equal/score の両方式をサポート。
      - 単元株 (lot_size) による丸め、1銘柄上限・aggregate cap（available_cash）でのスケーリング、cost_buffer（手数料・スリッページ見積）を考慮。
      - スケールダウン後の残余配分はフラクション残差に基づき再配分して再現性を保つ実装。

- 監視 / ツール
  - monitoring_db 初期化呼び出しを run_* スクリプトで行い、監視テーブルの存在を保証（冪等）。
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg, max, P95）を計算してレポート出力。
    - 閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - --from / --to / --db オプションで期間・DB を指定可能。

- リサーチ
  - research.factor_research: モメンタム等のファクター計算モジュールの骨組みを追加（DuckDB を使った prices_daily / raw_financials 参照を想定）。
    - モメンタム（1M/3M/6M、MA200乖離等）、ATR、流動性等の定義とスキャン窓の定数を定義。関数 calc_momentum の宣言とドキュメントが含まれる（実装継続）。

- ユーティリティ
  - utils.logging_setup: 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler、30日保持）のファイル出力をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の優先解決を実装。
  - utils.process_priority: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。
    - Windows と POSIX(Linux/Mac/FreeBSD) に対応。psutil を利用。アクセス権限や未サポート環境では警告を出してスキップ。
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- 設定読み込みはデフォルトで自動実行されるが、テストなどで無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を使用可。
- .env の自動ロードでは OS 環境変数を保護（.env.local の上書きも保護キーを考慮）。
- Paper Trading と Live の DB は明確に分離される設計（paper_trading 用に PAPER_TRADING_SQLITE_PATH を指定可能）。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されるが、ログディレクトリ作成失敗時は標準出力のみにフォールバックする。

---

今後のリリースでは、research.factor_research の完全実装、monitoring/system_monitor の詳細実装・アラート送信（LINE 連携）や execution のテスト用モック強化などが想定されます。