# CHANGELOG

この CHANGELOG は「Keep a Changelog」フォーマットに準拠しています。  
このファイルは、コードベースの内容から推測して作成した初期リリースの変更履歴です。

※ 日付はリポジトリのスナップショットに基づく想定日です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-17

### Added
- 基本バージョン情報を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`

- 設定管理
  - 環境変数および .env の自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml）。
  - .env パースの堅牢化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理）。
  - OS 環境変数を保護する仕組み（自動ロード時の上書き制御）。
  - Settings クラスを提供し、アプリケーション設定（DB パス、API トークン、環境フラグ、しきい値等）をプロパティ経由で取得可能に。

- 設定ユーティリティ / CLI
  - 対話式ウィザード `kabusys.config_setup` を実装し .env の初期作成・更新を支援。
    - 標準項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START など）をサポート。
    - シークレット項目はマスク表示。
  - 設定検証ツール `kabusys.validate_config` を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML あれば）パースチェックを実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行系 / 監視
  - Execution エントリポイント `run_execution.py`
    - ExecutionEngine 起動用のスクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合、専用の paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に分離して運用（MockBrokerClient を利用する想定）。
    - 起動時にプロセス優先度を High に設定。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
    - エンジンの PID 管理用ファイル (`data/execution.pid`) をサポート。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit 等）を定義、初期 portfolio value を broker.get_available_cash() から取得。
  - Monitoring エントリポイント `run_monitoring.py`
    - SystemMonitor のポーリングループを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒、0 以下の値はデフォルトにフォールバックして警告を出す）。
    - 監視は環境にかかわらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用して監視テーブルを初期化。
    - 停止フラグ検知でループ終了、KeyboardInterrupt に対するクリーンな終了処理を実装。

- ポートフォリオ構築関連（純粋関数群）
  - kabusys.portfolio モジュール
    - 選定: select_candidates（スコア降順、タイブレークに signal_rank を使用）
    - 重み計算: calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等分配にフォールバック）
    - リスク調整: apply_sector_cap（セクター集中上限、当日売却予定銘柄の除外、"unknown" セクターは適用除外）、calc_regime_multiplier（regime に応じた乗数定義、未知レジームはフォールバック）
    - 株数決定: calc_position_sizes（risk_based、equal、score の各配分方法、lot_size 単位で丸め、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積り）

- リサーチ / ファクター計算
  - kabusys.research.factor_research を追加
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルを参照してファクター（Momentum: 1M/3M/6M、MA200 乖離、Volatility: ATR20、流動性指標等）を計算する関数を実装。
    - 計算に必要なスキャン範囲・窓幅を定義し、データ不足時は None を返す挙動を明示。

- ユーティリティ
  - kabusys.utils.process_priority によるプロセス優先度制御と CPU affinity 設定を追加
    - Windows（HIGH_PRIORITY_CLASS 等）および POSIX（nice 値）をサポート。未対応 OS はスキップ。
    - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。
    - 実行権限不足時には警告を出してスキップする堅牢な実装。

- ツール
  - kabusys.tools.paper_verification_report を追加
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から統計を集計して検証レポートを出力する CLI。
    - 指標: 稼働率、注文成功率（Filled / Created）、送信率（Sent / Created）、リスク却下数、レイテンシ（avg/max/P95）。
    - パス/フェイル基準値を定義（稼働率 >= 99%、fill_rate >= 90% 等）し、PASS/FAIL を判定可能。
    - 日付フィルタ（--from, --to）と --db オプションをサポート。

### Changed
- .env の自動読み込み順を明確化
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
- config_setup による .env 出力テンプレートを追加
  - 生成される .env にヘッダとセクションコメントを付与（Git コミット禁止の注意喚起含む）。
- validate_config において、PyYAML 未インストール時は YAML 検証をスキップして警告を出すように変更。

### Fixed / Robustness
- .env 行パーサーの改善により以下を正しく扱えるように
  - export プレフィックス付き行、引用符内のバックスラッシュエスケープ、インラインコメントの扱い（スペースで始まる # のみコメントとみなす）。
- MONITOR_POLL_INTERVAL の不正値（非整数、0 以下）に対してデフォルトへフォールバックし警告を出力する安全策を実装。
- SQLite / DuckDB コネクションの確実なクローズ処理（finally ブロックや main の終了処理にて実施）。
- プロセス優先度・CPU affinity 設定で権限不足や未対応環境時に例外を吐かず警告でスキップするように。

### Known issues / Notes
- Portfolio の position sizing は単元株（lot_size）を共通で扱う実装。将来的に銘柄別 lot_size を導入する余地あり（TODO が記載）。
- apply_sector_cap は price_map が欠損（0.0）だとエクスポージャーが過少見積りされる可能性があり、前日終値等のフォールバック実装がコメントで示されている。
- Paper Trading モードでは MockBrokerClient を想定しているが、実際の Mock の実装や挙動（fill_mode の詳細）は別モジュールの実装依存。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合危険（validate_config で警告）。

### Security
- 機密情報（J-Quants トークン、kabu API パスワード等）は .env に保存する設計になっているため、.env を Git 管理しないよう .env テンプレートに注意喚起を出力。

-- end

（この CHANGELOG はコードの解析に基づく推測で作成しています。実際の変更履歴やリリースノートが存在する場合はそれに従ってください。）