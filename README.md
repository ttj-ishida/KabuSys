# KabuSys

バージョン: 0.1.0

KabuSys は日本株自動売買向けの軽量なフレームワークです。シグナルに基づく発注エンジン、ブローカークライアント抽象化、リスク管理、起動時のリコンシリエーション、監視ループ、カレンダー/ニュース収集などを含みます。ローカル開発やペーパートレードを想定したモック実装を備え、本番（live）環境にも対応する設計になっています。

---

目次
- プロジェクト概要
- 機能一覧
- 必須・任意の環境変数
- セットアップ手順
- 使い方（主なコマンド）
- .env と自動ロードの挙動
- 実行中の挙動（kill/pid/stop フラグ、paper_trading の DB 分離など）
- ディレクトリ構成（主要ファイルと役割）

---

プロジェクト概要
- シグナル駆動の発注エンジン（ExecutionEngine）
  - 発注前後に 3 段階のリスクガード（Gate1/2/3）を適用
  - Signal Queue からシグナルを読み発注し、WebSocket の push をドレインして状態同期
- ブローカークライアント抽象化（BrokerAPIProtocol）
  - 本物の kabu-station クライアント実装（KabuStationClient）と、テスト用の MockBrokerClient を提供
- 注文状態管理
  - OrderRecord（状態遷移ロジック）と SQLite を用いた OrderRepository（永続化）
  - OrderManager により発注フロー（生成 → 送信 → 同期 → キャンセル）を管理
- 起動時リコンシリエーション（Reconciler）
  - OrderSent（未確定）レコードをブローカーと突合し自動復旧
  - ブローカーポジションとローカル推定ポジションの差分検出
- 監視ループ（SystemMonitor 起動スクリプト）
  - 監視データを SQLite に記録し定期ポーリング実行
- データ関連ユーティリティ
  - DuckDB を用いたマーケットカレンダー管理、シグナル/ポートフォリオ読み込み、ニュース収集等

機能一覧（要点）
- 環境毎動作（development / paper_trading / live）
  - paper_trading では MockBrokerClient を利用し、paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）へ書き込む
- 発注フローのクラッシュ耐性設計（OrderSent の永続化、broker_order_id の二相永続化等）
- RiskManager（Gate1/2/3）
  - 余力、重複、ポジション上限、レートリミット、サーキットブレーカー、ドローダウン監視
- 起動時の自動リコンシリエーション（OrderSent -> broker 照合）
- WebSocket push の処理と push による同期・Gate3 評価
- 設定ウィザード（config_setup）・設定検証 CLI（validate_config）
- DuckDB / SQLite によるデータ永続化、ニュース収集（RSS）、JPX カレンダー更新

