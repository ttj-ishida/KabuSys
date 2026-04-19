CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠しています。

0.1.0 - 2026-04-19
-----------------

Added
- 起動スクリプト / デーモン機能
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境設定にかかわらず本番用 sqlite_path を使用して DB を初期化（init_monitoring_db）。
    - duckdb との接続を確立し、停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - プロセス優先度を高に設定（set_process_priority）し、例外発生時はログを出して次のポーリングへ継続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory により本番 / モックのブローカークライアントを生成。
    - Engine を別スレッドで実行、停止フラグ（data/stop_requested.flag）検知で Engine.stop() を呼び安全に停止。
    - 実行中 PID を data/execution.pid に記録する想定（pid_file 経由）。
    - 起動時にプロセス優先度を高に設定。

- 設定管理・初期化
  - config.py
    - Settings クラスを追加。環境変数からアプリ設定を取得するプロパティ群を提供（DB パス、API トークン、運用モード判定など）。
    - .env 自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサを強化し（_parse_env_line）、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
    - Paper Trading 固有設定（paper_fill_mode, paper_sqlite_path）や監視閾値設定（cpu/memory/disk）をプロパティ化。
    - env / log_level の検証と is_live / is_paper / is_dev ヘルパーを提供。
  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを追加。必須/任意項目の入力補助、既存 .env の読み込み・マスク表示、--env-file オプション対応。
    - .env 書き込みは決められたテンプレートで出力（秘匿項目はマスク表示）。
  - validate_config.py
    - .env および config/*.yaml の起動前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV および LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、PyYAML が利用可能なら YAML ファイルのパースチェックを実施。
    - --strict モードで警告を FAIL 扱いにできる CLI。

- 分析・レポートツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。指定期間（--from / --to）や DB パス（--db）で集計可能。
    - システム稼働率、注文成功率、送信率、P95 レイテンシなどを算出し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 計算、欠損データに対する安全処理、SQL クエリの分離を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順ソート＆上位 N 選出。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率で重み付け。全銘柄スコアが 0 の場合は等金額へフォールバック（警告出力）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）を評価し、上限超過セクターの新規候補を除外（"unknown" セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム ("bull" / "neutral" / "bear") に応じた投下資金乗数を返す。未知レジームは警告して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて発注株数を計算。
      - lot_size に従う丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積を実装。
      - price 欠損や小数処理に対する耐性、残余キャッシュを用いた再配分ロジックを実装。
      - risk_based の場合は risk_pct と stop_loss_pct から単純に株数を導出。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）を設定。
    - ログレベル・ログディレクトリの解決順を定義し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - stdout を使用することで外部スケジューラ等からのログリダイレクトと親和性を確保。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度（nice/priority class）を設定するヘルパーを追加（set_process_priority）。
    - CPU affinity 固定ユーティリティ（set_cpu_affinity）を追加。psutil 依存で、権限や OS の制約がある場合は警告してスキップ。

- 研究向けモジュール（下地）
  - research/factor_research.py
    - DuckDB を使ったファクター計算モジュールの骨子を追加（Momentum / Value / Volatility / Liquidity を想定）。
    - calc_momentum のインターフェースと定数群を定義（実装は継続）。

Changed
- ロギング出力先の明確化
  - logging_setup は StreamHandler を stdout に固定（stderr ではない）、起動スクリプトから共通で呼び出すことでログ管理を統一。

Fixed
- 環境変数パーサの堅牢化
  - config._parse_env_line がクォート・エスケープ・インラインコメント処理を改善し、より正確な .env 読み込みを実現。

Notes / Known limitations
- factor_research.py は一部実装が続行中（スニペットは途中で切れているため完全な計算ロジックは未完）。
- position_sizing 内の価格欠損処理に関する TODO が残されており、将来的にフォールバック価格（前日終値や取得原価）を導入する予定。
- apply_sector_cap は sector が "unknown" の銘柄を除外対象としない設計になっているため、マスタ未登録銘柄の扱いに注意が必要。
- process_priority / set_cpu_affinity は権限不足や一部 OS で動作しない場合があり、その際は警告を出して処理を継続する。
- .env 自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。自動ロードを無効化する環境変数を用意。

Security
- 本リリースでは特にセキュリティ修正はありません。環境変数に API トークン等を含むため .env ファイルは決してリポジトリにコミットしないでください（config_setup の出力にもその旨の注意を記載）。

Contributing
- バグ報告・プルリクエスト歓迎。テストやドキュメントの追加で貢献してください。

---
（初版リリース: v0.1.0）