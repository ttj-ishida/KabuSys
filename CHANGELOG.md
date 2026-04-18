CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠して記載しています。コードベースから推測できる変更・追加点を日本語でまとめています。

Unreleased
----------
- （現在の差分はありません）

0.1.0 - 2026-04-18
-----------------
注: パッケージの __version__ は 0.1.0 に設定されています。以下はこの初期リリースで導入された主要な機能・CLI・ユーティリティ・設計上の決定を、ソースコードから推測してまとめた内容です。

Added
- 基本パッケージ
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージエクスポート: data, strategy, execution, monitoring モジュール群を公開。

- 実行/監視用エントリポイント
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderManager / RiskManager / Reconciler などを組み立てて ExecutionEngine を別スレッドで実行。停止フラグ（data/stop_requested.flag）検知時に安全に停止。
    - エンジンの PID を data/execution.pid に記録する仕組み（pid_file を受け渡し）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path（Settings.sqlite_path）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - SQLite および DuckDB の接続を確立して SystemMonitor に渡す。

- 環境設定・検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新する CLI を追加。
    - J-Quants トークン・kabu API パスワード等の必須項目、ログレベルや DB パス、Kill Switch オプション等を対話形式で設定可能。
    - .env の読み書きロジックを備え、既存値の再利用やマスク表示（シークレット項目）に対応。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DUCKDB/SQLITE パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がインストールされている場合）などを実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- 環境変数・設定管理
  - config.py
    - Settings クラスを導入。プロパティベースで各種環境変数を取得・検証する（例: jquants_refresh_token, kabu_api_password, duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/Memory/Disk 閾値等）。
    - KABUSYS_ENV の自動読み取りと妥当性検証（development / paper_trading / live を許容）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject のみ）。
    - プロジェクトルートの自動検出ロジックを実装し、.env/.env.local の自動ロードを実行（OS 環境変数は保護される）。
    - settings = Settings() のグローバルインスタンスを提供。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を返す（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア正規化配分を提供。スコア合計が 0 の場合は等配分にフォールバックして警告。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）をチェックし、上限を超えるセクターの新規候補を除外するロジックを実装。"unknown" セクターは除外対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。

  - portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的コスト見積り、残差処理での追加配分ロジックなどを提供。

- ユーティリティ
  - utils.logging_setup
    - 統一的なログ設定関数 setup_logging を提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
    - ログディレクトリ解決順: 引数 > 環境変数 LOG_DIR > デフォルト logs/。ディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみで継続。

  - utils.process_priority
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収（psutil を利用）。権限不足や未サポート環境では警告を出してスキップ。

- モニタリング / 検証ツール
  - monitoring.monitoring_db の初期化を各エントリポイントが呼び出し、監視テーブルの存在を保証する（冪等）。
  - tools.paper_verification_report
    - ペーパートレード DB（デフォルト: data/paper_trading.db）を解析して検証レポートを生成する CLI。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate)、送信率 (send_rate)、レイテンシ（avg/max/P95）、リスク却下数 等。
    - 判定基準（閾値）を定義: 稼働率 >= 99.0%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - 日付フィルタ（--from/--to）、DB パス指定（--db / PAPER_TRADING_SQLITE_PATH）に対応。

Changed
- なし（初期リリースのため該当なし）

Fixed
- なし（初期リリースのため該当なし）

Notes / Known limitations / Implementation details
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値が設定された場合に警告を出しデフォルト（60 秒）へフォールバックする。0 以下は受け付けない（time.sleep の仕様に基づく）。
- run_execution は ExecutionEngine を別スレッドで実行し、停止フラグ検出時に engine.stop() を呼んで安全停止する。最大 join タイムアウトを設けて終了待ちを行う設計。
- Settings の自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行う。プロジェクトルートが特定できない場合は自動読み込みをスキップする。
- paper_trading と live の DB は分離される（paper_trading は paper_sqlite_path を使用）ため、ペーパートレードのデータが本番 DB に混入しない設計。
- process_priority / cpu_affinity は権限や OS 依存で失敗する可能性があるため例外を捕捉し、失敗時は警告を出して続行する安全設計。
- portfolio.* モジュールは純粋関数群として設計され、DB を直接参照しないためユニットテストが容易。将来的に lot_size を銘柄毎に持たせる拡張がコメントで示唆されている。
- research.factor_research モジュールはファクター計算（Momentum, Value, Volatility, Liquidity）を行う設計。ソースの一部が途中で切れているため（calc_momentum の定義途中で終了している）、実装が未完またはここでは一部のみが含まれている可能性がある。実動作には prices_daily / raw_financials テーブルの存在と適切な DuckDB 接続が必要。

Migration / Upgrade notes
- 本リリースからのアップグレード時は .env のキー名やデフォルトパスに注意すること（特に SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH）。
- ログ出力先をカスタムにする場合は LOG_DIR を設定するか setup_logging の引数で指定する。
- 本番移行時は KABUSYS_ENV=live、LINE_* の設定、KILL_FLAG_CLEAR_ON_START の値の取り扱い（0 推奨）などを validate_config で必ず確認すること。

Authors
- コードベース（初期実装）に基づき自動生成された CHANGELOG（推測情報を含む）。

もし特定のファイルや機能に関してより詳細な変更履歴や補足（例: 関数ごとの仕様、入出力例、未実装箇所の一覧）を希望される場合は、対象箇所を指定していただければ詳細に展開します。