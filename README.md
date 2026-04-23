# KabuSys

日本株自動売買システムの一部を実装したリポジトリ（内部ユーティリティ、Execution/Monitoring、Data 層など）。  
この README はコードベースの主要な機能・セットアップ・使い方・ディレクトリ構成をまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたシステムのコアコンポーネント群を含みます。主な役割は以下:

- 環境変数 / 設定ファイル (.env, config/*.yaml) の管理と対話式ウィザード
- 実行エンジン（ExecutionEngine）: シグナルの読み取り → リスクチェック → 発注
- ブローカー API 抽象化（kabu station クライアントおよびモッククライアント）
- 注文の状態管理（OrderRecord / OrderManager / OrderRepository）
- 再起動時の自動復旧（Reconciler）
- 3段階のリスクガード（RiskManager）
- 監視ループ（SystemMonitor を用いた run_monitoring）
- データ層ユーティリティ（マーケットカレンダー管理、RSS ニュース収集 等）

設計方針として、ビジネスロジックと永続化（SQLite / DuckDB）は明確に分離されており、テストやローカル開発のための MockBrokerClient も提供されています。

---

## 主な機能一覧

- 環境設定ウィザード（対話式）: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config（--strict フラグで警告も失敗扱い）
- ExecutionEngine（発注ループ、WebSocket push ドレイン、kill switch）
- Broker API 抽象化:
  - KabuStationClient（kabu station REST API 実装）
  - MockBrokerClient（テスト/開発用）
- 注文管理:
  - OrderRecord（状態遷移の検証）
  - OrderRepository（SQLite 永続化）
  - OrderManager（作成→送信→同期→キャンセルのワークフロー）
- リスク管理（Gate1/2/3: シグナル検査 / レート制限・CB / ドローダウン監視）
- Reconciler：再起動時に OrderSent の注文を突合して状態回復
- Data ツール:
  - calendar_management（JPX カレンダー管理）
  - news_collector（RSS 収集と前処理）
- 監視プロセス用スクリプト（run_monitoring）
- 実行プロセス用スクリプト（run_execution）

---

## 必要要件（概略）

- Python 3.10+（型注釈や一部の記法に依存）
- SQLite（Python 標準ライブラリに含まれる）
- DuckDB（Python パッケージ）
- 以下の Python パッケージ（用途に応じて必要）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML （config/*.yaml の内容検証を行う場合）
- ネットワーク接続（kabu station へ接続する場合）

pip でのインストール例（venv 推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml PyYAML
```

※ 実運用での追加要件（運用用サービス・監視・運転権限など）は別途必要です。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb httpx websocket-client defusedxml PyYAML
   ```
   - PyYAML がない場合、config/*.yaml のパース検証はスキップされます（validate_config が警告を出します）。

4. 環境変数の設定
   - 対話式ウィザードで .env を生成・編集:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートの `.env` を手動で作成してください。
   - 自動ロード動作:
     - パッケージは `.env` と `.env.local` を自動で読み込みます（OS 環境 > .env.local > .env の優先順）。
     - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 設定の検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする:
   python -m kabusys.validate_config --strict
   ```

6. データベース初期化
   - run_execution / run_monitoring の起動時に必要なテーブル（orders / monitoring など）は自動で初期化するユーティリティが呼ばれます。
   - 必要に応じて専用スクリプトやマイグレーションを実行してください（本リポジトリでは init_* 関数が用意されています）。

---

## 使い方（主要な実行コマンド）

- 環境ウィザード（対話式 .env 作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

  出力例:
  - INFO / WARNING / ERROR を表示し、ERROR があれば exit code 1 を返します。
  - --strict を付けると WARNING があっても exit code 1 になります。

- 実行エンジン（Execution）
  - 通常はサービスや systemd 等から起動します。手動実行の例:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV による動作:
    - development / paper_trading: MockBrokerClient を使用（安全にテスト可能）
    - live: 本番ブローカー（現状は未実装で NotImplementedError）

  - paper_trading の場合、発注は専用の SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）に分離されます。

- 監視ループ（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）。
  - 監視は常に本番 sqlite_path を使用します（KABUSYS_ENV にかかわらず）。

- 停止フラグ / PID ファイル
  - 停止用フラグ: data/stop_requested.flag を作成するとループは検知して終了します。
  - PID ファイル: 設定で指定した pid_file_path（デフォルト data/execution.pid）に PID が書き込まれます。
  - kill flag: settings.kill_flag_path（デフォルト data/kill.flag）
    - KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に kill.flag を自動クリアします（注意：本番では 0 推奨）。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABU_API_BASE_URL: kabu station のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（live 時は未設定だと警告）

その他:
- MONITOR_POLL_INTERVAL（監視ポーリング間隔, 秒）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか）

注意: `.env` ファイルは絶対に Git にコミットしないこと（config_setup の出力にもこの旨が書かれます）。

---

## 開発・テストのポイント

- MockBrokerClient を利用すれば kabu station を用意せずに発注フローやリコンシリエーションなどをテスト可能です。
  - KABUSYS_ENV=paper_trading または development で自動的にモックが選択されます。
  - Mock の fill_mode（instant / partial / never / reject）を `PAPER_FILL_MODE` で制御可能（Settings.paper_fill_mode）。
- OrderRecord は DB に触らない純粋なドメインロジックなので単体テストが書きやすい設計です。
- Reconciler はクラッシュ後復旧ロジックの中核。OrderSent の状態が残るケースに備える実装です。
- calendar_management と news_collector は DuckDB と J-Quants（外部 API）を使う想定のため、開発環境ではローカル DuckDB とモックを使ってテストするとよいです。

---

## ディレクトリ構成

主要ファイル / ディレクトリ（簡易）

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数 / .env 読み込み・Settings
    - config_setup.py              # 対話式 .env ウィザード
    - validate_config.py           # 設定検証 CLI
    - run_execution.py             # ExecutionEngine を起動するスクリプト
    - run_monitoring.py            # SystemMonitor ポーリングスクリプト
    - execution/
      - __init__.py
      - broker_api.py              # BrokerAPI の Protocol / データモデル / factory
      - broker_factory.py          # Settings に基づくクライアント生成
      - kabu_client.py             # KabuStationClient（REST + WebSocket）
      - mock_client.py             # MockBrokerClient（テスト用）
      - order_record.py            # 注文状態モデルと遷移
      - order_repository.py        # SQLite 永続化
      - order_manager.py           # 外向き注文 API（作成 / 送信 / 同期 / 取消）
      - execution_engine.py        # ExecutionEngine（シグナル処理 / push drain）
      - reconciler.py              # 再起動時リコンシリエーション
      - risk_manager.py            # Gate1/2/3 のリスク管理
    - monitoring/                   # （監視関連コード）
      - monitoring_db.py           # 監視用 DB 初期化 / ロギング
      - system_monitor.py          # SystemMonitor 実装（ポーリング対象チェック等）
    - data/
      - calendar_management.py     # JPX カレンダー管理（DuckDB）
      - news_collector.py          # RSS ニュース収集
      - jquants_client.py          # （J-Quants API ラッパ: 省略されているが参照あり）
    - utils/
      - logging_setup.py           # ロガー設定ユーティリティ
      - process_priority.py        # プロセス優先度設定ユーティリティ
    - その他: scripts / config/*.yaml など

上記は主要コンポーネントの配置イメージです。

---

## トラブルシューティング / 注意点

- validate_config が警告を出す項目:
  - `.env` のプレースホルダ（your_value や *_here）を検出すると警告になります。
  - PyYAML が未インストールだと config/*.yaml のパース検証はスキップされます（警告）。
- KABUSYS_ENV=live の場合:
  - 実運用向けの注意喚起（LINE 通知設定未設定等）を行います。
  - 本コードベースでは Live ブローカークライアントは未実装の箇所があります（BrokerClientFactory は NotImplementedError を投げます）。
- kill.flag の扱い:
  - 起動時に kill.flag が存在すると起動を拒否する（KILL_FLAG_CLEAR_ON_START=1 で自動クリアして起動可能）。
- SQLite / DuckDB のファイルパスが存在しない場合、親ディレクトリを自動作成する処理は起動側で行われますが、validate_config は親ディレクトリがない旨を警告します。
- WebSocket (kabu push) は websocket-client を使用しており、stop_event が set されると接続を閉じて再接続を止める仕組みになっています。

---

## 最後に

この README はコードベースから読み取れる設計・使い方の要点をまとめたものです。実際の運用時は以下を推奨します:

- 本番接続を行う前に必ず validate_config を実行する
- .env をバージョン管理に含めない（シークレット管理を厳格化）
- テスト時は MockBrokerClient を活用し、Reconciler 等の復旧ロジックを検証する

ご質問や追加のドキュメント（具体的な運用手順 / デプロイ手順 / テストケース等）が必要でしたらお知らせください。