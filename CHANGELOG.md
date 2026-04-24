CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

v0.1.0 — 2026-04-24
-------------------

Added
- 基本アプリケーション構成を実装（初回リリース）。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite を使用し、MockBrokerClient を利用することで本番 DB と分離。
    - Engine をデーモンスレッドで実行し、data/stop_requested.flag による安全停止を実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用途の DB 接続と duckdb 接続の初期化を行い、停止フラグ検知でループを終了。
- 設定・環境管理
  - config.py: Settings クラスを実装。
    - .env の自動読み込み（プロジェクトルート検知: .git / pyproject.toml）。
    - .env/.env.local の読み込みルール（OS 環境変数を保護する protected 指定）。
    - 各種環境変数（DB パス、API トークン、Paper Trading 設定、閾値や PID ファイルパス等）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーションなど、値検証ロジックを実装。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（CLI）。
    - 秘匿項目のマスク表示、選択肢・デフォルト対応、.env ファイル書き込みテンプレートを提供。
    - .env を Git にコミットしない旨の注意文を同梱。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証など。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純関数モジュール）
  - portfolio/portfolio_builder.py: 候補選定（スコアソート）、等配分・スコア重み計算を実装。
  - portfolio/risk_adjustment.py: セクター集中上限適用、レジームに応じた乗数（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py: 株数算出ロジックを実装（risk_based / equal / score）、単元株丸め、aggregate cap スケールダウン、コストバッファ考慮。
  - portfolio/__init__.py: 上記 API をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギングセットアップを実装。
    - stdout へ StreamHandler、ファイルへ TimedRotatingFileHandler（日次ローテート、30日保持）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを実装。
    - Windows / POSIX の差分を吸収して呼び出し側を単純化。
    - set_process_priority(level) / set_cpu_affinity(cpu_count) を提供。権限や未対応環境では警告を出してスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（Fill/Send）、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を行う。
    - DATE 範囲フィルタ、PAPER_TRADING_SQLITE_PATH による DB 指定対応。
- 研究用モジュール（部分実装）
  - research/factor_research.py: Momentum 等のファクター計算器を追加（DuckDB を用いた prices_daily / raw_financials 参照、Zスコア化等を想定）。一部実装は続きあり。

Changed
- 初期リリースのため、内部設計と CLI の公開を明確化（.env 自動ロードのデフォルト動作、ログ設定の解決順などを文書化）。

Fixed
- MONITOR_POLL_INTERVAL の無効な値に対してデフォルトにフォールバックする挙動を追加（不正値時に警告を出力）。これにより time.sleep に渡す不正な値による例外を防止。
- run_execution/run_monitoring での DB 初期化を冪等化（init_monitoring_db 呼び出し）。監視テーブルが確実に存在することを保証。
- ログディレクトリ作成やファイルハンドラ作成に失敗した際に適切にフォールバックするよう改善（起動が致命的に停止しない）。

Security
- config_setup にて .env ファイルを生成する際、ファイルを Git にコミットしない注意文を同梱。
- Settings._require による必須環境変数未設定時の明確なエラーメッセージを追加。

Notes / Caveats
- run_monitoring は意図的に KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計になっています（監視データは環境に依存せず集約したい場合に想定）。
- 一部モジュール（例: research/factor_research）の実装は続きがあるファイルが含まれます。今後のリリースで計算ロジックの追加・テストを進めます。
- OS / 権限により process priority や CPU affinity の設定が失敗する可能性があります。失敗時はログにワーニングを残してスキップします。

Acknowledgments
- 初期設計では DuckDB と SQLite を併用し、解析用と運用用にデータレイヤを分離しています。各種 CLI とユーティリティによりローカル開発・ペーパートレード・本番運用のワークフローを支援します。