必須 / 任意の環境変数（主なもの）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意（代表）:
  - KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - LOG_LEVEL — デフォルト: INFO
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
  - PAPER_FILL_MODE — paper_trading の fill 動作（instant / partial / never / reject）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- 補足:
  - 設定検証ツールは .env と config/*.yaml の存在/パースもチェック（PyYAML 未導入時は内容検証がスキップ）

セットアップ手順（ローカル開発想定）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 必要パッケージをインストール（最低限の例）
   - pip install duckdb httpx websocket-client defusedxml
   - PyYAML を入れると config/*.yaml の内容チェックが有効化されます: pip install pyyaml
   - その他、使用する機能に応じて依存パッケージを追加してください
3. .env を準備
   - 対話式ウィザードで作るのが簡単:
     - python -m kabusys.config_setup
   - 手動で作る場合はリポジトリルートに .env を配置（.env.example があれば参照）
4. 設定を検証（任意）
   - python -m kabusys.validate_config
   - 警告も FAIL として扱いたい場合: python -m kabusys.validate_config --strict

使い方（主なコマンド）
- 環境設定ウィザード（.env を作成・更新）
  - python -m kabusys.config_setup
  - 対話式に入力し .env を生成します（.env のデフォルト保存場所はプロジェクトルートの .env）
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があっても exit code 1 を返します
  - PyYAML がインストールされていれば config/*.yaml の YAML パースも行います
- 実行エンジン起動（本番/ペーパーのセッション実行）
  - python -m kabusys.run_execution
  - run_execution は KABUSYS_ENV によって振る舞いが変わります:
    - development / paper_trading → MockBrokerClient を使用（paper_trading は paper_trading 用 SQLite へ）
    - live → 現在は NotImplementedError（将来実装）
- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を上書き可能（デフォルト 60 秒）
- ログ設定
  - ログレベルは LOG_LEVEL 環境変数で制御（DEBUG / INFO / WARNING / ERROR / CRITICAL）

.env と自動ロードの挙動
- 自動ロード順序:
  - OS 環境変数（優先）
  - プロジェクトルートの .env
  - プロジェクトルートの .env.local（.env.local は既存 OS 環境変数を保護しつつ上書き）
- 自動ロードはデフォルトで有効。無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- .env の読み取りは .git や pyproject.toml を基準にプロジェクトルートを探索するため、実行カレントディレクトリに依存しません

実行時の運用上のポイント
- 停止フラグ / PID:
  - stop_requested.flag（data/stop_requested.flag）を設置するとループが停止します
  - エンジンは PID ファイル（デフォルト data/execution.pid）を書きます
- kill.flag:
  - settings.kill_flag_path（デフォルト data/kill.flag）を検査し、存在すると kill_switch を発動するか起動を拒否します
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag を削除して起動します（本番では推奨されません）
- DB の分離:
  - paper_trading では paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番監視 DB（SQLITE_PATH）と分離されます
- MockBrokerClient:
  - paper_trading / development 環境では MockBrokerClient を利用し、fill_mode によって発注挙動を変更できます（instant / partial / never / reject）

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数読み込み・Settings クラス（設定アクセス）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine を起動するスクリプト（メインエントリ）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py — BrokerAPIProtocol, データモデル, ファクトリ
    - kabu_client.py — kabuステーション REST API クライアント（httpx）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings を受け取って適切なブローカークライアントを生成
    - order_record.py — Order の状態遷移ロジック（状態マシン）
    - order_repository.py — SQLite による注文永続化
    - order_manager.py — ビジネス向け注文 API（create/send/sync/cancel）
    - execution_engine.py — シグナル・発注セッション（Engine本体）
    - reconciler.py — 起動時リコンシリエーション（OrderSent の突合）
    - risk_manager.py — Gate1/2/3 リスクガード
  - data/
    - calendar_management.py — JPX カレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（defusedxml 等を使用）
  - monitoring/ — 監視関連（DB 初期化や SystemMonitor 実装はこの下に配置）
  - utils/ — ロギング設定やプロセス優先度設定などユーティリティ群

補足（よくある操作）
- config/*.yaml がプロジェクトに存在し、PyYAML が入っている場合、validate_config は YAML のパースも検証します。PyYAML が未インストールなら YAML 内容検証はスキップされ、警告が出ます。
- generate_config.py の参照:
  - validate_config は config/*.yaml が無ければ「python scripts/generate_config.py で生成できます」と警告を出します（scripts ディレクトリのスクリプトはプロジェクトによって用意されている想定です）。

最小 .env 例（テンプレート）
- 実際は .env を絶対にリポジトリへコミットしないでください（シークレット漏洩防止）。
- 例:
  JQUANTS_REFRESH_TOKEN=your_jquants_token_here
  KABU_API_PASSWORD=your_kabu_api_password_here
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  LOG_LEVEL=INFO
  KILL_FLAG_CLEAR_ON_START=0

---

この README はコードベース（src/kabusys/*）から抽出した主要な利用情報をまとめたものです。実行環境や運用フローに応じて .env の内容・DB パス・ログ設定等を適切に調整してご利用ください。追加で「インストール要件の正確な一覧」「デプロイ手順」「詳細な運用手順（systemd / コンテナ化 等）」が必要であれば教えてください。