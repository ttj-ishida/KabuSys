# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。  
このファイルはコードベース（src/kabusys/*.py）から推測して作成したリリースノートです。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: KabuSys、バージョン: 0.1.0（src/kabusys/__init__.py）
- 起動スクリプト
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（data/paper_trading.db をデフォルト）で本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、実行 PID を data/execution.pid に保存（Engine 側）。
    - duckdb および sqlite 接続を利用。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
- 環境設定 / 検証ツール
  - config_setup: 対話式 .env 作成・更新ウィザードを追加（src/kabusys/config_setup.py）。
    - シークレット項目は入力/表示時にマスク、選択肢・デフォルトあり、保存前に確認プロンプト。
  - validate_config: .env と config/*.yaml の起動前検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 等の妥当性確認、DB パスや config ファイル存在チェック、KABUSYS_ENV=live 時の追加ガード。
    - --strict オプションで警告も失敗扱いにできる。
- 設定管理
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env 自動読み込み機能（.env / .env.local の順、OS 環境変数保護）を実装。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 形式・クォート・エスケープ・インラインコメント等に対応。
    - 各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、各種閾値、KABUSYS_ENV 判定等）を提供し、値検証を行う。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）など。
- ロギング / プロセス管理ユーティリティ
  - logging_setup: 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）を設定。
    - LOG_DIR, LOG_LEVEL による動作切替、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時はファイル出力をスキップして継続。
  - process_priority: クロスプラットフォームでのプロセス優先度（Windows の優先度クラス / POSIX の nice）と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(cpu_count) を提供。権限不足など失敗時は警告でスキップ。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder: シグナルから候補選定、等重/スコア加重の重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数計算（calc_regime_multiplier）。
    - 不明セクターは "unknown" 扱いで上限適用外にする挙動を採用。
  - position_sizing: 発注株数算出ロジックを追加（calc_position_sizes）。
    - allocation_method に "risk_based"/"equal"/"score" をサポート。
    - lot_size（単元）で丸め、per-position 上限や aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り等を実装。
    - 価格欠損時のスキップ、ログ出力による説明。
- 研究 / ファクター計算スケルトン
  - research/factor_research: モメンタム・ボラティリティ・バリュー等ファクターの計算モジュール基盤を追加（DuckDB を用いた prices_daily, raw_financials 参照を想定）。モメンタム計算関数 calc_momentum の実装開始（スキャン幅・パラメータ定義あり）。
- ツール
  - tools/paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み込み、稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を表示。
    - デフォルト閾値を設定（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ機能（--from/--to）。
- DB 初期化フック
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルが存在することを保証（起動時に冪等に呼び出す設計）。

### Changed
- ログ出力の既定動作を整備
  - ハンドラが既に存在する場合はクリアしてから再設定することで二重出力を防止。
- .env 読み込みの保護
  - OS 環境変数を保護するために .env の読み込み順序と上書きポリシーを明確化（.env は既存値を上書きせず、.env.local は上書き可能だが OS の既存キーは保護）。

### Fixed
- CLI の堅牢性向上
  - validate_config や config_setup での中断（EOF/KeyboardInterrupt）時に整然と終了・メッセージを出すように改善。
- モニタリング / 実行の安全停止
  - 停止フラグ（data/stop_requested.flag）検出時に適切にループ/スレッドを終了する挙動を実装。

### Notes / Known limitations
- research/factor_research はモメンタム部分の実装が途中で終端している（ファイル末尾が切れている）。完全なファクター計算の完成は今後の作業が必要。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価等）は TODO コメントとして残しているため、実運用前に検討・実装が推奨される。
- process_priority と set_cpu_affinity は環境依存で権限やプラットフォームによって失敗する可能性があり、その場合は警告を出してスキップする。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラをスキップする設計。ログ収集要件がある環境では LOG_DIR の権限確認を推奨。

---

（この CHANGELOG は配布されたソースコードの内容をもとに自動的に推測して作成しました。実際のリリースノートと差異がある可能性があります。必要に応じて日付・文言を調整してください。）