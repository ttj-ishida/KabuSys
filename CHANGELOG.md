CHANGELOG
=========

すべての重要な変更をこのファイルに時系列で記録します。
フォーマットは "Keep a Changelog" に準拠します。
リリース日: YYYY-MM-DD（各リリース行の右側の日付を参照してください）。

- 未リリースの変更は "Unreleased" セクションに記載します。
- 既リリースの項目はバージョンごとに整理します。

Unreleased
----------

- なし（初回リリース）

[0.1.0] - 2026-04-18
-------------------

Added
-----

- 基本アプリケーション構成
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - モジュール構成: data/、strategy/、execution/、monitoring/ などの想定ディレクトリ構成をエクスポート。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定して実行。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を利用して本番 DB と分離された paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用。
    - ExecutionEngine の依存コンポーネント（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）を組み立てて起動。PID ファイルおよび停止フラグ（data/execution.pid / data/stop_requested.flag）に対応。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む。

  - run_monitoring.py
    - SystemMonitor 起動スクリプトを追加。プロセス優先度を "high" に設定して実行。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満/不正値はデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（monitoring 用 DB 初期化処理を実行）。
    - 停止フラグ（data/stop_requested.flag）および KeyboardInterrupt に対応して正常終了。

- 設定管理・セットアップ
  - config.py
    - 環境変数読み込み・管理クラス（Settings）を提供。
    - .env 自動ロード機構（プロジェクトルートの検出: .git または pyproject.toml を基準）。.env と .env.local の読み込みルール（OS 環境変数優先、.env.local は上書き可）。
    - 複数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID/KILL フラグ関連, CPU/MEM/DISK 閾値、ログレベル、環境判定ユーティリティ）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV の妥当性チェック（development/paper_trading/live）。

  - config_setup.py
    - 対話型 .env ウィザードを追加。初回設定や更新時に利用可能。
    - 入力の既存値再利用、シークレットマスキング、選択肢サポート、確認ダイアログを実装。
    - .env 書き出し時にテンプレートヘッダと注意書きを含める（.env を絶対にコミットしない旨の注記）。

  - validate_config.py
    - 起動前に設定を検証する CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML 未インストール時はスキップ）、本番 (live) 用ガード（LINE トークンや Kill Switch 設定の警告）を実装。
    - --strict オプションで警告をエラー扱いにできる。

- ログ・プロセスユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテート、30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリ解決順を定義（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - プラットフォームに依存しないプロセス優先度設定ユーティリティを提供。
    - Windows（psutil の PRIORITY_CLASS）および POSIX（nice 値）の双方に対応。AccessDenied 等の例外は警告ログで無害にスキップ。
    - CPU affinity（最初の N コアに固定）を設定する set_cpu_affinity を提供（cpu_count が None の場合は何もしない）。

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）: score 降順、同点時は signal_rank でタイブレーク。
    - 重み計算: 等金額（calc_equal_weights）、スコア加重（calc_score_weights）。全スコアが 0 の場合は等分配へフォールバックと警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 現有ポジションからセクター別時価を計算し、max_sector_pct を超過するセクターの新規候補を除外。unknown セクターは除外しない（上限対象外）。
    - レジーム乗数（calc_regime_multiplier）: "bull"=1.0, "neutral"=0.7, "bear"=0.3 を返却。未知レジームは 1.0 にフォールバック（警告ログ）。

  - portfolio/position_sizing.py
    - 発注株数計算（calc_position_sizes）: allocation_method に応じた株数決定（"risk_based", "equal", "score"）。
    - risk_based: 許容リスク率、stop_loss_pct に基づくベース株数を計算し単元株（lot_size）で丸め。
    - equal/score: ポートフォリオ価値・重み・max_utilization を考慮して株数を算出、単元株丸め。
    - aggregate cap: 全銘柄の合計コストが available_cash を超える場合にスケーリング。スケーリング後の残差は lot_size 単位でフラクショナル残差の大きい順に追加配分。
    - price 欠損や price <= 0 の場合はスキップし、ログでデバッグ出力。

- Research / Tools
  - research/factor_research.py
    - ファクター計算の基礎モジュールを追加（Momentum, Value, Volatility, Liquidity の計算方針を実装予定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。モメンタム（mom_1m / mom_3m / mom_6m / ma200_dev）計算関数 calc_momentum の実装を開始（スキャン範囲・定数定義を含む）。
    - （注）ファイル末尾で実装途上の可能性あり（未完の箇所あり）。

  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。
    - DB（PAPER_TRADING_SQLITE_PATH / --db）から system_status / trade_logs / risk_logs を参照して指標を算出（稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95））。
    - Pass/Fail 基準を定義: 稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。
    - レポートは標準出力へ整形して表示。DB が存在しない・テーブル欠如時は該当項目を N/A として処理。

- その他
  - monitoring.monitoring_db の初期化ユーティリティを run_* スクリプトで呼び出してテーブル存在を保証（冪等な初期化）。
  - 多くのモジュールで例外ハンドリング・ログ出力を充実させて堅牢性を向上。

Changed
-------

- 初回リリースのため、変更履歴はありません（今後のリリースで記載）。

Fixed
-----

- 初回リリースのため、修正履歴はありません（今後のリリースで記載）。

Known issues / Notes
--------------------

- research/factor_research.calc_momentum の実装が途中の可能性があり、完全実装されていない部分があります（ソース末尾に "start_da" のような不完全な行があります）。ファクター計算周りは要確認。
- position_sizing の price 欠損時の挙動について注記（TODO コメントあり）。価格が欠損するとエクスポージャーが過少見積りされる可能性があり、将来的にフォールバック価格（前日終値等）の導入を検討する必要があります。
- ログディレクトリ作成やプロセス優先度設定は権限に依存するため、環境によっては警告が出る場合があります（例: systemd/jail 環境や Windows の制限）。
- .env 自動ロードはプロジェクトルートの特定（.git / pyproject.toml）に依存するため、配布環境では明示的に環境変数を設定することを推奨します。
- Paper Trading と本番 DB は明確に分離されていますが、設定ミスによる上書き事故を防ぐため .env の管理に注意してください。

Migration / Usage tips
----------------------

- 初回セットアップ:
  1. python -m kabusys.config_setup を実行して .env を作成します。
  2. python -m kabusys.validate_config で設定を検証します（--strict オプションで警告も失敗扱い）。
  3. 実行:
     - 監視ループ: python -m kabusys.run_monitoring
       - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。
     - 実行エンジン: python -m kabusys.run_execution
       - KABUSYS_ENV=paper_trading の場合は paper DB を使用。
     - ペーパートレード検証レポート:
       python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- ログ:
  - デフォルトは logs/ ディレクトリに日次ローテートで出力。環境変数 LOG_DIR で変更可。
  - ログレベルは環境変数 LOG_LEVEL や setup_logging の引数で制御可能。

References
----------

- ソースコード内 docstring とコメントを仕様の主要情報源として CHANGELOG を作成しました。実装の詳細や追加の設定項目については該当モジュールの docstring / ソースコードを参照してください。