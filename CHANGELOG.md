CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-22
--------------------

Added
- 基本アプリケーションと運用用ユーティリティ群を追加。
  - src/kabusys/__init__.py
    - パッケージバージョンを 0.1.0 に設定。
- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。
    - Monitoring は環境に依らず本番 sqlite_path を使用する旨を明示。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB（data/paper_trading.db のデフォルト）を使用し、本番 DB と分離する実装。
    - 停止フラグ / PID 管理（data/execution.pid）をサポートし、別スレッドでエンジンを起動・監視。
    - ブローカークライアントは BrokerClientFactory 経由で作成（paper_trading 時は MockClient 想定）。
- 設定管理・ウィザード・検証
  - src/kabusys/config.py
    - Settings クラスを導入。環境変数または .env から設定を取得。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動読込を実行（無効化可）。
    - 多数のプロパティを提供（J-Quants、kabu API、LINE、DuckDB/SQLite パス、PID/kill フラグ、閾値、ENV/LOG_LEVEL 判定など）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や paper_sqlite_path など paper_trading 関連設定をサポート。
  - src/kabusys/config_setup.py
    - .env の対話式ウィザードを追加。既存 .env 読み込み、項目別説明、シークレット入力、保存機能を提供。
  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）、本番環境向けの追加ガード等を実装。
    - --strict オプションで警告を失敗扱いにできる。
- 監視用 DB 初期化ユーティリティの呼び出しを run スクリプトで統一（init_monitoring_db）。
- ロギングとプロセス優先度ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - setup_logging を提供。stdout (StreamHandler) と日次ローテーションされたファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR 環境変数の尊重、ファイルハンドラ失敗時のフォールバックを実装。
    - ログファイルは <log_dir>/<app_name>.log、デフォルト logs/、30日保持。
  - src/kabusys/utils/process_priority.py
    - set_process_priority / set_cpu_affinity を提供。Windows/Linux/macOS (一部 POSIX) を抽象化して優先度設定や CPU affinity 設定を行う（psutil 依存）。権限不足等で失敗しても警告でスキップ。
- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限をチェックして候補を除外する apply_sector_cap、マーケットレジームに基づく投下資金乗数 calc_regime_multiplier を実装。
  - src/kabusys/portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - lot_size 単位丸め、単銘柄上限・アグリゲート上限・スケールダウン・残差処理（端数の再配分）などのロジックを含む。
    - 将来の拡張（銘柄別 lot_size 等）に関する TODO コメントあり。
  - src/kabusys/portfolio/__init__.py
    - 上記関数群をパッケージエクスポート。
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加（期間指定オプション --from / --to、--db で DB パス指定可）。
    - システム安定性（稼働率）、注文成功率（fill/send）、リスク却下数、API レイテンシ（avg/max/P95）を算出し、閾値と比較して PASS/FAIL を判定する。デフォルト閾値を定義。
- 研究用モジュール（未完の一部を含む）
  - src/kabusys/research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの設計・一部実装（モメンタム等の定数・インターフェース設計）。（ファイル末尾で実装が途切れているため、引き続き実装予定）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / 運用上の注意
- run_monitoring と run_execution はそれぞれ setup_logging と set_process_priority を起動直後に呼び出すため、ログの設定とプロセス優先度設定が統一されます。
- MONITOR_POLL_INTERVAL が不正（非整数、0 以下など）の場合は警告を出しデフォルト（60 秒）にフォールバックします。
- run_execution は KABUSYS_ENV に応じて paper_trading 用 DB を切り替えるため、本番 DB と paper_trading DB は分離されます（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可）。
- .env の自動読み込みはプロジェクトルートが検出できる場合にのみ行われます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログは標準出力（stdout）へ出力されるため、cron / task scheduler での標準出力リダイレクトとの相性が良い設計です。
- process_priority / set_cpu_affinity は権限や OS 実装差により失敗する可能性があります（その場合は警告が出てスキップされます）。
- Paper Verification レポートの閾値は src/kabusys/tools/paper_verification_report.py 内の定数で定義されています。必要に応じて調整してください。

Acknowledgements / TODO
- research/factor_research.py の詳細実装およびその他ドキュメント（PortfolioConstruction.md 等）に基づく追加実装は継続作業対象です。
- position_sizing の price フォールバック（price が欠損時の扱い）や、銘柄別 lot_size のサポートは将来の改善点としてコメントで残しています。