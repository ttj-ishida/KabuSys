# KabuSys

日本株自動売買システムのコアライブラリ（軽量版）。  
このリポジトリには、設定管理、発注エンジン、ブローカークライアント、リスクガード、監視ループ、データ処理ユーティリティなどの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- シグナルに基づく発注エンジン（ExecutionEngine）
- ブローカー API 抽象層（kabu station 実装 + Mock 実装）
- 注文状態管理（OrderRecord / OrderRepository / OrderManager）
- 起動時リコンシリエーション（Reconciler）
- 3 段階のリスクガード（RiskManager）
- 監視プロセス（SystemMonitor）
- マーケットカレンダー・ニュース収集等のデータ処理ユーティリティ
- .env ベースの設定ウィザード・検証ツール

設計方針として、DB と API 呼び出しを明確に分離し、クラッシュ耐性（2 相永続化や再照合）や安全な運用（kill switch、サーキットブレーカー）を重視しています。

---

## 主な機能一覧

- 設定ウィザード（対話式）: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config（--strict で警告も FAIL）
- 実行エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV に応じて Mock ブローカーを使用（paper_trading / development）
  - paper_trading は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と分離
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト: 60 秒）
  - 監視は環境にかかわらず本番 sqlite_path を使用
- Broker API 抽象化（BrokerAPIProtocol）とファクトリ（create_broker_api）
- MockBrokerClient によるテスト用発注 / 約定シミュレーション（fill_mode）
- 注文の永続化（SQLite）とリコンシリエーション
- DuckDB を用いたシグナル/ポートフォリオ読み込み・マーケットカレンダー処理
- ニュース収集（RSS）と前処理（SSRF 対策、正規化）

---

## 要件（推奨）

- Python 3.10+
- 必須パッケージ（一部）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml の検証を行う場合）
- SQLite は標準ライブラリで利用
- 実際の kabu station を使う場合は kabu station アプリの起動が必要

（プロジェクトには requirements.txt がない可能性があるため、上記を適宜インストールしてください）

例:
```
pip install duckdb httpx websocket-client defusedxml PyYAML
```

---

## セットアップ手順（開発 / 初回セットアップ）

1. リポジトリをチェックアウトし、Python 環境を用意する（venv 等）。
2. 必要なパッケージをインストールする（上記参照）。
3. .env を準備する
   - 対話式ウィザードを使う（推奨）:
     ```
     python -m kabusys.config_setup
     ```
     指示に従い .env を生成・更新してください。
   - もしくは手動で .env を作成（プロジェクトルートに置く）。自動読み込みの順序は:
     OS 環境変数 > .env > .env.local（.env.local は .env を上書き）
     自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
