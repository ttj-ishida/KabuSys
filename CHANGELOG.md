CHANGELOG
=========

すべての変更は Keep a Changelog の書式に準拠して記載しています。

Unreleased (2026-04-23)
-----------------------

Added
- run_monitoring.py: システム監視プロセス起動スクリプトを追加。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 常に本番用 sqlite_path を用いて監視 DB を初期化する仕様。
  - 停止フラグ（data/stop_requested.flag）検知による安全な終了処理を実装。
- run_execution.py: 実行エンジン起動スクリプトを追加。
  - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。
  - ブローカーファクトリ、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を起動。
  - 停止フラグ検知で Engine.stop() を呼びスレッドを安全に終了。
  - 起動時に PID ファイルを書き込む（execution.pid）設計（pid_file の扱い）。
- config.py: 環境設定読み込み／Settings クラスを追加。
  - プロジェクトルート自動検出（.git / pyproject.toml）。
  - .env 自動ロード機能（.env → .env.local、OS 環境変数を保護）。
  - export KEY=val、クォート、インラインコメント等に対応した .env パーサを実装。
  - 各種設定プロパティを公開（DB パス、paper_trading 関連、監視閾値、log レベル等）。
  - PAPER_FILL_MODE の検証（valid 値チェック）。
- config_setup.py: 対話式 .env 作成ウィザードを追加。
  - 秘密値はマスク表示、既存 .env 読み込み・Enter で再利用可。
  - 最終的に .env を書き出す機能を提供。
- validate_config.py: 起動前設定検証 CLI を追加。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス・config/*.yaml の存在や YAML パース確認（PyYAML が存在する場合）。
  - --strict オプションで警告をエラー扱いに。
  - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）。
- utils/logging_setup.py: ログ設定ユーティリティを追加。
  - stdout 出力（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。
  - LOG_DIR / LOG_LEVEL の解決順、ディレクトリ作成失敗時はファイル出力をスキップするフォールバックを実装。
- utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
  - Windows/Linux(macOS含む)の差分を吸収して set_process_priority, set_cpu_affinity を提供。
  - 権限不足等で設定できない場合はワーニングでスキップ。
- portfolio/*: ポートフォリオ構築モジュールを追加（純粋関数群）。
  - portfolio_builder: 候補選定 (select_candidates)、等重 / スコア重み計算 (calc_equal_weights, calc_score_weights)。
  - risk_adjustment: セクターキャップ適用 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier)。
  - position_sizing: 発注株数計算 (calc_position_sizes)。
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株( lot_size )丸め、aggregate cap によるスケーリング、cost_buffer を考慮した配分ロジックを実装。
- tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプトを追加。
  - 稼働率、注文成功率、送信率、レイテンシ(P95) 等を算出し PASS/FAIL 判定を出力。
  - P95 計算、日付フィルタ (--from/--to)、DB パス指定オプションをサポート。
- research/factor_research.py: ファクター計算モジュールを追加（モメンタム等の計算設計）。
  - DuckDB の prices_daily / raw_financials を利用する設計方針を記載。
- パッケージ情報: __init__.py にバージョン 0.1.0 を定義。

Changed
- logging_setup: ログを stderr ではなく stdout に出す方針を採用（Task Scheduler/cron との互換性考慮）。
- .env 自動ロードの挙動: OS 環境変数を保護しつつ .env/.env.local を適切に上書きする実装に調整。
- run_monitoring/run_execution: 起動処理でプロセス優先度を最初に設定するように統一（set_process_priority("high")）。

Fixed
- .env パーサ: export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの判定等の不備を修正・強化。
- calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックするよう改善（警告ログ付き）。
- position_sizing: aggregate スケールダウン時の端数処理を改善し、残余キャッシュを利用した補正ロジックを導入。

[0.1.0] - 2026-04-23
--------------------

Added
- 初回公開（ベース実装）。
  - 実行・監視ランナー（run_execution, run_monitoring）。
  - 環境設定 (config, config_setup, validate_config) と .env 管理ツール。
  - ロギング・プロセス優先度ユーティリティ。
  - ポートフォリオ構成（候補選定、重み計算、リスク調整、ポジションサイジング）。
  - 実行エンジン周辺（OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立てを想定した起動フロー）。
  - ペーパートレード検証レポートツール。
  - ファクター研究モジュール下地（momentum 等の設計と一部実装）。
  - パッケージメタ情報 (__version__ = "0.1.0")。

Fixed
- ドキュメント文字列（docstring）と CLI ヘルプの整備。
- 一般的なログ・例外取り扱いの追加（起動スクリプトでの例外捕捉とログ出力）。

Notes
- 本リポジトリは「本番/ペーパートレードの DB 分離」「.env の安全な取り扱い」「運用時の監視・停止フラグ」の設計を重視しています。
- 将来的な拡張案（README/ドキュメント等で案内する予定）:
  - stocks マスタに単元株情報を持たせることで銘柄ごとの lot_size をサポートする拡張。
  - position_sizing の価格フォールバック（前日終値等）の導入。