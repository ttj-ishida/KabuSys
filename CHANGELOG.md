# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

最新の変更は一番上に記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-22

初回リリース。

### Added
- 基本アプリケーションパッケージ KabuSys を追加
  - バージョン: 0.1.0

- 起動スクリプト / デーモン化関連
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用して本番 DB と分離。
    - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した安全な起動/停止制御。
    - デーモン的に ExecutionEngine をスレッドで実行し、停止フラグ検知でエンジン停止→終了を行う。
    - Execution 側の主要コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine）を組み立てて起動する。
    - RiskManager のデフォルト設定を組み込み（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() により初期化。

  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) による優雅なループ終了、KeyboardInterrupt の捕捉、例外発生時のログ出力と次回ポーリングへの継続。

- 設定関連
  - config.py: 環境変数・設定管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動読み込みを行う。
    - .env 自動読み込みの挙動を KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサは export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理などを含む堅牢な実装。
    - Settings クラスを提供し、各種設定値（J-Quants / kabuAPI / LINE / DuckDB/SQLite/ペーパートレード設定 / 監視閾値 / ログ設定等）をプロパティとして取得可能。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の検証を実装。

  - config_setup.py: 対話式ウィザードを追加（.env ファイルの初期作成・更新支援）。
    - 秘匿項目は入力時にマスク表示、保存前の確認、.env テンプレートの自動生成機能を提供。
    - デフォルト値や選択肢を提示して初心者でも .env を作成しやすい UX を実装。

  - validate_config.py: 設定検証 CLI を追加。
    - .env と config/*.yaml の存在・基本整合性検証、必須環境変数のチェック、KABUSYS_ENV=live 時の追加ガード等。
    - --strict オプションで警告も失敗扱い（exit code 1）にできる。

- ポートフォリオ構築ライブラリ (pure functions)
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソートと上位抽出を追加。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分（全スコア 0 の場合は等分配にフォールバックし警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有の時価ベースで判定）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を実装（未知レジームは 1.0 でフォールバックし警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based", "equal", "score") に基づく株数算出を実装。
      - lot_size（単元株）丸め、1 銘柄上限、aggregate cap によるスケールダウン（小数端数は lot 単位で再配分）、cost_buffer を用いた保守的見積もりをサポート。
      - 価格欠損時や価格 <= 0 のケースでスキップし、ログにデバッグ情報を出力。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）、リスク却下数）を集計し、PASS/FAIL レポートを標準出力に生成するスクリプトを追加。
    - P95 計算、日付フィルタ、存在しないテーブルへの堅牢なフォールバックを実装。
    - デフォルトの合格閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。

- 研究 / ファクター計算（骨格）
  - research/factor_research.py（モメンタム等のファクター計算の設計と一部実装を追加）
    - DuckDB を用いた prices_daily / raw_financials ベースの計算方針を実装（関数群を提供する設計）。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging: ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティ。
    - LOG_DIR 指定や環境変数 LOG_LEVEL の解決、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）をサポート。
    - stdout を使うことでジョブスケジューラ等でのリダイレクト運用を想定。

  - utils/process_priority.py
    - set_process_priority: Windows と POSIX の差分を吸収してプロセス優先度を設定するユーティリティを追加。
    - set_cpu_affinity: 指定コア数へのピン留め機能を提供（失敗時は警告してスキップ）。
    - 利用できない権限や未対応 OS の場合は安全にスキップして警告ログを出す。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注:
- .env は秘匿情報を含むため絶対にリポジトリにコミットしないでください（config_setup が生成する .env ヘッダでも注意を促しています）。
- 本リリースでは SystemMonitor / ExecutionEngine の具体的実装（監視・発注ロジックの詳細）は別モジュールに分離されています。運用前に validate_config を実行して設定を確認してください。