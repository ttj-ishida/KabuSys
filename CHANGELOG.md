# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [0.1.0] - 2026-04-17
初回リリース

### 追加
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 実行用エントリポイント
  - run_execution: 実取引/ペーパートレード双方に対応する ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（data/paper_trading.db をデフォルト）を使用し、MockBrokerClient（BrokerClientFactory 経由）で完全分離されたペーパートレードを行う旨をドキュメント化。
    - エンジンは別スレッドで稼働し、data/stop_requested.flag による停止、data/execution.pid を PID ファイルとして使用。
    - リスク管理のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を Engine 起動時に適用。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
    - data/stop_requested.flag による停止検出、例外発生時のログ記録と継続処理を実装。

- 設定管理とセットアップ
  - Settings クラスを追加（src/kabusys/config.py）。
    - .env の自動読み込みロジック（.env → .env.local、OS 環境変数優先）を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 各種環境変数取得用プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH ほか）を提供。
    - PAPER_FILL_MODE の検証（有効値チェック）、KABUSYS_ENV / LOG_LEVEL のバリデーション、各閾値設定（CPU/MEM/ディスク）を定義。
  - 環境設定ウィザード CLI を追加（src/kabusys/config_setup.py）。
    - 対話式で .env を生成／更新するウィザード。secret 項目はマスク表示、既存 .env の読み込み・再利用に対応。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と YAML パース検証（PyYAML が存在する場合）、本番用ガードを実装。
    - --strict オプションで警告をエラー扱いにする機能を実装。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順、同点は signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア加重配分。スコア合計が 0 の場合は等分配へフォールバックし警告を出力。
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に当該セクターの新規候補を除外。unknown セクターは上限チェック対象外。
    - calc_regime_multiplier: 市場レジーム ('bull','neutral','bear') に基づく投下資金乗数を返す。未知レジームは 1.0 にフォールバックし警告を出力。
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method ('risk_based','equal','score') に応じた発注株数計算を実装。
      - 単元株（lot_size）で丸め、per-stock 上限、aggregate cap（available_cash）超過時のスケーリング、cost_buffer による保守的見積り、残差分の優先配分ロジックを実装。
      - 価格欠損時は銘柄をスキップ。

- 研究用ファクター計算
  - research/factor_research（src/kabusys/research/factor_research.py）
    - DuckDB 接続を受け取り、prices_daily/raw_financials を参照してモメンタム・ボラティリティ等のファクターを計算する関数群を実装（例: calc_momentum, calc_volatility）。
    - MA200、ATR、各種リターン等を営業日ベースで計算。データ不足時は None を返す設計。

- ユーティリティ
  - process_priority（src/kabusys/utils/process_priority.py）
    - set_process_priority(level) を実装（Windows の優先度クラスと POSIX の nice 値を抽象化）。
    - set_cpu_affinity(cpu_count) を実装（指定コア数に固定）。権限不足や未対応環境では警告を出してスキップ。
    - 呼び出し側はプラットフォームを意識せずに優先度設定を要求可能。

- 運用ツール
  - tools/paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を参照して稼働率、注文成功率、送信率、レイテンシ（P95 等）を算出しレポート出力する CLI を実装。
    - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）と Pass/Fail 判定を実装。
    - --from / --to / --db オプションで期間・DB を指定可能。

- DB/監視初期化
  - monitoring.monitoring_db.init_monitoring_db を利用して、run_execution/run_monitoring 起動時に監視テーブルの存在を保証（冪等）する処理を追加。

### 変更（設計上の注意・フォールバック）
- .env 読み込みの堅牢化
  - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート（src/kabusys/config.py のパーサを強化）。
  - 自動読み込みはプロジェクトルート判定 (.git または pyproject.toml) に基づき実行。プロジェクトルートが特定できない場合は自動ロードをスキップ。

- 環境変数優先度
  - OS 環境変数を保護するため、.env(.local) 読み込み時に既存の OS 環境変数は上書きしない（.env.local は override=True だが protected により OS 環境変数は上書きされない）。

- エラー耐性強化
  - run_monitoring のポーリング中に monitor.check_once() が例外を投げてもループ継続するように例外ハンドリングを追加。
  - DB パスや YAML パースに問題があっても検証ツールが警告／エラーを出すが、起動時の致命的障害は明確にログに出力する方針。

### 修正（バグ修正・フォールバックの明示）
- MONITOR_POLL_INTERVAL の取り扱いを堅牢化（src/kabusys/run_monitoring.py）
  - 0 以下や不正な値が与えられた場合はデフォルト（60 秒）にフォールバックし警告を出力。

- データ不足時の安全な処理
  - factor_research の移動平均や ATR 等でデータ不足時には None を返すようにして上流での異常終了を防止。

- process_priority のフォールバック
  - 未対応 OS・権限不足時に警告を出して処理をスキップする実装に変更（例: Windows 定数が存在しない環境や nice が使えない環境）。

### 既知の問題 / TODO
- position_sizing.calc_position_sizes:
  - price が 0.0（欠損）時にエクスポージャーが過少に見積もられ、結果としてブロックが外れる可能性がある旨をコメントで追記。将来的に前日終値や取得原価等のフォールバックを検討中。
- sector_map による unknown セクターは apply_sector_cap で上限適用対象外にしているが、運用方針により挙動を変更する可能性あり。
- 単元株（lot_size）は現状グローバル固定（100）を想定。将来的に銘柄別単位対応を検討。

---

今後のリリースでは、ExecutionEngine / BrokerClient 等の内部実装、監視・アラート回り（LINE 通知の実装）、詳細なテストカバレッジ、並列実行・性能チューニング等を順次追加していく予定です。