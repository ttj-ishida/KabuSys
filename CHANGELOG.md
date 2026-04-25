# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルは、コードベースから推測される主要な追加・仕様をまとめたものです。

## [0.1.0] - 2026-04-25

### 追加
- 初期リリース（パッケージバージョン: 0.1.0）
- コア設定・環境変数管理
  - Settings クラスを提供。環境変数から各種設定を取得（KABUSYS_ENV / LOG_LEVEL / DUCKDB_PATH / SQLITE_PATH など）。
  - .env 自動読み込み機能を実装（プロジェクトルートの .env, .env.local を読み込み、OS 環境変数を保護）。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパースはシングル・ダブルクォート、エスケープ、コメント処理などに対応。
  - PAPER_FILL_MODE（paper trading のフィルモード）に対する入力検証（有効値: "instant", "partial", "never", "reject"）。
  - paper_trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を分離。

- 起動スクリプト / デーモン的プロセス
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用（Mock）ブローカークライアントを使用し、本番 DB と分離して data/paper_trading.db を用いる。
    - プロセス優先度を High に設定（set_process_priority を使用）。
    - 停止フラグ（data/stop_requested.flag）検出により安全に停止。
    - 実行時 PID を data/execution.pid に記録（pid_file を使用）。
    - 主要コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててスレッドで実行。
    - duckdb と sqlite 接続を確立し、起動終了時にクローズ。
  - run_monitoring.py: SystemMonitor（監視）起動スクリプトを追加。
    - 環境に関係なく本番 sqlite_path を用いて監視テーブルを初期化。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - stop flag 検出でループを終了。KeyboardInterrupt をハンドリングして正常終了。
    - duckdb 接続を使用。

- モジュール: 監視 / 実行の DB 初期化
  - init_monitoring_db（監視テーブルの初期化）を呼び出すことで、監視テーブルの存在を保証（冪等）。

- CLI 支援ツール
  - config_setup.py: 対話式の .env 設定ウィザードを追加。
    - J-Quants トークンや kabu API パスワードなどの必須項目や、ログレベル、DB パス等を対話的に設定・保存可能。
    - .env 出力テンプレートは Git へのコミット禁止注記を含む。
  - validate_config.py: 起動前に設定の整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証を実行。
    - KABUSYS_ENV=live の場合に追加の警告（LINE トークン未設定や Kill Flag の自動クリア設定など）を出力。
    - --strict フラグで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）＋ TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリ解決順: 引数 > LOG_DIR 環境変数 > デフォルト "logs/"。作成失敗時はファイル出力をスキップしてコンソールのみ動作。
    - ログレベル解決順: 引数 > LOG_LEVEL 環境変数 > "INFO"。
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加。Windows と POSIX 系で適切に値をマッピングし、権限不足や未対応 OS ではワーニングでスキップ。
    - CPU affinity 設定用の set_cpu_affinity(cpu_count) を追加（設定に失敗した場合はワーニングでスキップ）。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - 候補選定 select_candidates（score 降順、signal_rank によるタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコア 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限検査と候補除外（unknown セクターは除外対象外）。当日売却予定銘柄はエクスポージャー計算から除外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（既定値: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告して 1.0 フォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。
    - 単元株（lot_size）で丸め、max_position_pct（1銘柄上限）や max_utilization（投下資金上限）を考慮。
    - aggregate cap 超過時はスケーリングして、残余キャッシュを考慮して単元単位で追加配分するロジックを実装。
    - price が欠損または 0 の場合はスキップする挙動。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート作成ツールを追加。SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト: data/paper_trading.db）を読み、稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均/最大/P95）などを算出して PASS/FAIL を判定。
    - デフォルト閾値: 稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 レイテンシ <=200ms。
    - P95 計算、期間指定 (--from / --to)、DB 指定 (--db) に対応。
    - テーブルが存在しない場合は操作を安全にスキップ（OperationalError をハンドリング）。

- リサーチ / ファクター計算（開発中）
  - research/factor_research.py:
    - Momentum / Value / Volatility / Liquidity に関するファクター計算モジュールの骨格を追加。DuckDB の prices_daily / raw_financials テーブルを参照して計算する設計。
    - 主要定数（MA、ATR、期間等）と calc_momentum のインターフェースが定義されている（実装は続きがある模様）。

### 変更
- なし（初期リリース）

### 既知の注意点（挙動・制約）
- run_monitoring は「環境にかかわらず本番 sqlite_path を使用」するため、開発環境で監視 DB を分離したい場合は設定に注意が必要。
- process_priority の設定は OS 権限に依存し、権限不足時はワーニングを出してスキップする。
- portfolio.risk_adjustment.apply_sector_cap は price_map に価格欠損があると既存エクスポージャーを過少に評価する可能性があり、将来的にフォールバック価格を使う余地がある（TODO コメントあり）。
- research モジュールの一部関数は実装が完了していない可能性がある（ファイル末尾が途中で切れている）。

### セキュリティ
- .env ファイルには機密情報（API トークン等）を含むため、.env は絶対に Git などにコミットしない旨の注意書きを出力する仕様。

---

今後のリリースでは、下記が追加されることが期待されます（コードの TODO / 未完事項からの推測）:
- research/factor_research の完全実装（ファクター計算ロジックの完成）
- ExecutionEngine / SystemMonitor 等の細部テストケース追加・堅牢化
- 各種エラーハンドリングの拡張とログ出力改善
- 銘柄ごとの単元サイズや手数料モデルを考慮した position sizing の拡張

（本 CHANGELOG は与えられたコードベースから推測して作成しています。実際のコミット履歴とは差異がある場合があります。）