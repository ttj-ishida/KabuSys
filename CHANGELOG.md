# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
履歴は semver を想定しています。

## [Unreleased]
- （現在なし）

## [0.1.0] - 2026-04-18

### Added
- 実行用スクリプトを追加 / 整備
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH のサポート）。
    - BrokerClientFactory でブローカークライアントを抽象化。paper_trading 時は MockBrokerClient を利用。
    - ExecutionEngine の起動 / 停止ループ、PID ファイル（data/execution.pid）管理、停止フラグ監視を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検出で安全にループ終了。
    - 監視（monitoring）については環境にかかわらず本番 sqlite_path を参照する設計。

- 設定管理ツール・CLI を追加
  - config_setup.py: 対話式 .env ウィザードを追加。主要環境変数の初期作成・更新を支援（シークレットのマスク表示、既存値の再利用、保存確認など）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在チェック（PyYAML があればパース検証）を実行。
    - --strict オプションで警告を失敗扱いにできる。

- 環境変数読み込みの改善（config.py）
  - プロジェクトルートの自動探索（.git または pyproject.toml を基準）に基づいて .env / .env.local を自動読み込み。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - .env パーサを拡張し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いの改善に対応。
  - Settings クラスを導入し、アプリ設定（パス、閾値、env 判定、paper_trading 用パス、PAPER_FILL_MODE 等）をプロパティ化して検証を行う。

- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py:
    - stdout（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに統一設定する setup_logging を追加。
    - ログディレクトリ自動作成と、作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度を設定する set_process_priority を追加。
    - CPU affinity を設定する set_cpu_affinity を追加（必要に応じて最初の N コアに固定）。
    - パーミッション不足や未サポート環境時に安全にスキップして警告を出力。

- ポートフォリオ構築関連モジュール（kabusys.portfolio）
  - portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で選抜。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコアが全て 0 の場合は等金額へフォールバックして警告を出す。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に新規候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームは警告後 1.0 でフォールバック）。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づきロット丸め（lot_size）、単銘柄上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer（手数料/スリッページ見積り）を考慮した株数決定ロジックを実装。
    - aggregate スケーリング時に残余キャッシュで fractional 残差に基づいてロット単位で追加割当てを行う再現可能なロジックを実装。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）を解析して検証レポートを出力するスクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg / max / P95）やリスク却下数を算出。
    - P95 計算補助、日付フィルタ（--from / --to）サポート、閾値（稼働率 99%、fill_rate 90% など）に基づく PASS/FAIL 判定を実装。

- research/factor_research.py
  - DuckDB 接続を利用したファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を実装する下地を追加。
  - モメンタムファクター計算（mom_1m / mom_3m / mom_6m / MA200 乖離など）を実行する関数インタフェースを用意（実装の一部が含まれる）。

### Changed
- 監視コンポーネントの DB 運用方針
  - run_monitoring (SystemMonitor): 監視用は環境にかかわらず settings.sqlite_path（デフォルト: data/monitoring.db）を使用する動作を明示。これは監視が常に本番監視 DB を参照する設計方針に基づく。

- ログ設定の既定動作
  - setup_logging にてログレベル解決順やログディレクトリ解決順を明確化。既にハンドラが存在する場合は一度クリアしてから再設定するよう変更。

### Fixed / Robustness
- .env 解析の堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの解釈などへ対応し、意図しないパースやコメント取り扱いによる誤設定を低減。

- 環境変数の妥当性チェック
  - Settings と validate_config にて KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など無効値に対する早期検出と適切なエラーメッセージ・警告を追加。

- 実行時の安全停止 / 例外耐性
  - run_monitoring と run_execution のループで停止フラグを監視し、例外発生時にもループ継続（ログ出力）やリソースクローズを行うようにして安定性を向上。

- ロギング周りのフォールバック処理
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合、コンソールのみで継続し、適切な警告を出すように改善。

### Removed
- （今回のバージョンでは削除項目なし）

### Notes / Breaking changes
- 監視（run_monitoring）は開発環境であっても settings.sqlite_path（デフォルトの監視 DB）を使用するため、開発用に監視 DB を分離したい場合は SQLITE_PATH を明示的に変更してください。
- PAPER_FILL_MODE の不正な値は Settings で ValueError を送出するため、環境変数設定ミスがあると起動時に例外で停止します。config_setup と validate_config を利用して事前に検証することを推奨します。

---

参考: パッケージバージョンは kabusys.__version__ == "0.1.0"。