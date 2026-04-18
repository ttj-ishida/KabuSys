CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当する場合に記載

なお、変更内容はソースコードから推測して記載しています。

Unreleased
----------

（現時点の未リリース変更はありません）

0.1.0 - 2026-04-18
-----------------

Added
- 初期公開: KabuSys の基礎機能群を追加
  - パッケージ初期バージョンを src/kabusys/__init__.py に定義（__version__ = "0.1.0"）。
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB を使用し、MockBrokerClient を選択する仕組みを導入。停止フラグ（data/stop_requested.flag）検知・PID ファイル管理・デーモンスレッドでのエンジン実行を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き機能を実装。監視は環境にかかわらず本番用 sqlite_path を使用する仕様に明示。
- 設定管理・ウィザード・検証ツールを追加
  - config.py: 環境変数・.env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。.env と .env.local の優先度ルール、quoted/escaped 文字列のパース、必須環境変数取得用ヘルパなど。
  - config_setup.py: .env を対話式に作成・更新するウィザード CLI を追加（--env-file オプション）。機密項目はマスク表示、デフォルト値や選択肢のサポート、保存確認を実装。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML のパース検証、--strict オプションで警告もエラー扱いにできる。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py: ルートロガーに対して stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定するユーティリティを追加。ログディレクトリ自動作成、LOG_DIR / LOG_LEVEL の解決、ファイルハンドラ作成失敗時はコンソール出力にフォールバック。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定と CPU affinity 設定を追加。Windows と POSIX 系を吸収する実装で、権限不足や未対応環境では警告を出して処理をスキップするフォールバックを実装。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存）
  - portfolio/portfolio_builder.py: シグナル選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。スコアが全て 0 の場合のフォールバックを含む。
  - portfolio/risk_adjustment.py: セクター集中除外 apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を実装。レジーム不明時のフォールバックやログ出力あり。
  - portfolio/position_sizing.py: allocation_method（"risk_based", "equal", "score"）に応じた株数算出ロジックを実装。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer を考慮した保守的見積りなどを実装。
- Paper Trading 検証用レポートツールを追加
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポート出力する CLI を追加。--from / --to / --db オプションをサポート。判定閾値（稼働率 99% 等）と PASS/FAIL 判定を組み込み。
- research/factor_research.py: ファクター計算モジュールを追加（モメンタム / ATR / Value 等の設計・定数を定義）。DuckDB 接続を受けて prices_daily / raw_financials を参照する方針を実装。モメンタム計算関数の雛形が含まれる（実装途中の可能性あり）。
- DB 初期化ユーティリティ
  - monitoring/monitoring_db.py からの init_monitoring_db 呼び出しを各起動スクリプトで行い、監視テーブルの存在を冪等に保証。

Changed
- ログ出力の挙動を統一
  - setup_logging() が stdout を使うように明示（cron/Task Scheduler からの運用を考慮）。
- .env 読み込みポリシー
  - OS 環境変数を保護する protected 機構を導入（.env/.env.local の読み込み時に既存 OS 環境変数を上書きしない、.env.local は override=True だが protected を尊重）。
- run_monitoring の監視 DB 接続
  - Monitoring は KABUSYS_ENV に依存せず「本番」用 sqlite_path を使用する仕様を明文化。

Fixed
- 例外・安全終了処理の改善
  - run_monitoring と run_execution の両スクリプトで停止フラグ（data/stop_requested.flag）検知や KeyboardInterrupt を考慮して正常にクローズ処理（DB 接続の close 等）を行うように整理。
  - setup_logging() がログディレクトリ作成に失敗した際にファイルハンドラだけをスキップし、stderr ではなく stdout/stderr に適切に警告を出すように改善。
- config パーサの堅牢化
  - _parse_env_line() がシングル/ダブルクォート内のバックスラッシュエスケープと閉じクォート検出を扱い、コメントの扱いなどを正確にパースするよう改善。

Security
- .env の取り扱いに関する注意喚起を config_setup.py 内に明記（.env を絶対に Git にコミットしない旨のヘッダを生成）。

Notes / Implementation details
- 環境変数追加/仕様
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。不正値はデフォルト 60 秒へフォールバック。
  - PAPER_FILL_MODE: ペーパートレードの約定モード ("instant" | "partial" | "never" | "reject") をサポート。無効値は例外。
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite パス（デフォルト data/paper_trading.db）。
  - KILL_FLAG_CLEAR_ON_START: 本番環境での Kill Switch 自動クリアの危険性を検出するチェック。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（テスト用）。
  - LOG_DIR / LOG_LEVEL: ログ出力先とレベルのカスタム化。
- process_priority のフォールバック
  - Windows の優先度クラス・POSIX の nice 値をそれぞれ扱い、未対応 OS や権限不足時は警告を出してスキップ。
- Portfolio / Position sizing の設計上の注意
  - price が取得できない（0.0 等）場合にスキップする挙動や、lot_size 固定想定、将来的な拡張ポイント（株ごとの lot_size やフォールバック価格の採用）をコード内コメントで明示。
- tools/paper_verification_report の集計は SQLite のテーブル存在に依存するため、テーブルがない場合は N/A を返す耐性（try/except で sqlite3.OperationalError を扱う）。

Deprecated
- なし

Removed
- なし

参考
- 各 CLI の利用例は該当ファイルのモジュールドックストリングに記載されています（例: python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report）。

---

（以上は現行ソースコードから推測して作成した CHANGELOG です。実際のリリースノート作成時は、コミットログ・PR の説明に基づいた精査を推奨します。）