CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
形式は「Keep a Changelog」に準拠しています。
（初回リリースはコードベースから推測して作成しています）

Unreleased
----------

- なし

0.1.0 - 2026-04-25
------------------

Added
- 初回公開: KabuSys 基本モジュール群を実装
  - パッケージバージョン: __version__ = "0.1.0"
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用して本番 DB と分離（デフォルトで data/paper_trading.db を使用）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag を検知してセッションを停止、実行中 PID を data/execution.pid に保存（Engine 側で使用）。
    - DuckDB/SQLite 接続の初期化および監視テーブルの冪等な初期化を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視データは一元管理）。
    - 停止フラグ file による安全停止と KeyboardInterrupt ハンドリングを実装。
- 設定管理
  - config.py
    - Settings クラスを実装し、環境変数を型付で取得（J-Quants、kabu API、DB パス、監視閾値など）。
    - .env 自動ロード機能:
      - プロジェクトルートを .git / pyproject.toml で探索して .env / .env.local を自動読み込み（OS 環境変数は保護）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、各種閾値やフラグをプロパティで提供。値検証を実施。
- 設定ユーティリティ（CLI）
  - config_setup.py
    - .env の対話式ウィザードを実装（キー一覧、デフォルト、シークレット入力、保存機能）。
    - 既存 .env の読み込みと更新、.env ファイルの書式整形を行う。
  - validate_config.py
    - 起動前検証 CLI を実装（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選定（score 降順、タイブレークに signal_rank）と候補上限の取得。
    - 等金額配分（calc_equal_weights）およびスコア加重配分（calc_score_weights）。全スコアが 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）: 既存保有に基づき上限を超えるセクターの新規候補を除外。
    - レジーム乗数（calc_regime_multiplier）: market regime に応じた投下資金倍率（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - 発注株数計算（risk_based / equal / score の allocation_method）、単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケーリング処理を実装。
    - 手数料・スリッページ見積り（cost_buffer）を考慮した保守的計算。
- リサーチ（ファクター計算）
  - research/factor_research.py
    - DuckDB 接続を受けてモメンタム等のファクター計算を行う基盤を実装（モメンタム／MA200 乖離等、営業日ベースの窓処理を想定）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を実装。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出し、閾値（稼働率 99% 等）による PASS/FAIL 判定を出力。
    - DB パスは --db または PAPER_TRADING_SQLITE_PATH で指定可能。
- 監視 DB 初期化
  - monitoring/monitoring_db と SystemMonitor （参照されるが別モジュールに実装）を起動スクリプトから呼び出して監視テーブルを保証（冪等に初期化）。
- ユーティリティ
  - utils/logging_setup.py
    - 共通のロギング初期化関数 setup_logging を実装。
    - stdout への StreamHandler と 日次ローテーションの TimedRotatingFileHandler（30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップし、コンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（nice/priority class）を設定するユーティリティを実装。
    - CPU affinity を最初 N コアに固定する関数 set_cpu_affinity を提供。
    - psutil の例外（権限不足等）は警告ログに落としてスキップ。
- その他
  - パッケージエクスポート: portfolio モジュールをトップレベルでまとめてエクスポート。

Changed
- 初版のため該当なし（初回実装）。

Fixed
- 初版のため該当なし。

Known issues / Notes
- research/factor_research.py はモメンタム等の計算関数を含むが、ファイル末尾が途中で切れているため一部実装が未完の可能性あり（今後追加実装が必要）。
- apply_sector_cap の価格欠損時の挙動について注記あり（price=0.0 による過少見積り）。将来的なフォールバック価格実装が望まれる。
- Process priority / CPU affinity の設定は OS 権限に依存するため、失敗時は警告を出して続行する設計。
- .env 自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml）。検出できない場合は自動ロードをスキップ。

References
- 実行方法の例:
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Execution 起動: python -m kabusys.run_execution
  - Monitoring 起動: python -m kabusys.run_monitoring
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]

セキュリティ
- なし（初版公開時点）

--- 
（この CHANGELOG は与えられたコードの内容から推測して作成しています。実際のコミット履歴がある場合はそちらに合わせて更新してください。）