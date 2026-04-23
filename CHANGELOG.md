# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  

注: 以下はリポジトリ内のソースコードから推測した初回リリース向けの変更履歴です（コードベースの機能追加・設計を要約しています）。

## [Unreleased]

## [0.1.0] - 2026-04-23
初回リリース — 基本機能と CLI / ランナー群を実装。

### Added
- 基本パッケージ情報
  - kabusys パッケージ初期化（__version__ = 0.1.0）。

- 設定管理
  - Settings クラスによる環境変数ラッパーを実装（config.py）。
  - プロジェクトルート自動検出機能（.git または pyproject.toml を基準）。
  - .env ファイル自動読み込み（.env / .env.local）、および細かな .env パース（クォート・エスケープ・コメント対応）。
  - 必須変数未設定時に明確なエラーメッセージを返す _require()。

- 対話式設定ウィザード
  - config_setup.py: .env を対話式で作成・更新するウィザードを追加。
  - 作成済み .env の読み取り・上書きロジック、秘密項目マスク表示、確認プロンプト付き保存。

- 設定検証 CLI
  - validate_config.py: .env と config/*.yaml の整合性チェック（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、YAML パース等）。
  - --strict オプションで警告をエラー扱いにできる。

- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py: stdout StreamHandler と 日次ローテーションの TimedRotatingFileHandler を設定する共通ユーティリティ。
    - ログディレクトリ作成失敗時はファイル出力を無効化して継続。
  - utils/process_priority.py: マルチプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティ。
    - CPU affinity 設定関数（set_cpu_affinity）を実装。
    - 権限不足・未サポート環境時に警告を出して安全にフォールバック。

- 実行ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を設定し、SQLite / DuckDB に接続。
    - KABUSYS_ENV=paper_trading 時は paper 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - stop flag / pid ファイル管理、スレッドでの実行・監視、停止フラグ検知で安全終了。

- 監視ランナー
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境に依らず本番 sqlite_path を監視 DB に使用（監視は本番データを参照）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知・例外ハンドリング・接続クローズ処理を実装。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルの存在を保証（冪等処理）。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順 + tie-breaker（signal_rank）で候補選択。
    - calc_equal_weights, calc_score_weights: 等重配分・スコア加重配分（スコア合計 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（既存保有のエクスポージャー計算と候補除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジーム時のフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の割当方式に対応した株数算出。単元株（lot_size）丸め、per-stock 上限・aggregate キャップ、コストバッファ、available_cash によるスケーリングを実装。

- リサーチ（ファクター計算）基盤
  - research/factor_research.py: Momentum 等のファクター計算モジュールの骨組みを追加（DuckDB 接続を受け取り prices_daily 等を参照する設計、パラメータ定義や P95 等のユーティリティを含む）。（実装の一部が続く構成）

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計してレポート出力（稼働率、注文成功率、送信率、P95 レイテンシなど）。
    - 閾値に基づく PASS/FAIL 判定と詳細出力。
    - 日付フィルタ（--from/--to）と --db オプション対応。
    - P95 計算ヘルパと欠損データに対する堅牢な処理を実装。

### Changed
- ログ出力設計
  - 全ランナーが共通の setup_logging を呼び出すことでログ出力の一貫性を確保（日次ローテーション、stdout 出力）。

- データベース取り扱い
  - 起動時に monitoring DB の初期化を必ず実行して監視テーブルの存在を保証（冪等性を考慮）。

### Fixed
- 環境変数パースの堅牢化
  - .env パーサがクォート文字内のエスケープやインラインコメントの扱いを正しく解析するよう改善。
  - export KEY=val 形式への対応。

### Security
- .env の取り扱いに関する注意書きを config_setup の生成ファイルに明記（.env を絶対に Git にコミットしない旨）。

---

注:
- ここに記載した機能や挙動はソースコードから推測してまとめたものです。実際の挙動や API 仕様、細かい実装は実行環境や未表示のモジュール（例: execution/ 以下の細部、monitoring/system_monitor の実装等）に依存します。必要であれば各モジュール単位での詳細な CHANGELOG（関数シグネチャ変更・内部ロジックの差分等）を追記します。