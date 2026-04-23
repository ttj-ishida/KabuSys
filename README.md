# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README。  
この README はソース内の実装から主要な目的・使い方・セットアップ手順・ディレクトリ構成をまとめたものです。

> 注意: この README はソースコードを読み解いて作成しています。実運用や本番接続時は必ずコードと設定を理解したうえで運用してください。特に KABUSYS_ENV=live の場合は重大なリスクが伴います。

---

## 概要

KabuSys は、日本株自動売買を目的としたモジュール群です。  
主に以下の責務を持ちます。

- 環境変数 / .env の管理（対話式ウィザード）
- 起動前設定の検証（必須環境変数、YAML 設定ファイルチェック等）
- ExecutionEngine によるシグナル駆動型の発注処理（Signal → 発注 → リコンシリエーション）
- Monitoring（システムリソースや監視データのポーリング保存）
- ブローカー API 抽象化（kabuステーション実装、テスト用 Mock 実装）
- リスク管理（Gate1/2/3：余力・重複・レート制限・サーキットブレーカー・ドローダウン等）
- データ関連ユーティリティ（マーケットカレンダー、ニュース収集など）

設計上、DB（SQLite / DuckDB）や外部 API（kabuステーション、J-Quants）へ接続して動作します。テスト・開発用に MockBrokerClient を備え、ペーパートレード環境で本番 DB と切り離して動作させることができます。

---

## 主な機能一覧

- .env 対話式作成ウィザード（kabusys.config_setup）
  - 必須項目・任意項目を対話的に入力し .env を生成
