# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号はパッケージの `kabusys.__version__` に合わせています。

全般的な注意
- 環境変数や .env の自動読み込みを行う設計になっており、`.env` を絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意喚起あり）。

## [0.1.0] - 2026-04-18

### Added
- 初期リリース: KabuSys — 日本株自動売買システムの基礎機能群を追加。
- CLI エントリポイント / ユーティリティ
  - `python -m kabusys.config_setup` : 対話式の .env 作成／更新ウィザード。シークレットはマスク表示し、生成した .env に注意書きを含めて保存する機能を提供。
  - `python -m kabusys.validate_config` : 起動前の設定検証ツール。必須環境変数や config/*.yaml の存在・パース（PyYAML があれば内容も検証）をチェック。`--strict` で警告を失敗扱いにできる。
  - `python -m kabusys.tools.paper_verification_report` : Paper Trading 用検証レポート生成スクリプト。期間 (--from / --to) 指定と DB パス (--db または env) に対応し、稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL を出力する。
- 起動スクリプト
  - `src/kabusys/run_execution.py` : ExecutionEngine 起動スクリプト。プロセス優先度を高に設定し、paper_trading 環境では専用の paper DB を使用して本番 DB と分離する。停止フラグ / PID 管理に対応。
  - `src/kabusys/run_monitoring.py` : SystemMonitor ポーリングループ起動スクリプト。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を参照する設計（環境に依存せず監視情報を一元化）。
- 設定管理
  - `src/kabusys/config.py` : Settings クラスを追加。環境変数のラップ（デフォルト値・バリデーション含む）を提供。自動でプロジェクトルートを検出して `.env` / `.env.local` を読み込む（無効化は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。
  - サポートする主要環境変数とデフォルト（抜粋）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
    - PAPER_FILL_MODE（default: "instant"、有効値: instant|partial|never|reject）
    - LOG_LEVEL（default: INFO）
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
    - MONITOR_POLL_INTERVAL（監視頻度の上書き、run_monitoring で使用）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
- ロギング・プロセス制御ユーティリティ
  - `src/kabusys/utils/logging_setup.py` : 統一ログ設定ユーティリティ。stdout 出力用の StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。ログディレクトリは `LOG_DIR` 環境変数で指定可能。ファイル出力が失敗した場合はコンソール出力のみで継続するフォールバックを実装。ログファイルはデフォルトで `logs/<app_name>.log`、日次ローテーション・30 日保持。
  - `src/kabusys/utils/process_priority.py` : プラットフォーム差分を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティ。Windows / POSIX(nice) に対応し、権限不足等の例外は警告ログでスキップする安全な実装。
- ポートフォリオ構築ライブラリ（純粋関数・DB 参照なし）
  - `portfolio_builder.py` : 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights。全スコアが 0 の場合は等金額にフォールバック）。
  - `risk_adjustment.py` : セクター集中制限（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier。未知レジームは警告して 1.0 にフォールバック）。
  - `position_sizing.py` : 発注株数算出（calc_position_sizes）。`risk_based` / `equal` / `score` の各方式をサポート。単元株（lot_size）で丸め、ポートフォリオ総投資額が利用可能現金を超える場合はスケールダウンロジック（端数処理を含む）を実装。手数料やスリッページを考慮する cost_buffer 引数あり。
  - `src/kabusys/portfolio/__init__.py` で主要関数をエクスポート。
- Execution コンポーネントの組み立て（run_execution が依存）
  - BrokerClientFactory によるブローカー抽象化（paper_trading 用 MockBrokerClient を使用可能）。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行フロー。RiskManager はデフォルト設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit breaker など）を利用し、初期ポートフォリオ値は broker.get_available_cash() から取得している。
  - 停止フラグ（data/stop_requested.flag）を検知して安全に終了する仕組み。
- 監視（Monitoring）
  - SystemMonitor の呼び出しループ実装。1 回の check_once() 実行で例外が起きてもループを継続するよう例外をキャッチしてログ出力。KeyboardInterrupt のハンドリングあり。
  - 監視 DB の初期化関数 init_monitoring_db の呼び出しを起動時に行い、テーブルの存在を保証（冪等）。
- Paper Trading 検証ツール
  - `tools/paper_verification_report.py` は trade_logs / system_status / risk_logs などから各種指標（稼働率、Created/Filled/Sent の集計、レイテンシ統計 P95 等）を計算し、閾値に基づいて PASS/FAIL を出力する。閾値はソース内で定義（例: 稼働率 >= 99.0%、注文成功率 >= 90% 等）。DB が存在しない場合やテーブル欠損時は N/A を扱い、適切にメッセージを出す。
- research モジュール（骨格）
  - `research/factor_research.py` にモメンタム、MA200、ATR、出来高などのファクター計算ロジックの設計と一部実装が含まれている（DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 起動時のログハンドラ二重登録を防止するため、既存のルートハンドラを flush/close してから削除して再設定する実装を追加（logging_setup）。
- 環境変数ファイルパースの堅牢化:
  - `config._parse_env_line` にてシングル／ダブルクォート内のエスケープを正しく処理し、行内コメントの取り扱いを改善。
  - `config._load_env_file` で OS 環境変数を保護する protected 設定を導入（.env.local が OS 環境変数を上書きするのを防ぐ）。
- process_priority 周りで権限不足等が発生してもサービスが止まらないように例外を捕捉して警告に落とすように修正。

### Security
- config_setup による .env 生成時に「.env を絶対に Git にコミットしないこと」を明示。
- 必須秘密情報（J-Quants トークン、kabu API パスワード）は Settings 経由で `_require()` により未設定時に起動時エラーを出すようにしている（誤った起動を防止）。

### Notes / Operational details
- 監視プロセスは MONITOR_POLL_INTERVAL 環境変数で秒数を上書き可能（不正値や 0/負数はデフォルト 60 秒にフォールバック）。
- run_monitoring は監視データを常に本番用 sqlite_path に書き込む設計（環境に依存しない監視一元化）。
- run_execution は `KABUSYS_ENV=paper_trading` の場合に paper 用 SQLite（data/paper_trading.db）と Mock ブローカーを使用し、本番 DB とは完全に分離される。
- ログは標準で stdout に出力する（cron/task scheduler 環境での取り扱いを容易にするため stderr ではなく stdout を使用）。
- CPU affinity の設定は環境と権限に依存するため、失敗時は警告でスキップされる。

---

将来のリリースでは以下の点を予定・検討中:
- research/factor_research の完全実装（ファクター計算の SQL 実行部分の完成）
- 銘柄別 lot_size マスタの導入による position_sizing の拡張
- より包括的なユニットテストと CI ワークフローの整備

======

（参考: リポジトリ内の主なコマンド／スクリプト）
- 対話的 .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視プロセス起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]