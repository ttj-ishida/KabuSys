# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-20

初回リリース。日本株自動売買フレームワーク「KabuSys」のコア機能を追加しました。

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して監視テーブルを初期化。
    - 起動時にプロセス優先度を "high" に設定。
    - duckdb 接続を併用。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、Paper Trading 用 DB（data/paper_trading.db など）に記録して本番 DB と分離。
    - 停止フラグ、実行 PID ファイル（data/execution.pid）対応。バックグラウンドスレッドで engine.run_session を実行し、停止フラグで安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
    - init_monitoring_db による監視テーブルの冪等初期化を実行。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から検出）。
    - .env 読み込み順序: OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントなどに対応。
    - Settings クラスを導入し、J-Quants や kabu API、DB パス、paper trading 用設定、監視閾値、環境／ログレベル判定等のプロパティを提供。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
    - paper_sqlite_path / pid_file_path / kill_flag_path 等のパス取得ユーティリティを提供。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
    - 各設定項目のラベル・説明・デフォルト・選択肢を定義し、既存 .env の読み込み・マスク表示・確認・保存機能を提供。
    - 出力される .env テンプレートは Git にコミットしない旨のコメント付き。

  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在/パース検証（PyYAML がインストールされている場合）を実施。
    - KABUSYS_ENV=live 向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定検出）を追加。
    - --strict モードで警告を失敗扱い（exit 1）にできる。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティを追加。
    - ログレベルとログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみ継続。
    - stdout を使用することでジョブ実行時のリダイレクトを簡素化。

  - utils/process_priority.py
    - プロセス優先度（high/normal/low）をクロスプラットフォームで設定するユーティリティを追加（Windows の優先度クラス、POSIX の nice 値に対応）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - 権限不足や未対応 OS に対しては警告を出し失敗をスキップする設計。

- Execution サブシステム（骨子）
  - execution パッケージの各種コンポーネントを組み立てるロジック（BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等）を統合して起動する構成を追加。RiskConfig によるリスクパラメータ設定や available_cash の初期取得を行う。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの存在を保証（冪等な初期化）。

- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計して検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ、リスク却下数など。
    - P95 計算、期間フィルタ（--from / --to）、DB パスの指定（--db / 環境変数）に対応。
    - デフォルトの合格基準（閾値）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 latency <= 200 ms
    - データ欠損時には N/A を表示し、判定を FAIL とするロジックを導入。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（score 降順、タイブレークに signal_rank）select_candidates。
    - 等重み calc_equal_weights、スコア正規化による calc_score_weights（全スコア 0 の場合は等重みへフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（既存保有のセクターエクスポージャーに基づき新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマップ、未知のレジームは 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - 発注株数を決定する calc_position_sizes を追加。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - risk_based: 許容リスク率、損切り率に基づく単銘柄目標株数計算。
    - equal/score: 重みと利用可能資金から各銘柄のターゲット株数を算出。
    - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
    - aggregate cap を超える場合はスケールダウンし、残余キャッシュで端数配分ロジックを導入。
    - cost_buffer により手数料・スリッページを保守的に見積もる。

- 研究（ファクター計算）モジュール（部分実装）
  - research/factor_research.py（骨子）
    - モメンタム、MA200乖離、ATR、流動性等のファクター計算に関する設計と定数を追加。
    - DuckDB 接続（prices_daily / raw_financials を想定）を受け取り、(date, code) キーの辞書リストを返す方針を実装開始。
    - （ファイル末尾が途中のため一部実装が継続中）

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の注意点 / 動作仕様
- run_monitoring は「監視用」DB として Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用します。環境に依らず監視 DB を共有する設計です。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB とのデータ分離を行います。
- .env 自動読み込みはプロジェクトルート検出に依存します（.git または pyproject.toml）。検出できない場合は自動ロードをスキップします。
- process_priority の設定は権限や OS により失敗する可能性があり、その場合は警告を出して続行します。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化してコンソールのみでのログ出力にフォールバックします。
- research/factor_research は現在一部実装段階のため、完全なファクター計算ロジックは今後のリリースで追加予定。

### 使用例
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db /path/to/paper_trading.db

---

（今後のリリースでは research/factor_research の完全実装、詳細なテストカバレッジ追加、実行エンジン周りの堅牢化・監視アラート機能の強化を予定しています）