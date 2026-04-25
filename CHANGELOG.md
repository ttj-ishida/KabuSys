CHANGELOG
=========

This project follows "Keep a Changelog" format. 日本語での変更履歴です。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-25
--------------------

Added
- 全体
  - 初期リリースをタグ v0.1.0 として公開。パッケージ識別子は kabusys、__version__ = "0.1.0" を含む。

- 実行用スクリプト
  - run_execution.py を追加：
    - ExecutionEngine を起動するエントリポイント。プロセス優先度を高く設定して実行。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を介してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をバックグラウンドスレッドで実行。
    - data/stop_requested.flag の検出で安全にシャットダウンする仕組みを実装（実行 PID を data/execution.pid に記録）。
    - RiskManager の既定設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を組み込む。initial_portfolio_value は broker.get_available_cash() で初期化。

  - run_monitoring.py を追加：
    - SystemMonitor のポーリングループ起動スクリプト。プロセス優先度を高く設定して実行。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、負または不正値はデフォルトにフォールバック）。
    - 監視 DB は環境にかかわらず本番 sqlite_path（data/monitoring.db）を使用。停止フラグでループ終了。
    - duckdb との接続を確立し SystemMonitor に渡す。

- 設定・検証
  - config.py を追加：
    - 環境変数ラッパー Settings クラスを提供（J-Quants/FIX/Kabu/LINE/DB/監視閾値/システム設定等）。
    - .env の自動ロード機構を実装（プロジェクトルートの .git または pyproject.toml を検出基準）。優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パースでクォート内エスケープ、inline コメント処理、export キー対応など細かい仕様に対応。
    - 設定値検証（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）と is_live/is_paper/is_dev ヘルパーを提供。

  - config_setup.py を追加：
    - 対話式ウィザードで .env を初期作成／更新する CLI。
    - 標準項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE トークン等）を含む。既存 .env を読み込んで Enter で再利用可能、シークレットはマスク表示。
    - 保存前の確認ダイアログを実装。

  - validate_config.py を追加：
    - 起動前の設定検証 CLI。必須環境変数・KABUSYS_ENV の妥当性・DB パス親ディレクトリの存在・config/*.yaml の存在/パース（PyYAML がある場合）・本番環境向けガードをチェック。
    - --strict オプションで警告を失敗扱いにできる。

- ユーティリティ
  - utils/logging_setup.py を追加：
    - 共通のログ設定ユーティリティ。StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止、ログレベルとログディレクトリは引数・環境変数・デフォルトの順で解決。
    - ログディレクトリ作成失敗時はファイル出力をスキップして警告出力する。

  - utils/process_priority.py を追加：
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定するヘルパー。Windows では HIGH_PRIORITY_CLASS 等を利用、POSIX 系では nice 値を設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。権限不足や未対応環境では警告を出力して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナルの選定 select_candidates（スコア降順、同点時は signal_rank でタイブレーク）。
    - 等配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 同一セクターの既存エクスポージャが max_sector_pct を超える場合に新規候補を除外（"unknown" セクターは上限適用除外）。
    - calc_regime_multiplier: market レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは警告を出して 1.0 にフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数算出。単元株（lot_size）に丸め、1 銘柄上限／aggregate cap／cost_buffer（手数料・スリッページ想定）を考慮したスケールダウンロジックを実装。
    - aggregate cap 超過時はスケーリング後に残差（fractional remainder）優先で lot_size 単位を追加分配する仕組みを採用し、上限を超えないよう安全弁を実装。

- モニタリング・検証ツール
  - monitoring 側初期化ヘルパ（monitoring_db、SystemMonitor への初期化呼び出し）を各スクリプトから利用。
  - tools/paper_verification_report.py を追加：
    - Paper Trading 用 SQLite を読み、システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均／最大／P95）を集計してレポート表示。
    - P95 算出、日付フィルタ（--from/--to）対応、DB が無ければ適切にエラーメッセージを出力。
    - パス/フェイル閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）し、総合判定（PASS/FAIL）を出力。

Changed
- 設定読み込みポリシー
  - .env 自動ロードの優先度を明確化（OS 環境変数を保護し .env.local で上書き可能）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

- ロギング
  - 全起動スクリプト共通で setup_logging を利用する設計に変更。コンソール出力は stdout を使用し、cron/Task Scheduler でのリダイレクト想定。

Fixed
- 環境変数パーサ
  - config._parse_env_line においてクォート内のバックスラッシュエスケープやクォートの正しい終了検出、インラインコメント処理を正確に扱うように実装。export プレフィックスに対応。

Notes / Work in progress
- research/factor_research.py はモメンタム等のファクター計算方針と定数が実装されているものの、ファイル末尾で途中（calc_momentum の実装開始）で切れているように見えます。今後のリリースで DuckDB クエリを使った完全実装・ユニットテストの追加を予定。

Security
- 環境変数ファイル (.env) を絶対に Git にコミットしない旨を config_setup のヘッダに明記。

その他
- CLI ヘルパ（config_setup, validate_config, tools/paper_verification_report）を含め、運用向けの導線（設定ウィザード → 検証 → 実行/監視）を整備。
- 多くの箇所で権限不足・モジュール未提供時のフォールバック（例: ログディレクトリ作成失敗時、PyYAML 未インストール時、psutil の機能未提供時）を丁寧にハンドリングする方針を採用。

今後の予定（候補）
- research/factor_research の完全実装（DuckDB クエリによるファクター計算）。
- ExecutionEngine / SystemMonitor 周りのユニットテスト・統合テスト整備。
- 個別銘柄の lot_size を stocks マスタで管理する拡張（position_sizing の TODO）。