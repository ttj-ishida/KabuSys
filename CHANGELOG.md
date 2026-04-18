# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このファイルは主にリポジトリに含まれるコードから推測して作成した初回リリース向けの変更履歴です。

なおバージョンはパッケージ定義 (src/kabusys/__init__.py) の __version__ に合わせて記載しています。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション骨組みを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV に応じて DB を分離:
      - paper_trading 環境では PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
      - その他は通常の sqlite_path（デフォルト: data/monitoring.db）を使用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - Engine を別スレッドで起動し、data/stop_requested.flag による停止フラグ検知で安全停止。
    - 実行 PID を data/execution.pid に記録する仕組み（設定可能）。
    - DuckDB を分析用 DB として接続。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用（監視テーブルを初期化）。
    - data/stop_requested.flag による停止検知。
    - プロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml から検出して .env, .env.local を読み込む）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 句、クォート、エスケープ、インラインコメント等に対応する堅牢な実装。
    - 必須環境変数取得用の _require と Settings クラスを提供。
    - 各種設定プロパティ:
      - J-Quants / kabuAPI / LINE トークン等
      - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - PAPER_FILL_MODE（instant/partial/never/reject の検証）
      - 監視に関する閾値（CPU/MEM/DISK）や PID/KILL フラグパス
      - KABUSYS_ENV（development|paper_trading|live）の検証、LOG_LEVEL 検証

  - config_setup.py
    - 対話式ウィザードによる .env の初期作成・更新機能。
    - 各項目の説明とデフォルト提示、シークレットマスク表示、.env 書き出し機能を提供。
    - 出力ファイルは .env（デフォルト）で、書式・ヘッダコメントを付与。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の存在・基本チェックを行う CLI。
    - --strict モードで警告もエラー扱いにできる。
    - PyYAML が存在する場合は YAML のパース検証を行う（未インストール時はスキップし警告）。
    - live 環境向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定等の警告）。

- ユーティリティ
  - utils/process_priority.py
    - psutil を用いたプロセス優先度設定ユーティリティ。
    - Windows/Linux(macOS等POSIX) を吸収する実装。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count: int|None) を提供。
    - 権限不足や未対応環境では安全にフォールバックして警告ログを出す。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で上位 N 件抽出。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率に基づく配分（合計スコアが 0 の場合は等配分にフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限を評価して候補から除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未定義は警告のうえ 1.0 フォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes:
      - 複数の配分方法に対応（"risk_based", "equal", "score"）。
      - 設定可能なパラメータ: risk_pct, stop_loss_pct, max_position_pct, max_utilization, lot_size, cost_buffer 等。
      - 単元株（lot_size）で丸め、per-position と aggregate の上限を考慮したスケーリング（利用可能現金を超える場合のスケールダウンと残余配分アルゴリズムを実装）。
      - 価格欠損時にスキップするロバスト設計。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily テーブルからモメンタム・ボラティリティ等のファクターを計算する純粋関数を実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - calc_volatility: ATR, 相対 ATR, 20日平均売買代金等を計算（ウィンドウ考慮）。（ファイル途中まで実装あり）

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。
    - 指標: 稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（avg/max/P95）等を算出。
    - デフォルト判定基準を定義（稼働率 >=99%, fill_rate >=90%, send_rate >=95%, P95 <=200ms）。
    - 日付フィルタ (--from/--to)、--db で DB パス指定可能。
    - データ不足やテーブル未存在時の耐障害性（OperationalError を捕捉して N/A を返す）。

- DB 初期化
  - monitoring/monitoring_db.py（参照して init_monitoring_db を呼び出す実装）
    - 監視用テーブルが存在しない場合に初期化する処理（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数のデフォルトファイル（.env）は自動生成スクリプトで注意喚起コメントを出力（.env を Git にコミットしないよう明記）。
- 機密情報は対話ウィザードでマスク表示するが、ファイル保存時はプレーンテキストで .env に書き込まれるため取り扱いに注意。

---

補足（設計上の注記・既知のポイント）
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）はログ警告を出しデフォルト 60 秒にフォールバックする。
- run_monitoring は監視 DB に関して常に本番 sqlite_path を使う（環境に依存しない）。
- run_execution は paper_trading 環境では paper_sqlite_path を使い、発注記録を本番 DB と分離している。
- process_priority の設定は OS 権限やプラットフォーム差（Windows と POSIX 系）に依存するため、失敗時は警告を出してスキップする実装。
- portfolio の position sizing は lot_size（単元）丸め、aggregate スケールダウン、残余配分ロジックを備え、現金不足時に安定した配分を試みる。
- validate_config により起動前に設定不備を検出できるため、本番移行前に利用することを推奨。

もし追加でリリースノートの粒度（コミット別、モジュール別の詳細な差分、既知のバグリスト等）を増やしたい場合は、その旨を伝えてください。コード差分やコミットログがあればより正確な CHANGELOG を生成できます。