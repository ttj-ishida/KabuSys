# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在のパッケージバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-21
初回公開リリース。

### 追加 (Added)
- 基本アプリケーションとランタイムスクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を利用）。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 実行中は PID ファイル (data/execution.pid) を使用し、停止フラグ (data/stop_requested.flag) による安全停止をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は警告を出してデフォルトにフォールバック。
    - Monitoring は環境にかかわらず本番用の sqlite_path を使用して監視データを保存。
    - 停止フラグ (data/stop_requested.flag) によりループを終了。
- 環境設定・管理
  - config.py
    - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env / .env.local の読み込み順序と OS 環境変数保護（既存 OS 環境変数は上書きされない）。
    - Settings クラスを提供。J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / ログレベル等のプロパティを定義。
    - PAPER_FILL_MODE 等の入力検証（有効な値のみ許容）。
- 設定ユーティリティ・検証
  - config_setup.py
    - 対話式 .env 作成ウィザード。既存 .env 読み込み・編集、シークレット項目のマスク表示、ファイル保存。
    - デフォルト値・選択肢を提示し、生成された .env を安全に書き出す。
  - validate_config.py
    - 起動前に環境変数や config/*.yaml の存在／整合性を検証する CLI。
    - `--strict` オプションで警告も失敗扱いにできる。
    - PyYAML がない場合は YAML 検証をスキップして警告を出す。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルのソート・候補選定 (select_candidates) と重み計算 (calc_equal_weights, calc_score_weights) を実装。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく発注株数計算（単元株丸め、aggregate cap スケーリング、cost_buffer 対応）。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 共通のログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて導入。
    - ログディレクトリの解決順・作成とログレベル解決ロジックを実装。ファイル出力ができない場合は console のみで継続。
    - デフォルトログディレクトリ: logs/、保持日数: 30 日。
  - utils/process_priority.py
    - Windows/Linux/macOS 間の差を吸収するプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を提供。psutil を使用して権限エラー等は警告でスキップ。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から集計して検証レポートを生成。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL を判定するしきい値を定義（稼働率 >= 99%、注文成立率 >= 90% 等）。
    - 日付フィルタ（--from / --to）と DB パス指定 (--db) に対応。
- パッケージ情報
  - __init__.py にてバージョンを 0.1.0 と定義。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- .env パーサーの堅牢化（config._parse_env_line）
  - `export KEY=val` 形式をサポート。
  - シングル／ダブルクォート内のバックスラッシュエスケープ対応。
  - クォートなし値の行内コメント処理（空白直前の `#` をコメントとみなす）。
- DB 初期化において監視テーブルが存在しない場合でも安全に作成する初期化呼び出しを導入（init_monitoring_db を startup で呼び出すことで冪等性を確保）。

### 既知の制限・注意事項 (Known issues / Notes)
- position_sizing.calc_position_sizes
  - 銘柄ごとの lot_size を将来的に対応予定（現状は全銘柄共通の lot_size を想定）。コード内に TODO コメントあり。
  - open_prices に欠損 (0.0) がある場合、エクスポージャーが過少見積りされる可能性がある旨の注意（価格フォールバック未実装）。
- validate_config の YAML 検証は PyYAML に依存。未インストール時は検証をスキップして警告になる。
- process_priority / set_cpu_affinity は権限不足や未サポート環境で失敗する場合があり、その場合は警告を出してスキップする実装。
- run_monitoring は Monitoring 用 DB として常に Settings.sqlite_path を参照する（環境による分離は行わない設計）。
- Paper Trading 実行時は MockBrokerClient を使用する設計を想定（実装側での切り替え）。paper_trading 用 DB と本番 DB は完全に分離することを意図。

### セキュリティ (Security)
- .env ファイル生成時にシークレット項目（トークン・パスワード）は出力時にマスク表示するが、.env ファイル自体は生成されるため、必ず Git 等にコミットしないことを README 等で注意する必要あり（config_setup.py のヘッダに注意文あり）。

---

注: 本 CHANGELOG は提供されたコードベースから推測して作成した初期リリースの要約です。実際のリリースノートに含める日付・担当者・変更範囲等はプロジェクトのポリシーに合わせて調整してください。