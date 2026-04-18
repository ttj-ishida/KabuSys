# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新更新日: 2026-04-18

## [Unreleased]

- 特になし（初期リリースとしてまとめられています）。

## [0.1.0] - 2026-04-18

### Added
- 初期リリース。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV による paper_trading モード対応:
      - paper_trading 時は MockBrokerClient を利用し、専用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
    - 起動時にプロセス優先度を High に設定する仕組みを実装。
    - PID ファイル（data/execution.pid）と停止フラグ（data/stop_requested.flag）による起動／停止制御。
    - RiskManager、OrderManager、Reconciler の組み立てロジックを組み込んだ ExecutionEngine の起動・監視を実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）検出で安全にループを終了。

- 設定・環境管理
  - config.py
    - .env 自動読み込み（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env / .env.local の読み込み順 (OS 環境変数 > .env.local > .env) と、OS 環境変数の保護（上書き禁止）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化サポート。
    - Settings クラスを提供し、各種設定値（DB パス、API トークン、しきい値、env 判定など）をプロパティとして取得可能に。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH などペーパートレード向け設定をサポート。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - シークレット入力、選択肢、デフォルト値、保存前の確認表示を実装。
  - validate_config.py
    - 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パス親ディレクトリ存在チェック、YAML の存在およびパースチェック（PyYAML が存在する場合）を実施。
    - --strict モードで警告を FAIL 扱いにするオプションを提供。
    - 本番環境向けの注意（LINE 通知設定不足、KILL_FLAG_CLEAR_ON_START 設定など）を追加の警告として表示。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout に出す StreamHandler（標準出力）と、日次ローテーション（TimedRotatingFileHandler）を使ったファイル出力をルートロガーに設定。
    - ログレベル・ログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
  - utils/process_priority.py
    - psutil を用いたプラットフォーム横断のプロセス優先度設定（Windows / POSIX の差分吸収）を実装。
    - CPU アフィニティ設定ヘルパー（最初の N コアに固定）を追加。
    - 権限不足等で失敗した場合は警告を出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（スコア降順・同点時の tie-break）select_candidates を実装。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（当日売却予定銘柄の除外、unknown セクター取扱い）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py
    - ポジションサイズ計算 calc_position_sizes を実装。
    - allocation_method による "risk_based" / "equal" / "score" をサポート。
    - 単元株 (lot_size) による丸め、1 銘柄上限/max_utilization、コストバッファを考慮した aggregate cap スケールダウンロジックを実装。
    - スケーリング時の端数配分アルゴリズムで再現性を確保。

- 監視／検証ツール
  - monitoring.monitoring_db の初期化呼び出しを run_monitoring / run_execution の起動時に行い、監視テーブルが存在することを保証（冪等）。
  - tools/paper_verification_report.py
    - ペーパートレード結果の検証レポート生成ツールを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定する閾値を設定（稼働率 99%、成立率 90% など）。
    - 日付フィルタ、DB パス指定オプションをサポート。DB の存在チェックと、テーブル未存在時の障害耐性を実装。

- 研究用モジュール（着手）
  - research/factor_research.py を追加。
    - Momentum / Value / Volatility / Liquidity といったファクター計算設計を実装するための基盤を準備（DuckDB 接続を受け取る設計）。
    - モメンタム計算関数の実装を開始（コード途中まで含む）。

- パッケージメタ
  - パッケージバージョンを __version__ = "0.1.0" として定義。

### Changed
- なし（初期リリースにまとめられています）。

### Fixed
- .env パーサに以下の堅牢化を実施:
  - export PREFIX の除去、クォートあり値のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなし時の '#' をコメントとみなすルールの調整。
  - _load_env_file が読み込み失敗した場合に警告を出力してスキップする安全措置を追加。
- logging_setup: ログディレクトリ作成失敗時にファイルローテーションを無効化して stderr へ警告を出すようにし、起動継続を保証。

### Security
- シークレット扱いの設定項目（J-Quants トークン、kabu API パスワード、LINE トークン）は config_setup ウィザードでマスク表示されるよう配慮。

---

注記:
- この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合は、そちらに基づく更新を推奨します。