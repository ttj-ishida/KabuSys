# Changelog

すべての変更は「Keep a Changelog」準拠で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回公開リリース。日本株自動売買システム "KabuSys" の基本コンポーネントを追加しました。以下はコードベースから推測できる主要な機能・改善点の一覧です。

### 追加 (Added)
- 全体
  - パッケージの初期バージョンを定義（__version__ = "0.1.0"）。
  - モジュール構成: data / strategy / execution / monitoring 等の骨格を含むモジュール群を提供。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV に応じて paper_trading モードでは専用 SQLite（data/paper_trading.db デフォルト）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てと ExecutionEngine の開始・停止制御を実装。
    - 停止フラグファイル (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用した外部停止制御をサポート。
    - プロセス優先度を 'high' に設定して起動（utils.process_priority）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) の検出でループを終了。

- 設定管理
  - config.py
    - .env 自動ロード（プロジェクトルートの検出を行い .env/.env.local を読み込む。OS 環境変数は保護）。
    - 複雑な .env 行パース実装（export プレフィックス、クォートとエスケープ、インラインコメント処理など）を提供。
    - Settings クラスで各種設定値（J-Quants, kabuAPI, DB パス, PID/kill flag パス, モニタ閾値, 環境判定フラグ 等）を取得可能に。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
    - KABUSYS_ENV、LOG_LEVEL の妥当性チェック。

  - config_setup.py
    - .env 作成/更新のための対話式ウィザードを追加。既存 .env の読み込みと既存値の再利用が可能。
    - 主要設定項目（KABUSYS_ENV、API トークン、DB パス、ログ設定、Kill Switch 動作等）を対話的に入力・保存。

  - validate_config.py
    - 起動前の設定検証ツールを追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリチェック、config/*.yaml ファイル存在と YAML パース検証（PyYAML が存在する場合）などを実施。
    - --strict オプションで警告も失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし WARN ログを出力。

  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)：既存保有のセクター比率が上限を超える場合、新規候補をフィルタリング（"unknown" セクターは除外しない）。
    - レジーム乗数 (calc_regime_multiplier)：regime ラベルに応じた投下資金乗数を返す（bull/neutral/bear マッピング、未知レジームはフォールバックで 1.0 として警告）。

  - portfolio/position_sizing.py
    - ポートフォリオ価値・現金・価格情報に基づいた株数決定ロジックを実装。
    - allocation_method により "risk_based"（リスクベース）または "equal"/"score" をサポート。
    - 単元 (lot_size) による丸め、max_position_pct による個別上限、max_utilization による総投下上限、cost_buffer（手数料・スリッページ見積り）を考慮した aggregate cap の調整処理を実装。
    - aggregate 超過時はスケールダウンして端数分を残差順に lot 単位で再配分するアルゴリズムを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL / 引数に応じた解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラをクリアして多重設定を防止。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定を実装（psutil ベース）。
    - 標準レベル: high / normal / low。権限不足や未対応 OS の場合は警告とともにスキップ。

- モニタリング / 検証ツール
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトで呼び出して監視テーブルの存在を保証（冪等）。
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）からシステム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）等を集計して判定（PASS/FAIL）を出力。
    - デフォルトしきい値:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付範囲フィルタ（--from, --to）と --db オプションをサポート。

- 研究モジュール（未完成の一部）
  - research/factor_research.py
    - モメンタム・ボラティリティ・ファクター等の計算ロジック（設計と定数）を追加。ただしファイル末尾で計算関数の実装途中（calc_momentum の冒頭で終了）になっており、未完了箇所あり。

### 変更 (Changed)
- （初回リリースのため過去変更なし）

### 修正 (Fixed)
- （初回リリースのため過去修正なし）

### 注意事項（運用上の重要な挙動）
- run_monitoring は「監視 DB として常に本番 sqlite_path を使用する」ため、開発環境でも監視データは本番用パスに書き込まれる点に注意（設計上の意図として明記）。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB と分離する設計。
- .env の自動読み込みはプロジェクトルートの検出に依存するため、配布後やテスト環境でプロジェクトルートが検出できない場合は自動ロードをスキップする。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- KILL_FLAG_CLEAR_ON_START が本番（live）で "1" に設定されていると Kill Switch が自動クリアされ、危険となる旨の警告が validate_config に含まれる。

### 既知の制限 / TODO（コード内コメントより推測）
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積もられる問題があり、前日終値や取得原価等のフォールバック価格を使う改善が検討中。
- portfolio/position_sizing:
  - 将来的な拡張として銘柄別 lot_size をサポートする設計に変更する可能性あり。
- research/factor_research は一部実装が途中のため、本番利用には不十分。

---

開発に関する質問やリリース内容の補足が必要であればお知らせください。