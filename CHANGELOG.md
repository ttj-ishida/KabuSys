# Changelog

すべての重大な変更点はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

全般:
- 言語: 日本語で記載。
- バージョンはコードベース中の __version__ を基にしています。

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するためのエントリポイントを実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/ RiskManager/Reconciler の組立てと ExecutionEngine 起動を行う。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する動作をサポート。
    - 停止制御: data/stop_requested.flag を監視し、停止要求があれば安全にエンジンを停止する仕組みを実装。実行中 PID を data/execution.pid に保存。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定する処理を呼び出す。
    - 停止制御: プロジェクトルート/data/stop_requested.flag を検出してループを終了する。

- 設定管理機能を追加
  - config.py:
    - Settings クラスによるアプリケーション設定管理を実装（環境変数経由）。
    - .env 自動ロード（プロジェクトルートに .env / .env.local があれば読み込む）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - 複数の設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / 監視しきい値 / 実行環境など）。
    - PAPER_FILL_MODE 等の値チェックを実装（有効値チェック）。
    - is_live / is_paper / is_dev のショートハンドを追加。
    - 環境変数の未設定時は明示的にエラーを出すための _require 関数を提供。

- 設定ウィザード CLI を追加
  - config_setup.py:
    - 対話式に .env を初期作成・更新するウィザードを実装。
    - シークレット項目のマスク表示、既存 .env の読み込み、保存確認などを提供。

- 設定検証ツールを追加
  - validate_config.py:
    - .env と config/*.yaml の事前検証 CLI を実装。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、YAML のパースチェック（PyYAML があれば実施）など。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict オプションで警告を FAIL 扱いにする機能。

- ポートフォリオ構築関連モジュールを追加
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分ロジック（スコア全てゼロ時は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存ポジションのセクター別エクスポージャー計算と新規候補の除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返すユーティリティ。
  - portfolio/position_sizing.py:
    - calc_position_sizes: weight/candidates/portfolio_value 等から銘柄ごとの発注株数を計算。risk_based, equal, score 各方式をサポート。
    - lot_size（単元）丸め、per-stock 上限、aggregate cap（available_cash を超えた場合のスケールダウンと端数配分）を実装。
    - cost_buffer による手数料・スリッページの保守的見積りを考慮。

- ユーティリティを追加/改善
  - utils/logging_setup.py:
    - ルートロガーの共通設定ユーティリティを実装。
    - stdout（StreamHandler）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
    - 既存ハンドラの二重登録を防ぐため、設定前に既存ハンドラを flush/close して削除。
    - デフォルトログディレクトリは logs/、日次ローテーション 30 日分を保持。
  - utils/process_priority.py:
    - psutil を利用してクロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定する set_process_priority を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（失敗時は警告でスキップ）。
    - 権限不足や未対応 OS に対する弾性処理を実装。

- Paper Trading 検証ツールを追加
  - tools/paper_verification_report.py:
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から指標を集計して検証レポートを生成する CLI を実装。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出し、閾値に基づく PASS/FAIL 判定を行う。
    - P95 計算、日付フィルタ（--from / --to）、DB パスのオーバーライドオプションを提供。

- DuckDB 統合
  - run_execution/run_monitoring など複数箇所で DuckDB 接続を使用するための基礎を追加（Settings.duckdb_path が設定可能）。

- パッケージメタ
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" と定義。

### 変更 (Changed)
- ログ出力
  - ログを stderr ではなく stdout に出力するよう変更（cron/Task Scheduler からのリダイレクトを想定）。

- .env パーサーの強化
  - config.py の .env 自動ロードでのパースが強化され、以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート内でのバックスラッシュエスケープ
    - 行末コメントの基本的取り扱い（クォートあり/なしでの挙動差異を考慮）

### 修正 (Fixed)
- 監視（monitoring）初期化の冪等性
  - run_execution/run_monitoring の起動フローで init_monitoring_db を呼び出し、監視テーブルの存在を保証（既存でも安全に呼べるように）。
- ポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL に不正な値（0 以下や非数）が指定された場合、デフォルト（60 秒）にフォールバックして警告を出すように実装。time.sleep に渡す不正値による例外を防止。

### 注意点 / 想定運用上の注意 (Notes)
- run_monitoring のドキュメントにあるとおり、Monitoring 系は KABUSYS_ENV に関わらず（本実装では） production 用の sqlite_path を使用する旨が記載されています。運用時は sqlite_path の指し先に注意してください。
- KABUSYS_ENV=live の場合、validate_config にて LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定値に対する警告が出ます。本番では慎重に設定してください。
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも警告を記載）。
- process_priority / CPU affinity の設定は権限に依存します。権限不足時は警告を出して処理をスキップします。

### 既知の未完事項 (Known issues / TODO)
- research/factor_research.py はファクター計算の骨格が含まれているものの、ファイルの末尾が未完（途中で切れている）です。ファクター計算ロジックの完成・テストが必要です。
- position_sizing の price 欠損時の挙動について注記（price=0 の場合エクスポージャー過少推定となる可能性）。将来的にフォールバック価格を導入する余地あり（TODO コメントあり）。
- 一部モジュールは外部依存（psutil, duckdb, PyYAML 等）により、環境にない場合は機能制限や警告が発生します。導入時に依存関係の確認を推奨します。

---

今後のリリースでは、research モジュールの完成、各種ユニットテストの追加、並列性・性能改善、より細かな監視アラート/通知機能（LINE 連携の実装）などが想定されます。