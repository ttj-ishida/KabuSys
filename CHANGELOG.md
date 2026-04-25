CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
各バージョンの要約はコードベースから推測して作成しています。

## [Unreleased]

（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-04-25

初回リリース。日本株自動売買システム KabuSys の基盤ユーティリティ、起動スクリプト、設定管理、検証ツール、Paper Trading 向け検証レポート、ポートフォリオ構成ロジックなどの主要コンポーネントを追加。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。
    - KABUSYS_ENV=paper_trading の場合は専用の Paper Trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由で実際のブローカ／モックを切替。
    - ストップフラグ（data/stop_requested.flag）検知による安全停止、PID ファイル出力制御。
    - 実行はデーモンスレッドで行い、停止フラグ検知で engine.stop() を呼び停止。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、値検証あり）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動を採用（明示的挙動）。
    - 停止フラグ検知、例外発生時のログ出力とリカバリを実装。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能（.env, .env.local）を提供。プロジェクトルートを .git または pyproject.toml から自動検出。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - 強力な .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応）。
    - Settings クラスを導入し、各種設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE など）へのアクセスと妥当性チェックを提供。
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
    - 環境判定ユーティリティ（is_live, is_paper, is_dev）。

  - config_setup.py
    - 対話式 .env 作成・更新ウィザード。既存値の再利用、シークレット項目のマスク表示、デフォルト値提示、保存確認機能を提供。

  - validate_config.py
    - 起動前の設定検証 CLI。必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検査（PyYAML が存在する場合）。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging 関数を追加。
    - stdout への StreamHandler（stdout 使用）と、日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラをルートロガーに設定。
    - LOG_DIR 指定や環境変数 LOG_LEVEL の優先解決、ログディレクトリ作成失敗時のフォールバック（コンソール出力のみ）を実装。
  - utils/process_priority.py
    - set_process_priority: Windows/Linux/macOS を吸収してプロセス優先度を設定。アクセス権限不足時は警告を出して安全にスキップ。
    - set_cpu_affinity: 指定コア数で CPU affinity を固定（利用可能コア数チェック、例外ハンドリングあり）。

- ポートフォリオ構築・ポジション決定ロジック
  - portfolio/portfolio_builder.py
    - 信号のソート（スコア降順 + signal_rank によるタイブレーク）
    - 等金額配分（calc_equal_weights）
    - スコア加重配分（calc_score_weights）— 全銘柄スコアが 0 の場合は等金額配分にフォールバック
  - portfolio/risk_adjustment.py
    - セクター集中抑止（apply_sector_cap）: 既存保有のセクター比率に基づいて新規候補を除外
    - レジーム乗数（calc_regime_multiplier）: bull/neutral/bear に応じた乗数（未知値は警告後 1.0 フォールバック）
  - portfolio/position_sizing.py
    - position size 計算（calc_position_sizes）
    - allocation_method: "risk_based" / "equal" / "score" をサポート
    - 単元株（lot_size）丸め、1 銘柄上限・総投資上限（aggregate cap）へのスケーリング、cost_buffer による保守的コスト見積り
    - スケールダウン時の残差処理（lot_size 単位での再配分）を実装

- Paper Trading & 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を解析して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出するレポートツール。
    - CLI から期間（--from/--to）や DB パス（--db）を指定可能。
    - 合格基準（デフォルト）を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）し、PASS/FAIL 判定を出力。

- research/factor_research.py
  - DuckDB を用いたファクター計算モジュール（モメンタム / MA200 / ATR / 出来高系など）の基盤を追加（設計方針や定数定義を含む）。※実装の一部は継続開発中

- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を追加

### Changed
- 実行ログの一貫化
  - setup_logging により全スクリプトで統一的にログ設定を行うように統制（stdout + 日次ファイルローテーション）。
- 起動時のプロセス優先度設定を各起動スクリプトの最初に実行するように統一（set_process_priority("high") を呼び出し）。
- run_monitoring の挙動
  - 監視は環境設定に依らず、本番用 sqlite_path を参照することを明示（監視データを本番 DB に集約する方針）。

### Fixed / Robustness improvements
- .env パーサー強化（config.py）
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理に対応。これにより実運用での .env 設定ミスに強くなった。
- MONITOR_POLL_INTERVAL の入力妥当性検証（run_monitoring.py）
  - 1 未満・無効な値は警告を出しデフォルト（60秒）へフォールバック。
- ログディレクトリ作成失敗時のフォールバック（logging_setup.py）
  - ディレクトリ作成に失敗した場合はファイルハンドラをスキップし、コンソールログのみで継続。警告を stderr に出力。
- process_priority / cpu affinity の例外ハンドリング（utils/process_priority.py）
  - アクセス拒否や未実装エラーを捕捉して警告出力し、起動を中断しない設計。
- DB 初期化の冪等化（init_monitoring_db の呼び出し）
  - run_execution / run_monitoring で起動時に監視テーブルの存在を保証（init_monitoring_db を呼び出し）。既存 DB に対して安全に何度でも呼べる作り。

### Notes / Known limitations
- research/factor_research.py の実装が途中で切れている箇所があり、Factor 計算の一部は継続実装が必要。
- 一部の実行ロジック（ExecutionEngine、SystemMonitor、BrokerClientFactory、OrderManager 等）の詳細実装はこの差分に含まれている呼び出し箇所からの参照に留まり、実体は別モジュールに依存している（本 CHANGELOG は現行ファイル群の観察に基づく要約）。
- Paper Trading の振る舞い（MockBroker の細かい挙動等）は BrokerClientFactory 側の実装に依存するため、検証は当該実装に基づく。

---

今後のリリースでは以下を予定（案）
- research/factor_research の完全実装とユニットテスト
- Execution/Monitoring の統合テスト、異常系のさらに厳密なハンドリング強化
- 銘柄別 lot_size 設定対応（stocks マスタ参照による銘柄別単元対応）
- ドキュメント（PortfolioConstruction.md 等）との照合テストおよびサンプルデータを用いた検証パイプラインの整備

------