- 設定検証 CLI（kabusys.validate_config）
  - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パス確認、config/*.yaml の存在・YAML パース検査
  - --strict オプションで警告を FAIL 扱いにできる
- 実行エンジン（kabusys.run_execution）
  - ExecutionEngine を起動し、シグナルの読み込み→リスクゲート→発注→WebSocket ドレイン→セッション管理を実行
  - paper_trading では MockBrokerClient を使用
- 監視ループ（kabusys.run_monitoring）
  - SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL により間隔を変更可能
- ブローカー抽象層
  - create_broker_api() により Mock / 実ブローカーを切替
  - KabuStationClient（httpx, websocket ベース）実装
- 注文永続化（SQLite）と状態遷移（OrderRecord）
  - 安全な状態遷移チェック、永続化・更新 API
- リコンシリエーション（起動時の OrderSent 照合およびポジション差分検出）
- リスク管理（Rate limit / Circuit breaker / Drawdown 監視）

---

## セットアップ手順（開発向け）

前提：Python 3.10 以上を推奨（ソース内の型記法など）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

3. 必要なパッケージをインストール
   - requirements.txt が無ければ、最低限以下をインストールしてください（実際のプロジェクトで必要なパッケージが追加されている可能性があります）:
   ```
   pip install duckdb httpx websocket-client PyYAML defusedxml
   ```
   - 開発インストール（パッケージ化されている場合）:
   ```
   pip install -e .
   ```

4. 初期 .env を作成する
   - 対話式ウィザードを用いる:
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは .env の作成・上書きを行います。生成した .env は Git にコミットしないでください（README 内 .env コメントにも警告あり）。

5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. （任意）config/*.yaml のテンプレートが無い場合は
   - スクリプト参照: README では scripts/generate_config.py を案内している箇所があるため、リポジトリに存在する場合は実行して生成してください。
   - PyYAML が無いと YAML 内容のパース検査はスキップされます（validate_config が警告を出します）。

---

## 使い方

各主要モジュールの実行例。

- 環境設定ウィザード（.env 作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（SystemMonitor ポーリング）
  - デフォルトのポーリング間隔: 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）
  ```
  python -m kabusys.run_monitoring
  # 例: 30 秒に設定して起動
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV により挙動が変わる:
    - development / paper_trading → MockBrokerClient（本番ブローカーと接続しない）
    - live → 実ブローカーは未実装（コード中では NotImplementedError を投げる）
  ```
  python -m kabusys.run_execution
  ```
  - paper_trading では発注はモックされ、専用 SQLite（デフォルト data/paper_trading.db）に記録されます。

- ログ・監視ファイル
  - PID ファイル、kill/stop フラグ等はデフォルトで data/ ディレクトリ配下に配置されます（例: data/execution.pid, data/kill.flag, data/stop_requested.flag）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

---

## 主要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / 推奨:
- KABUSYS_ENV — 実行環境（development / paper_trading / live） デフォルト: development
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用 LINE 設定
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading 用の fill モード (instant / partial / never / reject)
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite の上書きパス
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

validate_config と Settings クラスにより、環境変数の妥当性チェックや既定値取得が行われます。

---

## ファイル / ディレクトリ構成

（主要部分のみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py       — 起動前検証 CLI（python -m kabusys.validate_config）
  - run_execution.py         — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - run_monitoring.py       — Monitoring ループ起動スクリプト（python -m kabusys.run_monitoring）
  - execution/
    - broker_api.py          — BrokerAPI Protocol・データモデル・例外・ファクトリ
    - broker_factory.py      — Settings に基づくブローカーファクトリ
    - kabu_client.py         — kabu station REST / WebSocket クライアント実装
    - mock_client.py         — テスト用モック実装
    - order_record.py        — 注文状態モデル & 遷移ロジック
    - order_repository.py    — SQLite を使った永続化層
    - order_manager.py       — 注文発行・同期・キャンセルの高レベル API
    - execution_engine.py    — セッション制御 / シグナル処理 / push ドレイン
    - reconciler.py          — 起動時の自動照合・復旧処理
    - risk_manager.py        — Gate1/2/3 によるリスク制御
  - monitoring/
    - monitoring_db.py      — 監視用 DB 初期化 / ログ機能（参照：run_monitoring）
    - system_monitor.py     — システムメトリクス収集
  - data/
    - calendar_management.py — マーケットカレンダー取得・判定ロジック
    - news_collector.py      — RSS 収集・前処理ロジック
  - utils/
    - logging_setup.py      — ロギング初期化
    - process_priority.py   — プロセス優先度設定ユーティリティ
  - その他: strategy/、monitoring/、data/ 等のサブパッケージ（実装あり）

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - validate_config は上記ファイルの存在と YAML パースをチェックします（PyYAML 必要）。

- data/
  - デフォルトで DB / PID / flag を置く場所（.env で上書き可能）

---

## 代表的なワークフロー・運用注意点

- 開発・テスト:
  - KABUSYS_ENV=development または paper_trading を使用。これにより MockBrokerClient が使用され、本番ブローカー接続を回避できます。
  - paper_trading は paper_trading 用 SQLite に記録され、本番データと分離されます。

- 本番（live）に関する注意:
  - KABUSYS_ENV=live を指定すると validate_config で警告が増え、本番接続関連設定（LINE 通知など）の確認を促します。
  - Live ブローカー実装はリポジトリ内で未実装の箇所があり（BrokerClientFactory で NotImplementedError）、本番利用前に実装と安全性レビューが必須です。
  - kill.flag / KILL_FLAG_CLEAR_ON_START の挙動を理解した上で運用してください（自動クリアは危険）。

- リスタート時の安全性:
  - ExecutionEngine は起動時に Reconciler を実行して OrderSent 状態の注文をブローカーと突合します。クラッシュ復旧設計が組み込まれていますが、手動確認が必要なケースもログに出ます。

---

## よくあるトラブルと対処

- validate_config で「必須環境変数が未設定」と出る
  - .env に必須キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が設定されているか確認
  - config_setup を再実行して設定を更新する

- config/*.yaml が見つからない / パース失敗
  - config ディレクトリに該当 YAML があるか確認
  - PyYAML がインストールされているか確認（validate_config は PyYAML が無い場合、YAML 内容チェックをスキップして警告）

- WebSocket / httpx 周りの接続エラー
  - KABU_API_BASE_URL、API パスワード、kabuステーション側の稼働状態を確認
  - ネットワーク・ファイアウォール設定を確認

- DuckDB / SQLite のディレクトリが存在しない
  - デフォルトの parent ディレクトリ（data/ 等）が存在しない場合は自動作成される箇所もありますが、必要に応じて手動で作成してください
  - .env で DUCKDB_PATH / SQLITE_PATH を明示的に設定可能

---

## 最後に（セキュリティ & 運用）

- .env は API トークン・パスワードを含みます。決して Git にコミットしないでください。
- 本番運用時はアラート通知（LINE 等）と kill / stop フラグ運用ルールを整備してください。
- live 環境での実売買は十分なテストと監査を行った上で実行してください。

---

必要に応じて README を補足します。実行コマンド例や .env サンプル、依存パッケージ一覧（requirements.txt）等の追加を希望する場合は教えてください。