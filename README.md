# KabuSys

日本株向け自動売買システムの一部実装。  
このリポジトリには、環境設定ウィザード、設定検証、発注エンジン、監視ループ、ブローカークライアント群（実装・モック）、リスク管理、カレンダー／ニュース収集などの主要コンポーネントが含まれます。

Version: 0.1.0

---

## プロジェクト概要
KabuSys は以下の機能を備えたエンジン群を提供します。

- 環境変数ベースの設定管理（.env の自動/手動読み込み）
- 対話式 .env 作成ウィザード（config_setup）
- 起動前に .env / config/*.yaml を検証する CLI（validate_config）
- 発注ロジック（ExecutionEngine）と注文状態管理（OrderRecord / OrderRepository / OrderManager）
- ブローカー抽象化（BrokerAPIProtocol）と Mock / KabuStation 実装
- 3段階のリスクガード（RiskManager: Gate1/2/3）
- 再起動時の自動リコンシリエーション（Reconciler）
- 監視ループ（SystemMonitor を用いる run_monitoring）
- データ関連ユーティリティ（マーケットカレンダー、ニュース収集など）

設計方針として、DB（SQLite / DuckDB）は永続層に限定し、ビジネスロジックと DB 操作を分離しています。発注フローはクラッシュ耐性を考慮した2相永続化などの工夫があります。

---

## 主な機能一覧
- .env 対話式ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数検査、KABUSYS_ENV の妥当性確認、YAML パース検証（PyYAML がある場合）、本番時ガード等
  - --strict フラグで警告もエラー扱い
- 発注エンジン（ExecutionEngine）
  - シグナルの読み取り→Gate1/Gate2 リスクチェック→発注→push/drain ループ
  - WebSocket push の処理（kabu station の push を受ける）
- 注文管理
  - OrderRecord（状態遷移の検証）
  - OrderRepository（SQLite 永続化）
  - OrderManager（DB とブローカー API を繋ぐ）
- ブローカー抽象化と実実装
  - BrokerAPIProtocol（共通インターフェース）
  - MockBrokerClient（テスト用、fill_mode を制御可能）
  - KabuStationClient（httpx, websocket-client ベースの実装）
- リスク管理（RiskManager）
  - Gate1: 余力・重複・ポジション上限
  - Gate2: レート制限・サーキットブレーカー
  - Gate3: ドローダウン監視（kill_switch 発動）
- リコンシリエーション（Reconciler）
  - OrderSent の突合、ポジション差分検出
- データユーティリティ
  - マーケットカレンダー管理（duckdb 経由）
  - ニュース収集（RSS パース、安全対策を含む）

---

## 必要条件（推奨）
- Python 3.9+（型注釈や typing 機能の利用を踏まえて）
- 必要パッケージ（代表例）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML （config/*.yaml のパース検証を行いたい場合）
  - （標準ライブラリ以外は pip でインストールしてください）

※requirements.txt はリポジトリにない場合があるため、環境に合わせて上記をインストールしてください。

例:
pip install duckdb httpx websocket-client defusedxml PyYAML

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML

4. .env の作成（推奨: 対話式ウィザードを使用）
   - python -m kabusys.config_setup
     - 対話に従い必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）を入力
     - 完了後 .env が生成されます

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする: python -m kabusys.validate_config --strict

6. DB ディレクトリ作成（.env のパスを使用する）
   - デフォルトでは data/ 以下に DuckDB と SQLite を置きます。必要に応じて親ディレクトリを作成してください。
   - run_execution/run_monitoring は起動時に親ディレクトリを作成する処理を行う箇所もありますが、権限等で失敗する場合があるため予め確認してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / 推奨:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - paper_trading / development は MockBrokerClient を利用
  - live は本番（注意: 本実装では Live broker client は未実装箇所あり）
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABU_API_BASE_URL — kabu station API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番でのアラート通知（任意）
- PAPER_FILL_MODE — ペーパートレードの約定振る舞い: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 起動・停止に関連するファイル制御設定
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

自動 .env ロード:
- 起動時に .env を自動で読み込みます（プロジェクトルートは .git または pyproject.toml を基準に検出）。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要コマンド）

- .env を対話式で作成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 警告も失敗にしたい場合:
    - python -m kabusys.validate_config --strict

- 発注エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作例（ペーパートレード）:
    - 環境変数 KABUSYS_ENV=paper_trading を .env または環境で設定
    - PAPER_FILL_MODE=partial などを設定して動作を試せます
  - 起動前に stop フラグ（data/stop_requested.flag や kill.flag）が立っていないことを確認してください。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）

- 停止 / 強制停止
  - 停止フラグを立てる: 作業ディレクトリの data/stop_requested.flag を作成すると実行中のループは検知して終了します
  - kill.flag（KILL_FLAG_PATH）を使って緊急停止（kill_switch）が発動します。KILL_FLAG_CLEAR_ON_START=1 なら起動時に自動クリアされます。

---

## 実装上のポイント（簡易）

- 発注のクラッシュ安全性:
  - OrderManager.send_order は OrderSent の永続化を broker 呼び出し前に行い、broker_order_id を先に保存してから OrderAccepted に遷移する 2 相永続化を採用。
  - OrderSent のままクラッシュしても Reconciler により再突合される設計。
- リスク管理:
  - Gate1（シグナル単位）: 余力、重複、ポジション上限
  - Gate2（送信前）: レート制限（トークンバケツ）、サーキットブレーカー
  - Gate3（約定後）: ドローダウン監視 → NG の場合は kill_switch 発動
- MockBrokerClient:
  - fill_mode により instant / partial / never / reject の挙動を模擬可能。テスト・ローカル開発で有用。
- カレンダー / ニュース関連:
  - duckdb をデータ層に用いるユーティリティ群。JPX カレンダーや RSS 収集を安全に行う実装が存在。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- __init__.py
  - パッケージ定義（__version__ 等）

- config.py
  - 環境変数の自動読み込み・Settings クラス（settings）を提供
  - .env のパースロジック、プロジェクトルート自動検出

- config_setup.py
  - 対話式 .env ウィザード（python -m kabusys.config_setup）

- validate_config.py
  - 起動前チェック CLI（python -m kabusys.validate_config）

- run_execution.py
  - ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（python -m kabusys.run_monitoring）

- execution/
  - broker_api.py — BrokerAPIProtocol, データモデル, ファクトリ
  - kabu_client.py — kabu station 実装（httpx / websocket）
  - mock_client.py — テスト用 MockBrokerClient
  - broker_factory.py — Settings に応じたクライアント生成
  - order_record.py — 注文状態モデル（状態遷移検証）
  - order_repository.py — SQLite 永続化層（init_orders_db を含む）
  - order_manager.py — 外向きの注文 API（create/send/sync/cancel）
  - execution_engine.py — ExecutionEngine 本体（セッション制御、push/drain）
  - reconciler.py — リコンシリエーション（再起動時）
  - risk_manager.py — 3段階リスクガード
  - その他（order_*、risk_*）

- monitoring/
  - monitoring_db.py 等（監視用 DB 初期化・ログ記録）※ run_monitoring と連携

- data/
  - calendar_management.py — マーケットカレンダー取得/判定ロジック（DuckDB）
  - news_collector.py — RSS 収集（安全対策付き）
  - jquants_client.py （J-Quants API 連携は別途実装想定）

- utils/
  - logging_setup.py — ロギング初期化
  - process_priority.py — プロセス優先度設定 等

- scripts/
  - generate_config.py 等（config/*.yaml 生成スクリプトが参照される箇所あり）

---

## 例: ローカルでの起動フロー（簡易）
1. 仮想環境を作成し依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定をチェック
4. python -m kabusys.run_monitoring を別ターミナルで起動（監視）
5. python -m kabusys.run_execution を起動してセッションを実行

---

## 注意事項
- .env ファイルは機密情報を含むため、絶対に Git へコミットしないでください（config_setup もその旨を出力します）。
- KABUSYS_ENV=live（本番）では設定ミスが重大な損失につながるため、validate_config の警告・チェックを慎重に確認してください。
- ライブブローカークライアントは一部未実装／未検証箇所があります（コード内に注記あり）。本番運用前に十分なテストを行ってください。

---

必要があれば、README に付け加える以下の項目も作成できます:
- requirements.txt の推奨内容
- 詳細な環境変数一覧（説明付きテーブル）
- 起動時のログ例 / トラブルシューティング
- テスト方法（ユニットテスト例、Mock の使い方）

どの追加情報が必要か教えてください。