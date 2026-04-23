# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
このファイルは Keep a Changelog に準拠しています。  
Released はセマンティックバージョニングに従います。

## [Unreleased]

- （現時点のリポジトリ状態はバージョン 0.1.0 としてリリース済みのため、未リリースの変更はありません。）

## [0.1.0] - 2026-04-23

初回公開リリース。自動売買システム KabuSys のコア機能群を実装しました。主な追加点は以下のとおりです。

### 追加 (Added)
- 基本パッケージとバージョニング
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。

- 設定管理
  - Settings クラス（kabusys.config）を実装し、環境変数から設定を取得する仕組みを提供。
    - DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）や API トークン等をプロパティ経由で取得。
    - KABUSYS_ENV / LOG_LEVEL の検証、paper_trading 用の挙動識別（is_paper / is_live / is_dev）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - OS 環境変数を保護する protected 上書きルール。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード抑止。

- .env ウィザード CLI
  - config_setup.py：対話式ウィザードで .env の生成・更新を支援。
    - 秘匿入力（トークン等）のマスク表示、選択肢やデフォルト値サポート、確認・保存機能。
    - 書き出しフォーマットおよび注意文を出力。

- 設定検証 CLI
  - validate_config.py：起動前の設定検証ツールを実装（必須環境変数チェック、KABUSYS_ENV 検証、DB パス確認、config/*.yaml の存在・パースチェックなど）。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML 未インストール時は YAML 内容検証をスキップして警告。

- 起動スクリプト
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定する処理を実行。
    - paper_trading 環境では専用の PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用した停止制御。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正値は警告してデフォルトへフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは共通の monitoring DB へ記録）。
    - 停止フラグ検知と例外ハンドリング機構を実装。

- データベース初期化
  - monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

- ロギング・プロセス管理ユーティリティ
  - utils.logging_setup.setup_logging を実装。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の優先解決ルールを実装。
  - utils.process_priority:
    - set_process_priority(level) で Windows / POSIX(Linux, macOS 等) を吸収してプロセス優先度 (nice / HIGH_PRIORITY_CLASS) を設定。
    - set_cpu_affinity(cpu_count) によりプロセスを最初の N コアにピン留め可能。権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築モジュール
  - kabusys.portfolio:
    - portfolio_builder.select_candidates / calc_equal_weights / calc_score_weights を実装（スコア順ソート、等金額・スコア加重配分、スコア0時のフォールバック）。
    - risk_adjustment.apply_sector_cap / calc_regime_multiplier を実装（セクター上限適用、レジーム別投下資金乗数）。
    - position_sizing.calc_position_sizes を実装（risk_based / equal / score の配分方式、単元株処理 lot_size デフォルト 100、aggregate cap によるスケール調整・端数処理）。
    - 設計注釈（価格欠損時の挙動、将来の拡張ポイント）を含む。

- リサーチ（ファクター計算）雛形
  - research.factor_research にてモメンタム等ファクター計算の骨子を追加（DuckDB 接続を受け、prices_daily / raw_financials を参照する設計）。一部未完の関数（ファイル末尾で途切れ）あり。

- Paper Trading 検証ツール
  - tools.paper_verification_report を実装。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH、既定: data/paper_trading.db）を参照して検証レポートを標準出力に生成。
    - 指標：稼働率 (uptime)、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）等。
    - デフォルト閾値を定義（稼働率 99%、成功率 90%、送信率 95%、P95 200ms）。
    - CLI オプション: --from / --to / --db（期間フィルタ、DB 指定）。
    - DB 未存在やテーブル欠落時のフォールバックとメッセージ出力を実装。

### 変更 (Changed)
- 設計方針として、起動系（monitoring / execution）は停止フラグファイルと PID ファイルでプロセス管理を行う共通仕様を採用。

### 修正 (Fixed)
- 各種外部環境や権限不足に対する堅牢化を実施（ログディレクトリ作成失敗、プロセス優先度設定失敗、DB の OperationalError 等で警告・フォールバックする実装）。

### ドキュメント / コメント
- 各モジュールに日本語の docstring と設計コメントを追加（動作の前提・制約・将来の TODO などを明記）。

### 既知の制限 / TODO
- research.factor_research の一部関数が未完（ファイル終端で途中）。本格運用前に完成が必要。
- position_sizing の lot_size は現状全銘柄共通の仮定（将来的に銘柄別単元対応の拡張予定）。
- price 欠損時のエクスポージャー過小見積りに関する改善（前日終値などのフォールバック）を検討中。

---

注: 上記はソースコードから推測して作成した変更履歴です。実際のリリースノート作成時は、コミット単位の変更差分やパッケージ配布履歴を参照して補完してください。