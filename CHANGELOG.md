# Changelog

すべての注記は Keep a Changelog の慣例に従います。  
このファイルは、コードベースから推測される変更点・追加機能をまとめた初期リリースの変更履歴です。

フォーマット: [バージョン] - YYYY-MM-DD

## [0.1.0] - 2026-04-18

### Added
- 全体
  - パッケージ初期リリースとして以下の機能群を追加。
  - バージョンはパッケージルートで `__version__ = "0.1.0"` に設定。

- 実行系
  - run_execution: 実際の発注ループを実行する起動スクリプトを追加。
    - プロセス優先度を起動直後に High に設定。
    - 環境に応じて Paper Trading 用 DB（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と分離。
    - BrokerClientFactory により環境に合わせたブローカークライアントを生成（paper_trading 時はモックを利用）。
    - ExecutionEngine をスレッドで起動し、`data/stop_requested.flag` による停止検知機構を実装。
    - 起動時に PID ファイルを書き込む仕組み（`data/execution.pid` を使用）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境に関係なく本番用の sqlite_path を使用。
    - 停止フラグによる安全停止、例外発生時のログ出力と継続動作を実装。
  - tools/paper_verification_report: Paper Trading の検証レポートを生成する CLI ツールを追加。
    - 指定期間の稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）、リスク却下数などを集計・出力。
    - パスや期間をコマンドライン引数で指定可能（デフォルト DB: data/paper_trading.db）。

- 設定関連
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
    - `.env` / `.env.local` の読み込み優先度を実装（OS 環境変数を保護）。
    - 複雑な .env の行解析に対応（`export`、クォート、エスケープ、インラインコメント処理）。
    - Settings クラスで各種設定プロパティを提供（DuckDB/SQLite パス、PID/kill flag パス、閾値、env/log level 判定等）。
    - PAPER_FILL_MODE の妥当性チェック、KABUSYS_ENV / LOG_LEVEL の検証、便利なプロパティ（is_live/is_paper/is_dev）を実装。
  - config_setup.py: .env を対話的に生成・更新するウィザードを追加。
    - 複数の設定項目を対話入力で設定し `.env` を安全に書き出す機能。
    - シークレット項目はマスク表示、確認プロンプト付きで保存。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML があれば中身も検証）等。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/、30日保持）をルートロガーへ設定。
    - LOG_LEVEL / LOG_DIR の解決、既存ハンドラのクリア、ディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度・CPU affinity 設定ユーティリティを追加。
    - psutil を用いて `set_process_priority(level)`（high/normal/low）を実装。対応しない OS や権限不足時は警告でスキップ。
    - `set_cpu_affinity(cpu_count)` によりプロセスの CPU 固定を行える（未指定は無効）。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定・重み付け関数を追加。
    - select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment: セクター集中制限・レジーム乗数を追加。
    - apply_sector_cap（既存保有を基にセクター上限を超える場合に新規候補を除外）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" による乗数、未知値は警告とともに 1.0 にフォールバック）。
  - portfolio.position_sizing: 発注株数計算（等配分/スコア/リスクベース）を追加。
    - lot_size（単元）丸め、1銘柄上限・合計投下資金（aggregate cap）処理、cost_buffer による保守的見積り、スケーリングと残差処理（lot 単位で再配分）を実装。

- リサーチ
  - research.factor_research: ファクター計算モジュール（Momentum / Value / Volatility / Liquidity）を追加（設計と定数のみを含み、計算関数の実装が進行中の形跡あり）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計。

### Changed
- DB/監視の扱い
  - 監視用コード（run_monitoring, run_execution）は DuckDB と SQLite を併用するように組み込み（duckdb_path / sqlite_path を Settings 経由で取得）。
  - Monitoring 初期化処理 init_monitoring_db を起動時に冪等的に呼び出して監視テーブルの存在を保証。

- 設定読み込みの挙動
  - デフォルトの .env 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` を使って無効化可能。プロジェクトルートが判別できない場合は自動ロードをスキップする。

### Fixed
- .env パーサーの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント判定（クォート無しの場合の `#` 扱い）などに対応し、実運用で見られる .env 形式に耐性を向上。

- ポジションサイズ計算の安定化
  - 価格欠損時のスキップ、0 またはマイナス価格への安全処理、合計投下額が available_cash を超えた際のスケーリングと lot 単位での端数処理を修正・実装。

### Documentation / Tooling
- config_setup の対話式ウィザードにより .env 作成手順を分かりやすく案内する仕組みを追加（保存前に内容確認と同意プロンプトあり）。
- validate_config により起動前に設定不備を検知しやすくなった（必須 env の未設定やプレースホルダ検出、YAML パースエラーの検出など）。

### Notes / Behavior
- Paper Trading は本番 DB から完全に分離される設計になっている（`paper_sqlite_path` を利用）。paper 環境では MockBrokerClient の使用が想定される。
- run_monitoring は MONITOR_POLL_INTERVAL（秒）でループ間隔を制御。0 以下や不正入力はデフォルト 60 秒にフォールバックしログに警告を出す。
- process_priority の呼び出しは起動直後に行われる設計で、権限不足等の理由で失敗しても警告ログを出力して続行する。

---

今後の改善候補（コード上の TODO/設計メモから推測）
- portfolio.position_sizing: 銘柄ごとの単元（lot_size）を stocks マスタなどから取得する拡張。
- risk_adjustment.apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価の使用）を検討。
- research.factor_research: ファクター計算関数の完全実装・パフォーマンス最適化。
- ロギング: ファイルハンドラ作成失敗時の診断情報を更に充実させる。

以上が、提供されたコードベースから推測して作成した CHANGELOG.md（Keep a Changelog 準拠）の内容です。必要であれば項目の言い回しや粒度（リリース分割、日付の修正など）を調整します。