# CHANGELOG

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
このファイルは、リポジトリ内のコードから推測できる機能追加・挙動・既知の注意点をまとめたものです。

注: バージョン番号は src/kabusys/__init__.py の __version__= "0.1.0" に基づきます。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-21
最初のリリース（推定）。自動売買システムのコアユーティリティ、実行・監視スクリプト、設定管理、ポートフォリオ構築ロジック、検証ツールなどを含む。

### Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の SQLite DB に記録する分離動作を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。停止は data/stop_requested.flag ファイルの存在で検出。
- 設定管理・CLI
  - config.py: .env 自動ロード機能（プロジェクトルートの .env / .env.local）と Settings クラスを実装。必須値チェック用の _require、各種設定プロパティ（DB パス、PID/kill flag、閾値、PAPER_FILL_MODE の検証等）を提供。
    - .env 自動ロードは OS 環境変数を保護（上書き禁止）し、.env.local は優先してロード（既存 OS 環境変数を保護した上で上書き）する。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD`=1 で抑止可能。
  - config_setup.py: 対話式ウィザードで .env ファイルを生成・更新する CLI を追加。複数の項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START など）を考慮。
  - validate_config.py: .env と config/*.yaml を事前検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML 未インストール時は警告）の実装。`--strict` オプションで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 共通ログ設定ユーティリティを追加（stdout 用 StreamHandler と 日次ローテートの TimedRotatingFileHandler）。ログディレクトリ作成のフォールバックや既存ハンドラの一度クリアなどを実装。
  - utils/process_priority.py: Windows と POSIX を透過するプロセス優先度と CPU affinity 設定ユーティリティを追加。失敗時は警告を出し安全にスキップする設計。
- ポートフォリオ構築・リスク管理ロジック
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）と重み算出（等配分・スコア重み）を実装。スコア全てが 0 の場合に等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームはフォールバックし警告を出す。apply_sector_cap は売却予定銘柄をエクスポージャー計算から除外し、"unknown" セクターは上限適用対象外。
  - portfolio/position_sizing.py: 株数計算ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。個別・総合上限、lot_size（単元）丸め、cost_buffer（手数料/スリッページ保守見積）、スケールダウン（available_cash を超える場合の按分）と残差配分ロジックを実装。
  - portfolio/__init__.py: 上記関数をパブリック API としてエクスポート。
- Execution コンポーネント統合
  - run_execution.py は BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立てを行い、ExecutionEngine をバックグラウンドスレッドで実行する。停止フラグ検出時には Engine.stop() を呼び安全に終了する実装。
  - RiskManager の設定（RiskConfig）に初期ポートフォリオ値として broker.get_available_cash() を利用している。
- 監視関連
  - run_monitoring.py は SystemMonitor を初期化し、SQLite（settings.sqlite_path）と DuckDB を接続してポーリングを行う。MONITOR_POLL_INTERVAL の不正値に対するフォールバック処理や例外捕捉（check_once の例外はログに残して継続）を実装。
  - monitoring_db.init_monitoring_db を起動時に呼び出してテーブル存在を保証（冪等）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite データベースから検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定を行う。P95 計算のユーティリティと期間フィルタ機能を実装。
- リサーチ / ファクター計算（部分実装）
  - research/factor_research.py: momentum、MA200 乖離、ATR、ボリューム等のファクター設計を追加。DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照して計算する設計。ファイルは一部未完（末尾が途切れている）で、モメンタム計算関数の続きが必要。

### Changed
- 設定ロードの優先順と振る舞いを明文化
  - OS 環境 > .env.local > .env の優先順で自動ロード。既存の OS 環境変数は保護され、.env.local は既存 OS 変数を上書きしない設計。
- ログ出力の標準化
  - 全起動スクリプトから utils.setup_logging を使用し、stdout と日次ローテーションファイルへ統一的に出力されるように設計。

### Fixed / Robustness
- .env パーサの強化
  - config._parse_env_line はクォート内のバックスラッシュエスケープや inline コメントの扱い、`export KEY=val` 形式対応などを行う堅牢なパーサを実装。
- process_priority と CPU affinity は権限不足や未実装環境に対して例外を吸収し、警告出力で安全にスキップするよう改善。
- ログディレクトリ作成失敗時にファイルハンドラをスキップして stdout ログのみで継続するフェールセーフを実装。

### Documentation / UX
- config_setup.py による初期設定ウィザードで .env のサンプル生成・更新を対話的にサポート。シークレット項目は表示をマスク。
- validate_config.py による事前検証により、起動前に設定不備（未設定の必須環境変数、YAML のパースエラー、危険な本番設定など）を検出可能。

### Notes / Known issues / TODO
- 監視モジュール（run_monitoring）は環境にかかわらず settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計になっているため、開発/ペーパートレード時でも本番用監視 DB を参照する点に注意が必要。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使っているが、監視 DB と Execution DB が分離されるため運用時の DB 取り扱いに注意。
- portfolio/risk_adjustment.apply_sector_cap の価格欠損（price が 0.0 の場合）に対する取り扱いが保守的ではなく、将来的に前日終値や取得原価へのフォールバックが必要（TODO コメントあり）。
- research/factor_research.py は未完の箇所（末尾が切れている）あり。ファクター計算ロジックの完成とユニットテスト追加が必要。
- paper_verification_report の日付は UTC ISO8601 でフィルタリングする点に注意（ローカルタイムとのズレを意識する必要あり）。
- .env の自動ロードはプロジェクトルートが検出できない場合にスキップされる。配布パッケージ利用時に .env を明示的に指定する運用が必要な場合がある。

### Security
- シークレット（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に保存する前提。.env を絶対にリポジトリにコミットしない旨を config_setup.py のコメントで明記。

---

（必要に応じて各項目を実装コミットやチケットと紐付けて更新してください）