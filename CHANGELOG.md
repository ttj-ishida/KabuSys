CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
バージョン番号はパッケージの __version__ に合わせています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-22
--------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本実装を追加。
  - 実行/監視スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを実装。
      - KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を分離して使用（data/paper_trading.db、設定は PAPER_TRADING_SQLITE_PATH）。
      - BrokerClientFactory によるブローカークライアント生成。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動。
      - 実行中の停止は data/stop_requested.flag により制御。PID ファイル管理（data/execution.pid）。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番用 sqlite_path を使用する設計。
      - 停止フラグ（data/stop_requested.flag）検知で安全に終了。
  - 設定管理
    - config.py
      - .env 自動ロード（.env / .env.local）機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
      - .env パース機能を実装（export プレフィックス、クォート・バックスラッシュエスケープ、インラインコメント処理に対応）。
      - Settings クラスを提供し、各種設定（DB パス・API トークン・閾値・環境種別ほか）をプロパティで取得可能。
      - PAPER_FILL_MODE 等の値検証を実装。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
    - config_setup.py
      - .env を対話的に作成/更新するウィザード CLI を実装（項目: KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE など）。
  - 設定検証
    - validate_config.py
      - .env と config/*.yaml の存在・基本妥当性をチェックする CLI を実装。
      - --strict オプションで警告をエラー扱いに出来る。
      - PyYAML 未インストール時は YAML 検証をスキップして警告を出力。
  - ロギング・プロセス管理ユーティリティ
    - utils/logging_setup.py
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーへ設定するユーティリティを追加。
      - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力を無効化して続行。
    - utils/process_priority.py
      - Windows/Linux/macOS 間の差分を吸収するプロセス優先度設定ユーティリティを追加。
      - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応プラットフォームは警告でスキップ。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て0の場合は等配分へフォールバック。
    - portfolio/risk_adjustment.py
      - セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックで 1.0。
    - portfolio/position_sizing.py
      - 発注株数算出ロジック（risk_based / equal / score）を実装。単元株（lot_size）での丸め、per-position および aggregate の上限制御、cost_buffer を考慮したスケーリングをサポート。
  - リサーチ
    - research/factor_research.py（ファクター計算基盤）
      - Momentum, Value, Volatility, Liquidity 等の計算方針と DuckDB での計算インターフェースを記述（prices_daily / raw_financials を参照）。
      - （ファイルの一部は実装継続を示唆するコメントあり）
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用検証レポート生成 CLI を実装。期間フィルタ（--from/--to）と DB パス指定（--db / 環境変数）をサポート。
      - システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を行う。
      - デフォルトの合格閾値をソースに定義（稼働率 >=99%、成功率等）。
  - パッケージ初期化
    - kabusys/__init__.py にバージョン 0.1.0 を追加。

Changed
- （初期リリースにつき変更履歴は無し）

Fixed
- （初期リリースにつき修正履歴は無し）

Security
- （なし）

注記 / 既知の制約と TODO
- .env の自動ロードはプロジェクトルートが検出できない場合スキップされる（配布後の実行環境安全化）。
- config._parse_env_line はクォート内のバックスラッシュエスケープを処理するが、複雑な .env 構文全般を網羅していない可能性あり。
- portfolio.position_sizing の価格欠損（price が 0.0）の場合、エクスポージャーや発注量計算が過少見積りされる点は TODO コメントでフォールバック価格検討が示されている。
- research/factor_research.py はファイル末尾で実装が途切れている（継続実装が必要）。

参考
- 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時の注意点は validate_config の live ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の設定）を参照してください。

---