# Changelog

すべての変更は「Keep a Changelog」準拠で記載しています。  
フォーマット: 変更種別ごとに箇条で記載。各バージョンにはリリース日を付与しています。

<!-- 例: Unreleased セクションを使う場合はここに追記できます -->

## [0.1.0] - 2026-04-19

初回リリース。本リリースでは自動売買システム KabuSys の起動スクリプト群、設定管理、監視/発注に関連するコンポーネント、ポートフォリオ構築ユーティリティ、ユーティリティ関数群、Paper Trading 検証ツールなどを提供します。

### Added
- 起動スクリプト（デーモン/サービス）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag ファイルを検知して安全に終了。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する仕様。
    - DuckDB 接続も併用（duckdb_path）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、Paper Trading 用 DB（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを生成。
    - ExecutionEngine を別スレッドで実行し、stop flag を検知して安全に停止。
    - 実行用 PID ファイル管理（data/execution.pid）をサポート。

- 設定関連 CLI / ユーティリティ
  - config.py
    - .env 自動読み込み機能（.env / .env.local）を実装（プロジェクトルートは .git または pyproject.toml から探索）。
    - コピー保護: OS 環境変数を protected として上書きされないよう扱う。
    - .env 行パーサは export 形式、引用符、エスケープ、インラインコメント等に対応。
    - Settings クラスを導入: 環境変数の型変換・バリデーションを集約（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - paper_trading 用の paper_sqlite_path、paper_fill_mode の検証ロジックを追加。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加（対話入力 → .env 書き出し）。
    - 標準的な設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KILL_FLAG_CLEAR_ON_START, LINE 関連など）をサポート。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルの確認、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在/パース（PyYAML がインストールされている場合）など。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（ログの日時ローテーション）を設定する共通ユーティリティを追加。
    - ログレベルおよびログディレクトリは引数 / 環境変数 / デフォルトの優先で決定。ファイルハンドラは日次ローテーション、30 日分保持。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows/Linux/Mac の差分を吸収してプロセス優先度（high/normal/low）を設定する関数を追加。
    - CPU affinity を設定する set_cpu_affinity 関数を追加（指定が None のときは何もしない）。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップ。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates：BUY シグナルをスコアでソートして上位 N を選定。
    - calc_equal_weights：等金額配分の重み計算。
    - calc_score_weights：スコア加重配分、全て 0 の場合は等金額にフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクター集中上限チェック（既存保有比率に基づき新規候補の除外）。
    - calc_regime_multiplier：市場レジームに基づく投下資金乗数（bull/neutral/bear のマッピング及び未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes：等配分 / スコア配分 / リスクベース配分に基づく株数決定ロジック（単元株丸め、per-stock 上限、aggregate cap スケーリング、cost_buffer を加味した見積り等を実装）。
  - portfolio/__init__.py にて上記関数群をエクスポート。

- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポートを生成する CLI を追加。
    - 日付フィルタ（--from, --to）や --db で DB パスを指定可能。
    - Pass/Fail 基準の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を内蔵。
    - P95 計算、NULL/データ欠損時の安全ハンドリングを実装。

- 研究用モジュール（初期実装）
  - research/factor_research.py
    - ファクター計算モジュール（モメンタム、ボラティリティ、バリュー、流動性等）の骨格を追加。DuckDB の prices_daily / raw_financials を参照する設計。関数 calc_momentum などの計算ロジックを開始（注: 一部関数は実装途中の可能性あり）。

- パッケージメタ
  - __init__.py にてバージョンを 0.1.0 として設定。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / 動作上の重要なポイント
- .env 自動ロード
  - デフォルトでプロジェクトルートの .env と .env.local を読み込みます。OS 環境変数は保護され上書きされません。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- PAPER TRADING の分離
  - Paper Trading 実行時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番用 SQLite と完全に分離します。
- プロセス優先度
  - 起動スクリプトは起動直後に set_process_priority("high") を呼びます。権限がない環境では警告が出てスキップします。
- ログ
  - デフォルトで stdout にログを出力しつつ、logs/<app_name>.log に日次ローテーションで出力します。ログディレクトリの作成に失敗した場合はファイル出力を諦めて stdout のみになります。
- 監視ループ停止方法
  - 監視/実行スクリプトはプロジェクト内 data/stop_requested.flag を監視して安全に終了します（手動でフラグを作成/削除する運用を想定）。
- 設定検証
  - validate_config は PyYAML 未導入時に YAML 内容検証をスキップします（警告）。PyYAML があると YAML のパース検証も行います。

---

今後の予定（例）
- research/factor_research の完全実装とユニットテスト追加
- ExecutionEngine / BrokerClient 周りのテスト補強、MockBroker の挙動検証
- 各モジュールに対するユニットテスト・ドキュメントの拡充
- CLI のサブコマンド統合検討（起動/停止管理の簡素化）

（必要に応じて Unreleased セクションを設け、次回リリース計画を記載してください。）