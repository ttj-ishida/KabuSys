Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードベースから推測できる変更点・追加機能を項目化しています。

注意:
- これは実際のコミット履歴ではなく、提供いただいたコード内容から推測して作成した初期リリース向けの変更履歴です。
- 必須環境変数の設定や .env の作成は初回セットアップ時に必要です（config_setup と validate_config を参照）。

============================================================
Keep a Changelog
全ての重要な変更をこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/
============================================================

## [0.1.0] - 2026-04-21
初期リリース。システムのコア機能、運用スクリプト、設定ユーティリティ、ポートフォリオ構築・ポジション決定ロジック、監視・検証ツールなどを含む初版を導入。

### 追加 (Added)
- パッケージ全体
  - 基本パッケージ `kabusys` を導入。バージョンは `__version__ = "0.1.0"`。

- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - 環境により paper_trading モードで MockBrokerClient を使用し、Paper Trading 用 DB（data/paper_trading.db）と分離する挙動をサポート。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）および実行 PID 管理を実装。
    - ExecutionEngine の構成要素（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler）を組み立てて実行。
    - RiskManager のデフォルト設定値（max_position_pct 等）を定義。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境に関わらず本番用 sqlite_path を使用して監視情報を記録。
    - 停止フラグ検出でループ終了、例外捕捉で次ポーリングに継続。

- 設定関連
  - config.py: 環境変数と設定を管理する `Settings` クラスを実装。
    - .env ファイルの自動読み込み (プロジェクトルート検出: .git または pyproject.toml)。
    - .env の読み込み順序: OS 環境 > .env.local > .env。OS 環境を保護する仕組みを実装。
    - .env パースの堅牢化（export 形式、クォート文字列、エスケープ、インラインコメント処理）。
    - 各種設定プロパティ（DBパス、PID / KILL フラグ、閾値、PAPER_FILL_MODE バリデーションなど）を提供。
    - KABUSYS_ENV の検証（development / paper_trading / live）やログレベル検証を行う。

  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。
    - 主要な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）を対話的に入力して .env に書き出す。
    - 既存 .env の読み込みと既存値の再利用に対応。

  - validate_config.py: 起動前の設定検証ツールを追加。
    - 必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース検証（PyYAML がない場合は警告）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（毎日ローテート、30 日保持）を設定するユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベルとログディレクトリの解決順序を明示。
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを追加。
    - Windows / POSIX (Linux/Mac/FreeBSD) に対応し、権限不足等の失敗を警告してスキップする安全設計。

- ポートフォリオ構築・リスク制御・ポジション算出
  - portfolio/portfolio_builder.py:
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコアが全て 0 の場合は等金額配分にフォールバック（警告）。

  - portfolio/risk_adjustment.py:
    - セクター集中制限を実施する apply_sector_cap を追加。既存保有のセクター比率を計算して上限を超えるセクターの新規候補を除外。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear をマップ、未知のレジームはフォールバックで 1.0）。

  - portfolio/position_sizing.py:
    - ポジションサイズ算出 calc_position_sizes を追加。複数の allocation_method をサポート（"risk_based"、"equal"、"score"）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）を実装。cost_buffer による保守的見積もり対応。
    - 価格欠損や 0 値への安全処理、残余配分の再現性確保ロジック（fractional remainders）を実装。

- 監視 / 検証ツール
  - monitoring.monitoring_db モジュールを参照して監視テーブルの初期化（init_monitoring_db）を呼び出す仕組みを導入（冪等）。
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を参照して検証レポートを生成するスクリプトを追加。
    - 指標: 稼働率、注文成功率 (Filled/Created)、送信率 (Sent/Created)、リスク却下数、API レイテンシ（avg/max/P95）などを出力。
    - P95 計算、日付フィルタ（--from/--to）、閾値による PASS/FAIL 判定を実装。デフォルト閾値を定義（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200ms）。

- リサーチ / ファクター計算（下書き / 実装開始）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、ボリューム系等の計算方針を実装）。関数 calc_momentum の実装開始（コード断片あり、以降の処理は継続実装想定）。

### 変更 (Changed)
- 設計上の注記（実装仕様として明示）
  - run_monitoring は monitoring 用 DB に常に本番 sqlite_path を使用する（監視は環境に依存しない方針）。
  - ログは stdout に出力する設計（cron/task scheduler の出力統合を想定）。

### ドキュメント (Documentation)
- 各モジュールに docstring を充実させ、使い方・設計方針・引数仕様・返り値を明記。
- config_setup と validate_config に実行手順の説明を追加。

### 未着手 / 注意事項 (Known issues / Notes)
- factor_research.calc_momentum の実装が途中で切れている箇所あり（ファイル末尾の断片）。さらなる実装が必要。
- price が欠損（0.0）の場合のエクスポージャー計算で過少評価される可能性があり、将来的にフォールバック価格（前日終値等）を導入する旨の TODO が存在。
- 一部処理は外部ライブラリ（psutil、duckdb、PyYAML）に依存。実行環境にインストールが必要。
- .env 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定可能（テスト用途）。

### 互換性 / Breaking Changes
- 初期リリースのため破壊的変更はなし。

------------------------------------------------------------
セットアップ / 初回起動の推奨手順（参考）
1. .env を作成:
   - python -m kabusys.config_setup
2. 設定検証:
   - python -m kabusys.validate_config
3. 実行:
   - 監視: python -m kabusys.run_monitoring
   - 実行エンジン: python -m kabusys.run_execution
4. Paper Trading 検証:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

必要な主要環境変数の例:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL, LOG_DIR（オプション）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（本番アラート用、任意）

============================================================
以上です。CHANGELOG の文言や日付、項目の追加・修正希望があれば指示してください。