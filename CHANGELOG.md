# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

最新リリース: 0.1.0 — 2026-04-18

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しています。主な追加内容は以下の通りです。

### 追加 (Added)
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合はペーパートレード専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - 停止フラグ (data/stop_requested.flag) を監視し、検出時にエンジンを安全に停止。
    - 実行時の PID ファイルを書き出す (data/execution.pid デフォルト)。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に依らず本番 sqlite_path（data/monitoring.db デフォルト）を使用。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機構（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env / .env.local の読み込みルール（OS 環境変数優先、.env.local は上書き許可）。
    - 各種設定プロパティを Settings クラスとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - KABUSYS_ENV の妥当性チェック（development, paper_trading, live を受け入れ）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
  - config_setup.py
    - .env を対話形式で生成・更新するウィザード。
    - 多数の設定項目をユーザに提示し、保存用の .env を作成。
  - validate_config.py
    - .env と config/*.yaml の設定検証 CLI。
    - 必須環境変数のチェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、YAML パースチェック（PyYAML がインストールされている場合）など。
    - --strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築（純粋関数群・メモリ計算）
  - portfolio/portfolio_builder.py
    - シグナルの選択 (select_candidates)。
    - 等金額配分 (calc_equal_weights) とスコア加重配分 (calc_score_weights)。全スコアが 0 の場合は等配分にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py
    - セクター集中の上限適用 (apply_sector_cap)。売却予定銘柄をエクスポージャー計算から除外可能。
    - 市場レジームに応じた資金乗数 (calc_regime_multiplier)：bull/neutral/bear に対する既定値（1.0/0.7/0.3）、未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - 発注株数算出ロジック (calc_position_sizes)。
    - risk_based / equal / score の配分方式に対応。
    - 単位株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリング、手数料・スリッページのバッファ考慮など。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティ。
    - stdout への StreamHandler と日次ローテーションのファイルハンドラ (TimedRotatingFileHandler) を設定。
    - ログディレクトリは引数 > 環境変数 LOG_DIR > デフォルト logs/ の順に解決。ファイル出力はディレクトリ作成に失敗した場合は無効化して stdout のみで継続。
    - ログ保持は 30 日。
  - utils/process_priority.py
    - Windows と POSIX を吸収したプロセス優先度設定（psutil に依存）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS では警告を出してスキップ。

- 監視・レポート
  - monitoring モジュール用の DB 初期化呼び出し（init_monitoring_db を起動スクリプトで呼び出し、監視テーブルの冪等な作成を保証）。
  - tools/paper_verification_report.py
    - ペーパートレード用 DB を解析して検証レポートを生成する CLI。
    - 指標: 稼働率（uptime%), 注文成功率（fill_rate), 送信率（send_rate), レイテンシ (avg/max/P95)。
    - 基準値を設定して PASS/FAIL 判定を行う（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）。
    - DB パスは --db 引数 > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト data/paper_trading.db の順で解決。

- リサーチ（途中実装）
  - research/factor_research.py（ファクター計算の骨格）
    - モメンタム、MA200、ATR、出来高系などのファクター計算方針と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials テーブルから計算する設計。
    - 実装は一部（calc_momentum の冒頭）で始まっており、引き続き関数の完成が想定される。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 廃止 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （初回リリースのため該当なし）

## 互換性・移行メモ (Upgrade / Migration Notes)
- 必須環境変数
  - 以下は必ず設定してください: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - .env を生成するには config_setup.py のウィザードを利用できます: python -m kabusys.config_setup
- 環境切替
  - KABUSYS_ENV により動作モードが変わります。paper_trading を指定すると Execution は paper 用 DB（PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db）を使用します。監視（run_monitoring）は常に sqlite_path（SQLITE_PATH デフォルト: data/monitoring.db）を使用します。
- ログ
  - デフォルトで logs/ ディレクトリを作成し、アプリケーション別に日次ローテートされるログを保存します。必要に応じて LOG_DIR を設定してください。
- 停止フラグ / Kill Switch
  - 両スクリプトは data/stop_requested.flag を監視して安全停止します。運用上の停止はこのファイルを作成してください。KILL_FLAG_CLEAR_ON_START により起動時に kill flag を自動クリアする設定がありますが、本番では 0 を推奨します。
- 依存パッケージ
  - duckdb, psutil は必須（psutil はプロセス優先度設定で使用）。PyYAML は config 検証のための任意依存（インストールされていない場合は YAML 検証をスキップして警告を出力）。
- ファイル・ディレクトリの作成
  - 初回起動前に以下ディレクトリ（またはそれらを自動作成できる権限）を用意してください:
    - data/ （SQLite DB、PID/フラグファイル等）
    - logs/ （ログ出力）
  - logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化して stdout のみで継続します。

## CLI 使用例
- 環境ウィザード（.env 生成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict
- 実行エンジン起動
  - python -m kabusys.run_execution
- 監視プロセス起動
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db

---

このリリースは基盤機能の整備に重点を置いています。今後の予定としては、research/factor_research の完全実装、ExecutionEngine / BrokerClient の詳細実装・テスト、監視アラート（LINE通知等）の強化、より細かなユニットテストの追加などを想定しています。