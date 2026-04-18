# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。  
このリポジトリの初期リリースを表すバージョン情報をまとめています。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初期機能群を実装して公開。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を介して本番/モックブローカーを切替え。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag を監視して安全に停止可能（PID ファイル: data/execution.pid）。
    - 起動時にプロセス優先度を "high" に設定するユーティリティ呼び出しを行う。
    - duckdb/SQLite の接続管理（起動時の監視テーブル初期化を含む）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。不正値はデフォルトにフォールバックし、警告を出力。
    - 監視は環境にかかわらず本番の sqlite_path（デフォルト: data/monitoring.db）を使用する仕様。
    - data/stop_requested.flag による停止検知、KeyboardInterrupt による終了処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルートに基づく: .git または pyproject.toml を起点）を実装。読み込み順は OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化。
    - .env パーサは export KEY=val 形式、クォート付き値、インラインコメント等に対応。
    - Settings クラスを提供し、環境変数から各種設定（DB パス、API トークン、監視閾値、環境種別など）を取得可能。環境値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
    - settings = Settings() の単一インスタンスをエクスポート。

  - config_setup.py
    - 対話式ウィザードで .env を初期生成・更新する CLI を実装。
    - 秘匿値は表示時にマスク。生成時に .env 保存内容の確認を行いユーザー承認後に保存。
    - デフォルト値・選択肢を定義済み（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KILL_FLAG_CLEAR_ON_START 等）。

  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config YAML の存在/パース検証（PyYAML がインストールされている場合）。
    - KABUSYS_ENV=live の場合に本番ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実施。
    - --strict フラグで警告も失敗（exit(1)）扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を選出（同スコア時は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコアに応じた重み付け（全スコアが 0 の場合は等配分にフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用し、過度に露出したセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（"bull"/"neutral"/"bear"）に基づく投下資金乗数を返す（未知のレジームは警告の上フォールバック 1.0）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて発注株数を計算。
      - risk_based: 許容リスク率、ストップロス率に基づく株数算出。
      - equal/score: 重みから単元株（lot_size）丸め、1 銘柄上限・集計上限（available_cash）を考慮。
      - cost_buffer を用いた保守的なコスト見積りと、available_cash 超過時のスケーリング（端数処理のための remainder ベースの追加配分ロジックを実装）。
      - lot_size（デフォルト 100）に基づく丸め実装と将来の拡張ポイント明記。

- 分析 / 研究
  - research/factor_research.py（骨格実装）
    - Momentum/Value/Volatility/Liquidity 等のファクター計算設計を実装（DuckDB 接続を受け、prices_daily / raw_financials テーブルのみを参照する方針）。
    - モメンタム計算の定数（1M/3M/6M、MA200、ATR など）を定義。関数 calc_momentum の API と意図を定義（実装途上の箇所あり）。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成ツールを追加。
    - 指定期間（--from / --to）で trade_logs / system_status / risk_logs から各種指標を算出し、PASS/FAIL 判定を行う。
    - デフォルト閾値: 稼働率 >= 99.0%、注文成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - DB パスは引数 --db または環境変数 PAPER_TRADING_SQLITE_PATH、デフォルトは data/paper_trading.db。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して監視用テーブルの冪等な初期化処理を実施（run_* スクリプトから呼び出し）。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 標準出力 (stdout) 用 StreamHandler と、日次ローテーションの TimedRotatingFileHandler をルートロガーに設定するユーティリティを実装。
    - ログディレクトリ自動作成、既存ハンドラの flush/close 後のクリア、ログレベル解決ロジックを実装。
    - ファイルハンドラ作成失敗時はコンソール出力のみで継続する安全設計。

  - utils/process_priority.py
    - Windows/Linux/Mac の差分を吸収してプロセス優先度（nice / Windows priority class）を設定するユーティリティを実装。
    - set_cpu_affinity による CPU コアピンニングも提供（未指定時は何もしない）。権限不足時は警告を出してスキップ。

### Changed
- n/a（初期リリースのため履歴変更なし）

### Fixed
- n/a（初期リリース）

### Deprecated
- n/a

### Security
- n/a

---

補足 / 運用メモ
- デフォルトのファイルパス
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID / フラグ: data/execution.pid, data/stop_requested.flag など
- 環境変数の自動ロード
  - OS 環境 > .env.local (上書き) > .env (未設定時のみ) の優先順位でロードされる。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- run_monitoring はモニタリング目的で本番 sqlite_path を常に使用するため、テスト時や開発時の扱いに注意。
- run_execution は KABUSYS_ENV に応じて paper_trading 用 DB に切り替わり、ペーパーモード時は発注がモック処理され DB に記録される（本番データと分離）。
- .env は絶対にリポジトリにコミットしないことを推奨（config_setup.py のヘッダに注記あり）。

将来的な TODO（コード内に注記あり）
- position_sizing: 銘柄ごとの lot_size を stocks マスタから読む拡張
- risk_adjustment: price 欠損時のフォールバック価格導入
- research/factor_research: calc_momentum 等の完全実装と単体テスト追加

--- 

本 CHANGELOG はコードベースからの実装内容推測に基づいて作成しています。実際のリリースノートとして使用する場合は、変更を加えたコミット／差分と照合の上で必要に応じて補正してください。