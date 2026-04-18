# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

- リリース日付はコミット時のソース内容から推定しています。
- 記載内容はコードベースの実装から推測してまとめたものです。実際の変更履歴やリリースノートと差異がある場合があります。

## [Unreleased]
- （現在のコードベースでは次回リリース向けの未確定変更は特に検出できません）

## [0.1.0] - 2026-04-18

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 実行用スクリプト / デーモン制御
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH` / data/paper_trading.db）を使用し、本番 DB と分離する仕組みを実装。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、ExecutionEngine を別スレッドで起動する。
    - 停止用フラグ（data/stop_requested.flag）検出時の安全な停止処理（engine.stop()）を実装。
    - 実行 PID を data/execution.pid に出力する設計（pid_file パスを引数で渡す）。

  - run_monitoring.py
    - SystemMonitor（監視ループ）の起動スクリプトを追加。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値は警告ログを出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用の `sqlite_path`（監視 DB）を使用する挙動と明記。
    - 停止用フラグ（data/stop_requested.flag）検出でループ終了、KeyboardInterrupt での終了処理、接続クローズ処理を実装。

- 環境変数 / 設定管理
  - config.py
    - `.env` ファイルと `.env.local` の自動読み込みを実装（OS 環境変数を優先し、上書き挙動に保護付き制御あり）。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - `.env` のパースは `export KEY=val`、クォート値、インラインコメントの扱いなどに対応するロバストな実装。
    - Settings クラスに各種設定プロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、paper_trading 用パス、監視閾値、ログ・環境判定ヘルパー等）。
    - `paper_fill_mode` など一部環境変数は値検証（有効値チェック）を行い、不正値の場合は例外を送出。

  - config_setup.py
    - 対話式ウィザードで `.env` を生成・更新する CLI を追加。
    - シークレット項目はマスク表示、選択肢・デフォルトの提示、既存 `.env` の読み込みと Enter での再利用に対応。
    - 生成される `.env` はヘッダ注釈付きで安全に書き出し。

  - validate_config.py
    - 起動前に設定（環境変数、config/*.yaml）の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス（親ディレクトリ存在）確認、config/*.yaml の存在確認と PyYAML があればパース検証を実施。
    - `--strict` フラグで警告を失敗扱いにできる。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を実装。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear とフォールバック挙動含む）。
    - 未知セクター・価格欠損に関する挙動と将来の拡張 TODO を注記。

  - portfolio/position_sizing.py
    - 重み・候補・現金・価格を受け取り発注株数を計算する calc_position_sizes を実装（allocation_method: risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer（手数料・スリッページ見積り）反映、残差の公平配分ロジックを実装。
    - price 欠損時のスキップや既存保有との差分計算を適切に行う。

- 監視・レポートツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計して判定（PASS/FAIL）を出力。
    - デフォルト DB は `PAPER_TRADING_SQLITE_PATH` 環境変数または data/paper_trading.db。
    - P95 計算ロジックや日付フィルタの取り扱い、閾値定義を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトから使える統一的ロギング設定を実装。
    - コンソール出力は stdout を使用、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を logs/<app>.log に出力、30 日分保持。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラのクリーンアップ実装。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定（set_process_priority）を実装。
    - CPU affinity を設定する set_cpu_affinity を実装。許可エラーや未対応 OS の場合は警告を出してスキップ。
    - 権限不足時に安全にフォールバックするよう例外を捕捉してログ出力。

- リサーチ（初期実装）
  - research/factor_research.py
    - ファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity を想定）。
    - calc_momentum のスケルトン（1M/3M/6M リターンや MA200 乖離計算）を実装開始（ファイル末尾は一部未完のセクションあり）。

### Changed
- なし（初回リリースのため変更履歴はなし）。

### Fixed
- なし（初回リリースのため修正履歴はなし）。

### Known issues / Notes
- factor_research.calc_momentum はファイル末尾で未完の箇所（ソースが途中で切れている）を含みます。実運用では追加実装が必要です。
- portfolio.risk_adjustment.apply_sector_cap は price が 0.0（欠損）時にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値等のフォールバック価格導入が検討されています（TODO コメントあり）。
- run_monitoring の挙動として「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」点は運用上の注意点です。テスト環境でも監視 DB を分離したい場合は実装や環境変数設計を見直してください。
- process_priority / set_cpu_affinity は権限や OS によって失敗する可能性があるため、実行環境での動作確認を推奨します。

---

（以上）