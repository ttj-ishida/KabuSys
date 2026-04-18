# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従っています。  
当リポジトリでの初回公開リリースを記録しています。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本 CLI / ランチャースクリプトを追加
  - run_execution.py — ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は専用の Paper Trading DB（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用して本番 DB と完全に分離する。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
  - validate_config.py — .env と config/*.yaml を検証する CLI。--strict オプションで警告を失敗扱いにできる。
  - config_setup.py — 対話式 .env ウィザード。秘密値はマスク表示、生成した .env は Git にコミットしない旨のヘッダを付与して保存する。
  - tools/paper_verification_report.py — Paper Trading 向けの検証レポート生成ツール。期間指定 (--from / --to) と DB パス指定 (--db) に対応。

- 設定管理
  - config.py: Settings クラスを導入し、環境変数の取得・バリデーションを集中管理。
  - .env 自動ロード機能を実装（プロジェクトルートに基づき .env、.env.local を順次読み込み）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。

- 環境変数パーサーの追加
  - .env の行パースを頑健に実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。

- ポートフォリオ構築モジュールを追加（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中上限処理）、calc_regime_multiplier（市場レジームに応じた資金乗数）
  - portfolio.position_sizing: calc_position_sizes（risk_based / equal / score の割当方式、単元株切り捨て、aggregate cap のスケールダウンロジック、手数料/スリッページ見積り cost_buffer 対応）

- 低レベルユーティリティ
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティ（set_process_priority / set_cpu_affinity）。Windows と POSIX 系の差分を吸収。

- リサーチ / ファクター計算
  - research/factor_research.py: DuckDB 接続を受け取り、Momentum / Volatility / Liquidity / Value 系のファクターを計算する関数群（例: calc_momentum, calc_volatility）。200日移動平均や ATR 等を SQL ウィンドウ関数で計算。

- モニタリング DB 初期化
  - init_monitoring_db 呼び出しを run_execution/run_monitoring の起動時に実行し、監視テーブルが存在することを冪等的に保証。

### 変更 (Changed)
- 実行・監視プロセスの実行ポリシー
  - run_execution.py / run_monitoring.py 起動時にプロセス優先度を "high" に設定する処理を追加（set_process_priority 呼出し）。
  - run_execution はスレッドで ExecutionEngine をデーモン実行し、data/execution.pid を使用する仕組みを提供。停止フラグ（data/stop_requested.flag）検知による安全停止に対応。

- 設定の有効値チェック
  - Settings.env と Settings.log_level に対する厳密な検証を導入（有効な選択肢以外は ValueError を発生）。
  - PAPER_FILL_MODE（paper trading の fill モード）に対して有効値検査を追加（instant/partial/never/reject）。

- Paper Trading の分離強化
  - Paper Trading 環境では paper_sqlite_path を使用し、本番監視 DB と完全分離する挙動を明記・実装。

- .env 読み込み順序
  - OS 環境変数 > .env.local > .env の優先順位でロードする仕様に変更。デフォルトの挙動は環境変数優先。

### 修正 (Fixed)
- ポーリング間隔の堅牢化
  - run_monitoring._get_poll_interval(): 環境変数 MONITOR_POLL_INTERVAL が不正（非整数・0 以下など）な場合に警告を出しデフォルト（60 秒）へフォールバックするよう改善。time.sleep に渡せない値を回避。

- ロバストネス向上
  - run_monitoring の監視ループ内で monitor.check_once() が例外を投げてもループを継続し、例外スタックをログ出力して次ポーリングへ回復するように変更。
  - Paper verification レポート生成でテーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値を返すよう保護。

- .env ウィザード入出力改善
  - config_setup.py の run_wizard/_prompt にてシークレットはマスク表示、Enter で既存値やデフォルトを維持可能にし、キャンセル時の挙動を明確化。

### 破壊的変更 (Breaking Changes)
- なし（初回公開のため互換性影響はありません）。ただし、Settings の厳密検証により未設定や不正な環境変数があると起動時に例外が発生するため、既存環境では .env を整備する必要があります。

### セキュリティ (Security)
- なし特記事項。ただし .env ファイルの生成時に「.env を絶対に Git にコミットしないこと」という注意をヘッダに出力。

---

備考:
- 本リリースは「初期機能実装」を中心としたものです。ExecutionEngine や SystemMonitor 本体、Broker クライアント等の詳細実装（ビジネスロジック）は別モジュールに分離されていますが、本 CHANGELOG は提供されたコード範囲から推測して記載しています。