4. 設定検証を行う
   ```
   python -m kabusys.validate_config
   # 警告も FAIL として扱う場合
   python -m kabusys.validate_config --strict
   ```
   必須環境変数や config/*.yaml の存在／パースをチェックします。

---

## 主要な環境変数（例とデフォルト）

必須（少なくとも設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルト:
- KABUSYS_ENV — execution 環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station の base URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — paper_trading の挙動（instant / partial / never / reject）

README 内の .env 例（要置換）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## 使い方（CLI）

- .env 作成（対話式ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（発注）起動
  ```
  python -m kabusys.run_execution
  ```
  動作モード:
  - KABUSYS_ENV=development / paper_trading: MockBrokerClient を使用（paper_trading は専用 DB を使用）
  - KABUSYS_ENV=live: 現時点では NotImplementedError（要実装）

  停止:
  - 実行中はプロセスが data/execution.pid を持ちます。外部から停止させるにはプロセスを終了するか、プロジェクトルートの data/stop_requested.flag を作成してください。run_execution はこのフラグを検出して安全に停止します。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を調整できます。
  - 監視は settings.sqlite_path（本番用 sqlite）を使用します。
  - 停止の方法は run_execution と同様に data/stop_requested.flag。

---

## 運用上の注意

- kill.flag と kill スイッチ:
  - settings.kill_flag_path（デフォルト: data/kill.flag）を使って kill スイッチを検知します。
  - kill.flag が存在すると ExecutionEngine は起動を拒否します（ただし KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動でクリアして起動します）。
  - 実行中の kill スイッチ発動時は全 active 注文をキャンセルして安全に停止します。

- 本番環境（KABUSYS_ENV=live）注意点:
  - validate_config は live 設定時に追加の警告チェック（LINE 通知設定など）を行います。
  - live モードでは慎重な事前検証を行ってください。

- DB の分離:
  - paper_trading は paper 用 SQLite を使用し、本番（monitoring.sqlite）と分離します。
  - DuckDB はシグナルやポートフォリオを扱う分析 DB として用います。

- YAML 検証:
  - validate_config は PyYAML がインストールされていれば config/*.yaml のパース検証を行います。未インストール時は警告でスキップします。
  - 期待される config ファイル一覧:
    - config/system_config.yaml
    - config/data_config.yaml
    - config/strategy_config.yaml
    - config/risk_config.yaml
    - config/execution_config.yaml
    - config/monitoring_config.yaml

---

## テスト・開発向け機能

- MockBrokerClient（fill_mode: instant/partial/never/reject）
  - create_broker_api(mock=True, fill_mode="...") または Settings による自動選択で利用可能。
  - unit テストやローカル動作確認に便利です。
- Reconciler による起動時の自動復旧（OrderSent の再照合・ポジション差分検出）
- ExecutionEngine は WebSocket push（kabu station の push）を受け取る設計で、MockBrokerClient は stream_push を持たないため WebSocket スレッドはスキップされます。

---

## ディレクトリ構成（要約）

以下は主要ファイルの一覧と簡単な説明（src/kabusys 以下）:

- __init__.py
  - パッケージ定義、バージョン情報

- config.py
  - 環境変数読み込み・自動 .env ロード
  - Settings クラス（設定プロパティ、検証）
- config_setup.py
  - 対話式 .env 作成ウィザード
- validate_config.py
  - 起動前の設定検証 CLI（必須 env、config/*.yaml など）

- run_execution.py
  - ExecutionEngine 起動スクリプト（発注ルーチン）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（監視）

- execution/（発注関連）
  - broker_api.py — BrokerAPIProtocol、データモデル、例外、factory
  - broker_factory.py — Settings を元にクライアントを作るファクトリ
  - kabu_client.py — kabu station REST クライアント実装
  - mock_client.py — テスト用 MockBrokerClient
  - execution_engine.py — ExecutionEngine（シグナル処理 / push ドレイン）
  - order_record.py — 注文状態モデルと遷移ロジック
  - order_repository.py — SQLite 永続化
  - order_manager.py — 外向け注文 API（作成・送信・同期・取消）
  - reconciler.py — 起動時の再照合ロジック
  - risk_manager.py — Gate1/2/3 のリスクガード
  - その他: order_*、risk_* ファイル群

- data/（データ処理）
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py — RSS ニュース収集・前処理
  - jquants_client.py（参照あり） — J-Quants API クライアント（カレンダーやデータ取得）

- monitoring/
  - monitoring_db.py — 監視用 SQLite テーブル初期化・書き込み
  - system_monitor.py — システム状態監視ロジック（CPU/メモリ/ディスク しきい値等）

- utils/
  - logging_setup.py — ロギング初期化
  - process_priority.py — プロセス優先度設定
  - その他ユーティリティ

（実際のファイル数はもっと多く、上記は主要モジュールの抜粋です）

---

## 典型的なワークフロー（開発時）

1. 仮想環境を作成 & 依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で確認
4. DuckDB にシグナル/portfolio テーブル等を用意（分析側）
5. python -m kabusys.run_execution を起動して発注をテスト（PAPER_TRADING にて MockBroker）
6. python -m kabusys.run_monitoring を別プロセスで起動し監視を行う

---

## 補足 / トラブルシューティング

- config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env を自動ロードします。配布パッケージ化後やテストではこの自動読み込みを無効化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- validate_config は PyYAML が無い場合、YAML パース検証をスキップして警告を出します。config/*.yaml を検証したい場合は PyYAML を入れてください。
- 本番運用前に必ず validate_config を実行し、LINE 通知や KILL_FLAG 設定などの注意点を確認してください。
- run_execution の起動時に data/kill.flag が存在すると起動を拒否します。既存のファイルが残っているときは手動で確認・削除してください（または KILL_FLAG_CLEAR_ON_START=1 を設定して自動クリア）。

---

以上がこのコードベースの README.md（日本語）です。必要に応じてサンプル .env.example、requirements.txt、運用手順書（デプロイ手順・systemd ユニット 等）を追加することをおすすめします。必要であれば README をさらに詳しく拡張（各設定の意味、DB 初期化 SQL、サンプル DuckDB クエリ等）します。どの情報を追加しましょうか？