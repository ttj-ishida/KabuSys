CHANGELOG
=========

このファイルは「Keep a Changelog」に準拠しています。
リリース履歴はセマンティックバージョニングを前提とします。

Unreleased
----------

（次回リリースに向けてのエントリをここに追加してください）

0.1.0 - 2026-04-23
-----------------

初回公開リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、
設定管理ツール、ペーパートレード検証ツール、および各種ユーティリティ群を収録しています。

Added
- 基本バージョン情報を追加
  - パッケージ版番号を src/kabusys/__init__.py の __version__ = "0.1.0" として定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離。
    - BrokerClientFactory を用いて環境に応じたブローカークライアントを生成。
    - PID 管理（data/execution.pid）および停止フラグ（data/stop_requested.flag）に対応。停止フラグ検知でエンジンを安全停止。
    - スレッドで ExecutionEngine.run_session を実行し、停止フラグ監視ループを実装。
    - RiskManager の初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）をデフォルト値で注入。

  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値（0 以下や整数以外）の場合はデフォルトにフォールバックして警告を出力。
    - 監視用 DB 初期化（init_monitoring_db）を実行。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは一元管理）。

- 設定管理
  - src/kabusys/config.py
    - 環境変数自動読み込み機能（プロジェクトルートを .git または pyproject.toml により検出）。
    - .env/.env.local ファイルの読み込み実装（override/protected 機能）。
    - .env パースの細かな挙動対応（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い）。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、Paper Trading 設定、監視閾値、PID/Kill フラグパス等）をプロパティ経由で取得。値検証（有効な KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を行う。
    - settings = Settings() のインスタンスをエクスポート。

  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI。
    - 入力補助・選択肢表示、シークレット値のマスク、既存 .env 読み込みの再利用などに対応。
    - .env ファイルはテンプレート形式で安全に書き出し（コミット禁止の注意書き含む）。

  - src/kabusys/validate_config.py
    - 起動前に設定の整合性を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションにより警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
    - スコアが全て 0 の場合は等配分へフォールバック。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（現保有のセクターエクスポージャーに基づいて候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" のマッピング、未知値は 1.0 にフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - position サイズ決定ロジック calc_position_sizes。
    - risk_based / equal / score の配分方式対応、単元株（lot_size）丸め、1 銘柄上限・合計投下上限のスケール調整、cost_buffer による保守的見積り。

  - パッケージエクスポートを整備（src/kabusys/portfolio/__init__.py）。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 共通ロギング設定ユーティリティ setup_logging。
    - stdout への StreamHandler（stdout を使用）、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、バックアップ 30 日）を設定。
    - 既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック対応。
    - LOG_LEVEL / LOG_DIR の解決順と引数上書きに対応。

  - src/kabusys/utils/process_priority.py
    - プロセス優先度設定のクロスプラットフォームユーティリティ（set_process_priority）および CPU affinity 設定（set_cpu_affinity）。
    - Windows / POSIX（Linux/Mac/FreeBSD） に対応する優先度マッピング。psutil を使用し、権限不足や未対応 API を安全にスキップして警告ログを出力。

- 研究系ツール（初期実装）
  - src/kabusys/research/factor_research.py（モメンタム等ファクター計算の骨子）
    - DuckDB 接続を受け取り prices_daily / raw_financials から Momentum / Value / Volatility / Liquidity を計算する設計。
    - モメンタム計算 calc_momentum のインターフェースを定義（ファイルは途中まで実装）。

- 運用ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。
    - システム稼働率、注文成功率（Fill/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）を集計。
    - PASS/FAIL 基準（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms）に基づく判定を出力。
    - --from / --to / --db オプション対応。

Changed
- 監視データの取り扱い方針を明確化
  - run_monitoring は環境変数 KABUSYS_ENV にかかわらず本番向けの sqlite_path を使用する（監視データは一元化）。
  - run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB から分離。

Fixed
- .env 読み込みロジックの堅牢化
  - export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどを明示的にサポート。
  - プロジェクトルートが検出できない場合は自動ロードをスキップして安全に振る舞う。

- DB 初期化の冪等化
  - init_monitoring_db を起動スクリプト（実行/監視）で呼び出し、監視用テーブルが存在することを保証（既に存在していても問題ないよう設計）。

Notes / Potential breaking changes
- Monitoring の挙動に関する設計
  - run_monitoring が常に本番 sqlite_path を使用するため、開発中に監視を分離したい場合は別途設定・DB パスの切替が必要です。
- PAPER_FILL_MODE のバリデーション
  - 許容値以外を設定した場合、Settings.paper_fill_mode が ValueError を送出します（起動時に早期検出されます）。
- process_priority / set_cpu_affinity は実行環境の権限に依存します。権限不足時は警告ログを出して処理をスキップします。

Developers
- 各モジュールは外部依存を最小化するよう設計されていますが、一部機能は以下の外部ライブラリを使用します:
  - psutil（process_priority）
  - duckdb（DuckDB 接続）
  - sqlite3（標準ライブラリだが DB ファイル操作で使用）
  - PyYAML（config 検証を有効にする場合）

今後の予定（例）
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の全指標）。
- ExecutionEngine / SystemMonitor の詳細なユニットテスト追加。
- 単体テストを含む CI 設定の充実。

---