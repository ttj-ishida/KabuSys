CHANGELOG
=========

すべての変更は Keep a Changelog 規約 (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

未リリース
---------

- 現時点では未リリースの変更はありません。

[0.1.0] - 2026-04-17
-------------------

Added
- 初回公開リリース: KabuSys のコア機能を実装。
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" と設定。
- 実行用スクリプトを追加:
  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor をポーリングするループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag によるフラグ検知で行う。
    - 監視処理は KABUSYS_ENV の値に関わらず settings.sqlite_path（本番用 SQLite）を使用して DB 接続を行う。
    - DuckDB も接続して SystemMonitor に渡す。
    - 例外発生時はログ出力して次のポーリングを継続する実装。
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine を起動するエントリポイント。Engine は別スレッドで実行され、停止フラグで優雅に停止可能。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を行う。
    - 起動時に既に停止フラグがある場合は起動せず終了する。
- 設定・環境管理 (src/kabusys/config.py)
  - .env 自動ロード機能を実装（プロジェクトルート検出による .env / .env.local の読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パースは export KEY=val 形式やクォート文字列、インラインコメント（スペース直前の #）に対応。
  - Settings クラスを提供し、主要な環境変数をラップ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, 各種閾値など）。
  - PAPER_FILL_MODE の値検証（instant/partial/never/reject）。
- 設定ウィザード CLI (src/kabusys/config_setup.py)
  - .env の対話式作成・更新ウィザードを追加。複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START 等）に対応。
  - 既存 .env 読み込み、デフォルト値表示、シークレット値のマスク表示、保存確認機能を実装。
- 設定検証 CLI (src/kabusys/validate_config.py)
  - .env および config/*.yaml の基本的な妥当性検証を実装。必須環境変数の存在チェック・プレースホルダ値検出、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML パース（PyYAML が存在する場合）を行う。
  - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ライブラリ (src/kabusys/portfolio/)
  - portfolio_builder.py: 銘柄選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）およびマーケットレジームに応じた乗数（calc_regime_multiplier）。
  - position_sizing.py: 発注株数算出（calc_position_sizes）。allocation_method ("risk_based", "equal", "score")、lot_size、cost_buffer、aggregate cap スケーリング（小数端数の lot 単位での調整）などを実装。
  - パッケージエクスポートを整理（src/kabusys/portfolio/__init__.py）。
- ユーティリティ (src/kabusys/utils/process_priority.py)
  - プロセス優先度設定と CPU affinity 設定関数を実装（set_process_priority, set_cpu_affinity）。Windows/Linux/macOS の差分を吸収する実装。
  - 実行開始直後に run_* スクリプトが set_process_priority("high") を呼ぶように統一。
- Paper Trading 検証レポートツール (src/kabusys/tools/paper_verification_report.py)
  - SQLite（ペーパー用 DB）から各指標（稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ）を集計してレポート出力する CLI を実装。閾値を定義して PASS/FAIL 判定を行う。
  - 日付フィルタ（--from / --to）と DB パス指定 (--db) に対応。
- 研究用ファクター計算 (src/kabusys/research/factor_research.py)
  - DuckDB を用いたモメンタム／ボラティリティ系ファクター計算の実装（calc_momentum, calc_volatility の一部を実装）。prices_daily テーブルを前提に計算を行う設計。

Changed
- なし（初回リリースのため該当なし）。

Fixed
- なし（初回リリースのため該当なし）。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

注意事項（重要）
- 監視 (run_monitoring) は KABUSYS_ENV の値に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用して監視データベースへ接続します。環境によって別 DB を期待する場合は設定を確認してください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。ペーパートレード DB と本番 DB は分離されます。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）が見つからない場合にスキップされます。CI/特別なケースでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- process_priority 設定や CPU affinity 設定は権限不足やプラットフォーム非対応時にスキップされ、警告ログが出力されます。
- risk_adjustment.apply_sector_cap 内に price が欠損（0.0）だった場合の注記（TODO）が残っており、将来的にフォールバック価格の導入が予定されています。現在は欠損価格があるとエクスポージャーが過小評価される可能性があります。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db（paper_trading 用）
- PAPER_FILL_MODE — instant | partial | never | reject（デフォルト instant）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START — 本番環境での Kill Switch 自動クリア (0/1)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — .env 自動ロード無効化フラグ (任意)

CLI / 実行例
- 環境設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- エンジン起動（ExecutionEngine）:
  - python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

既知の改善余地（今後の対応候補）
- risk_adjustment の price 欠損時のフォールバック実装（前日終値や取得原価の利用）。
- 各銘柄の単元株数 (lot_size) を銘柄別に対応するための拡張（stocks マスタからの取得）。
- factor_research のファクター群追加・ユニットテスト強化。
- validate_config の YAML チェックは PyYAML 非導入時にスキップされるため、環境に依存しない検証を追加検討。

Authors
- KabuSys 開発チーム（コードヘッダに記載の各モジュール）

---