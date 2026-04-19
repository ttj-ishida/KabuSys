# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [0.1.0] - 2026-04-19

初回リリース。本リポジトリは日本株自動売買システムの基盤的コンポーネント群を含みます。主要な追加点・設計方針は以下の通りです。

### 追加
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイント。プロセス優先度を "high" に設定してから起動。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）による制御を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値はデフォルトへフォールバック。
    - Monitoring は環境に関わらず本番用 sqlite_path を使用する設計（設定の意図的運用を容易にするため）。

- 設定関連ツール
  - config.py
    - .env 自動読み込み（.env, .env.local）を実装。プロジェクトルート（.git または pyproject.toml を基準）を探索してパスを決定。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを提供し、各種環境変数（DB パス、API トークン、監視閾値、KABUSYS_ENV 等）をプロパティ経由で取得。環境値のバリデーション（有効値チェック）を実装。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の設定をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI。シークレット項目はマスク表示、デフォルト・選択肢をサポート。
  - validate_config.py
    - 起動前検証 CLI。必須環境変数や KABUSYS_ENV、DB パス、config/*.yaml の存在とパース（PyYAML がインストールされている場合）をチェック。
    - --strict を指定すると警告も失敗（exit(1)）扱いにできる。

- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティ。コンソール出力（stdout）と日次ローテートファイル（logs/<app_name>.log）をルートロガーに設定。
    - 既存ハンドラをクリアして二重登録を防止。ログディレクトリは環境変数 LOG_DIR や引数で上書き可能。日次ローテーションで 30 日分保持。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > "INFO"。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - psutil を使い、Windows（priority class）と POSIX（nice 値）を吸収してプロセス優先度を設定するユーティリティ。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS では警告ログを出してスキップ。

- ポートフォリオ構築関連（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates(): BUY シグナルをスコア降順で選抜。
    - calc_equal_weights(), calc_score_weights(): 等金額配分とスコア加重配分。スコア全てが 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中制限を適用（既存保有比率が閾値超過のセクターから新規候補を除外）。"unknown" セクターは適用対象外。
    - calc_regime_multiplier(): 市場レジームに応じた投下資金乗数（bull/neutral/bear -> 1.0/0.7/0.3）。未知のレジームは警告と 1.0 フォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method("risk_based" / "equal" / "score") に基づく発注株数計算。lot_size（単元）対応、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap によるスケーリングと端数処理の実装。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - ペーパートレーディング用検証レポート生成。稼働率、注文成功率（fill_rate）、送信率、P95 レイテンシ等を計算し PASS/FAIL を判定する閾値を定義（例: 稼働率 >= 99%）。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）対応。P95 計算と各種フォールバックを実装。

- 研究用 (research)
  - research/factor_research.py（初期実装）
    - DuckDB 接続を受け取り、Momentum / Value / Volatility / Liquidity 等のファクターを計算する設計。モメンタム計算のための定数定義や計算方針（移動平均日数、ATR、ボリューム窓など）を含む（詳細実装続行中）。

- パッケージ情報
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として定義。

### 変更
- （初回リリースのため、過去バージョンからの変更はありません。）

### 修正
- config._parse_env_line(): export プレフィックス、クォート内のエスケープ文字、インラインコメントの扱いなど実務的な .env パースの堅牢化を実装。
- logging_setup: 既存ハンドラの flush/close とクリアを行うことで多重ハンドラ登録による重複ログ出力を防止。

### 注意事項 / 補足
- デフォルト DB/ログパスはすべてプロジェクト相対（例: data/, logs/）。デプロイ時は環境変数で上書き可能。
- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないこと（config_setup の出力ヘッダにも注意喚起を記載）。
- run_monitoring はドキュメント通り Monitoring の DB に本番 sqlite_path を使用するため、開発環境で分離したい場合は設定を見直してください。
- process_priority や CPU affinity の設定は OS 権限に依存します。権限不足時は警告によりスキップされます。
- validate_config の YAML 内容検証は PyYAML の存在に依存します。CI 環境等で厳密な検証を行う場合は PyYAML を導入してください。

今後の予定（例）
- research/factor_research の各ファクター実装完了とユニットテスト追加
- ExecutionEngine / SystemMonitor 周りの統合テストおよびモックを用いたシミュレーション
- ロギング設定の更なる拡張（セントラルログ集約、JSON 出力オプション等）
- 銘柄ごとの lot_size 等マスタ情報対応による position_sizing の拡張

---
（本 CHANGELOG はソースコードから推測して作成しています。運用方針や実際のリリースノートはプロジェクトのリリースポリシーに従って適宜調整してください。）