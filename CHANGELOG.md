CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーション構成を追加
  - パッケージ初期版として KabuSys の主要コンポーネントを実装。
  - バージョン: 0.1.0

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成を BrokerClientFactory で抽象化。
    - Engine をデーモンスレッドで実行し、 data/stop_requested.flag による停止制御と execution.pid による PID 管理をサポート。
    - リスク管理用のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を提供。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する挙動を明示。
    - 停止フラグ（data/stop_requested.flag）検出、例外ハンドリング、接続のクローズ処理を実装。

- 設定・環境管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml により検出）。
    - .env / .env.local を OS 環境変数を保護しつつロード（.env.local で上書き可能）。
    - .env パース機能を強化（export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱い）。
    - Settings クラスで各種環境変数をラップ（DB パス、ログ設定、Paper Trading 関連、監視しきい値など）。
    - PAPER_FILL_MODE のバリデーションを実装（instant|partial|never|reject）。

  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を実装。
    - 既存 .env 読み込み、シークレット入力、デフォルト提示、保存確認機能を提供。
    - .env ファイルへの書式化保存を実装（コメント付き、Git にコミットしない旨の注記）。

  - validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML がある場合）を実施。
    - --strict モードで警告を FAIL 扱いにできる。
    - 本番（live）用の追加ガード（LINE 通知設定の有無、KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。
    - LOG_DIR / LOG_LEVEL の優先順位、ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続するフォールバックを実装。
    - 既存ハンドラのクリーンアップ処理を実装（重複設定防止）。

  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows / POSIX 機能）を実装。
    - set_process_priority(level) で high/normal/low を設定、psutil のエラーは警告で無視。
    - set_cpu_affinity(cpu_count) による CPU affinity 設定を提供（未サポート環境では警告）。

- ポートフォリオ構成ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
    - スコア全ゼロ時のフォールバックと警告処理を実装。

  - portfolio/risk_adjustment.py
    - セクター上限チェック（apply_sector_cap）を実装。既存保有を考慮して当日売却予定銘柄を除外するオプションを実装。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear にマッピング、未知レジームはフォールバックで 1.0）。

  - portfolio/position_sizing.py
    - position sizing（calc_position_sizes）を実装。
    - allocation_method="risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap、cost_buffer（スリッページ・手数料見積）に基づくスケーリング、残差処理ロジックを実装。
    - price 欠損時のスキップ、将来的な拡張（銘柄別 lot_size 等）についての TODO を明記。

- Paper Trading / 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを実装。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計。
    - 判定基準（稼働率、成功率、送信率、P95 レイテンシ）と PASS/FAIL 判定を実装。
    - 日付フィルタ（--from/--to）、DB パス指定（--db / 環境変数）対応。

- データベース / 分析
  - DuckDB を分析用途に採用（Settings.duckdb_path）。
  - 監視用 SQLite の初期化ユーティリティ（monitoring.monitoring_db.init_monitoring_db）を run_* スクリプトから呼び出して冪等に作成。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Deprecated
- なし（初回リリース）

Security
- なし（特別なセキュリティ修正はなし）

Notes / Migration
- .env の自動ロード
  - デフォルトでプロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- paper_trading 環境
  - paper_trading モードでは発注は実ネットワークに送信されない想定ですが、リスク設定やモックブローカーの振る舞い次第で挙動が異なるため .env の PAPER_FILL_MODE 等を確認してください。

- ロギング
  - ログ出力先はデフォルトで logs/<app_name>.log（日次ローテーション）ですが、LOG_DIR を設定することで変更できます。ディレクトリ作成に失敗した場合は標準出力のみで動作します。

Known issues / TODO
- research/factor_research.py は設計方針や定数を定義しているものの、ファイル末尾で実装が途中（ソース切断の痕跡あり）になっています。ファクター計算ロジックの完全実装が必要です。
- position_sizing.calc_position_sizes や apply_sector_cap 内に「将来的な拡張」を示す TODO コメントがあります（価格欠損時の代替価格、銘柄別 lot_size 等）。
- 一部の外部依存（psutil, duckdb, PyYAML など）が存在します。利用環境にインストールされているか確認してください。
- 実行時の権限不足でプロセス優先度や CPU affinity の設定が失敗する場合、警告を出してスキップします。

参考: 主要コマンド
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。