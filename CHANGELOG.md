# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
フォーマット: 変更はカテゴリ（Added, Changed, Fixed, Removed, Security）ごとに整理しています。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成と CLI / 実行スクリプトを実装
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合に専用の paper DB（デフォルト: data/paper_trading.db）を使用する仕組みを実装。paper_trading 環境では MockBrokerClient を使用して本番 DB と分離して動作可能。
    - 停止フラグ (data/stop_requested.flag) と実行 PID ファイル (data/execution.pid) を扱うロジックを実装。
    - スレッドでエンジンを起動し、停止フラグ検知時に安全に停止する仕組みを追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` による上書きが可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視データを記録する仕様（意図的な動作）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了処理を実装。
  - config.py
    - 環境変数 / .env の読み込み・管理を提供する Settings クラスを追加。
    - 自動 .env ロード（プロジェクトルート検出: .git または pyproject.toml 基準）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント処理に対応。
    - 各種設定プロパティ（J-Quants トークン、kabu API、DB パス、paper_trading 用設定、監視閾値、環境判定、ログレベルなど）を提供。
  - config_setup.py
    - 対話式 .env ウィザードを追加。主要設定項目の入力支援と .env の生成（.env を誤って Git 管理しない旨の注記を含む）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの存在チェック、config/*.yaml の存在・パース（PyYAML がある場合）などを検証。
    - `--strict` オプションで警告を FAIL 扱いにできる。
  - utils/logging_setup.py
    - 統一ログセットアップユーティリティを追加。
    - コンソール出力は stdout（cron/Task Scheduler でのリダイレクト想定）へ出力。
    - 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をサポートし、ログローテーションと 30 日分保持を実装。
    - LOG_DIR / LOG_LEVEL による設定や、ディレクトリ作成失敗時のフォールバック（コンソールのみ）に対応。
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定ユーティリティを追加（Windows の priority class / POSIX の nice 値を考慮）。
    - set_process_priority(level)（high/normal/low）と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS の場合は警告を出してスキップ。
  - portfolio モジュール（選定・配分・リスク調整・株数算出）
    - portfolio_builder.py: シグナルの候補選定 (select_candidates)、等金額/スコア重み計算 (calc_equal_weights, calc_score_weights) を実装。スコア全てが 0 の場合は等分配へフォールバックして警告を出す。
    - risk_adjustment.py: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数計算 (calc_regime_multiplier) を実装。未知レジームは 1.0 でフォールバック。
    - position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に応じた株数決定ロジックを実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer（コスト保守見積り）などを考慮。
    - portfolio/__init__.py で API をエクスポート。
  - research/factor_research.py
    - ファクター計算の骨格を実装（モメンタム、MA200乖離、ATR、出来高系等を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を集計し、閾値（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）に基づいて PASS/FAIL を判定する機能を提供。
    - 日付フィルタ、P95 計算、DB 存在チェックなどを実装。

### Changed
- ログ出力の既定挙動と管理を統一
  - すべての起動スクリプトで setup_logging() を呼ぶ設計により、コンソール出力（stdout）とファイル出力（ローテーション）を共通化。
- 環境変数ロード順序の明確化
  - OS 環境 > .env.local > .env の順でロードする仕様を実装。既存の OS 環境変数は保護される。

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス、クォート内エスケープ、行内コメントの扱いなどを正しく処理するよう改善。
- ログディレクトリ作成失敗時の挙動を明確化
  - 失敗時はファイルハンドラを無効化し、コンソール出力のみで継続するようしたことで起動の堅牢性を向上。

### Removed
- （このリリースでは削除なし）

### Security
- 機密情報取り扱い
  - config_setup の対話式ウィザードでトークン/パスワード項目を secret として取り扱い、表示時はマスクする仕様を採用。

---

注意:
- 監視（run_monitoring）はコード上で「Monitoring は環境に関わらず本番 sqlite_path を使用する」と明示的に動作しているため、テスト環境や paper_trading 環境と監視 DB を分離したい場合は実行環境の設定やコードの改変が必要です。
- process_priority や CPU affinity 設定は OS 権限に依存します。権限が不足する場合は警告を出してスキップします。
- research/factor_research.py はファクター計算の構成を含むが、関数の実装の一部（ファイル末尾での補完など）が未完の可能性があります。必要に応じて追加実装・テストを行ってください。

（バージョン情報: __version__ = "0.1.0"）