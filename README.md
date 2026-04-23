# KabuSys

日本株自動売買システム（簡易実装） — 設定管理、発注エンジン、監視、データ処理の主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。主要な機能は次の通りです。

- 環境変数 / .env の対話式作成ウィザードと自動読み込み
- 起動前の設定検証ツール（警告/エラーの検出）
- 発注エンジン（ExecutionEngine） — シグナルベースの発注ワークフロー、WebSocket プッシュの処理、リスクガード、リコンシリエーション
- ブローカー API レイヤ（kabuステーションクライアントの実装とテスト用モック）
- 注文永続化（SQLite）と状態遷移ロジック（OrderRecord）
- 監視プロセス（SystemMonitor のポーリングループを起動）
- データサブモジュール（マーケットカレンダー管理、RSS ニュース収集など）
- 開発/ペーパートレード用の Mock ブローカー（Paper Trading 用 DB に分離保存）

本リポジトリでは、実際の kabuステーション連携や本番用ブローカークライアントの実装（Live client）は限定的／未実装な箇所があります。開発・テストは `development` / `paper_trading` で行う想定です。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成・更新）: kabusys.config_setup.run_wizard
  - 対話形式で .env を作成、既存値の再利用
- 設定検証 CLI: kabusys.validate_config
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスや config/*.yaml の存在と YAML パース確認（PyYAML 必須）
  - --strict オプションで警告も FAIL 扱い
- Execution（発注）ランナー: kabusys.run_execution
  - ExecutionEngine の起動。環境に応じて Mock/Live ブローカーを使用
  - PID / stop flag / kill flag を扱う（安全起動ロジック）
- Monitoring（監視）ランナー: kabusys.run_monitoring
  - SystemMonitor のポーリングループを常時実行（MONITOR_POLL_INTERVAL で調整）
- ブローカー層
  - 共通インターフェース（BrokerAPIProtocol）と例外
  - MockBrokerClient（fill モード付き）と KabuStationClient（kabuステーション REST / WebSocket 実装）
- 注文管理
  - OrderRecord（状態遷移を厳格化）
  - OrderRepository（SQLite 永続化、テーブル初期化）
  - OrderManager（発注フロー、送信・同期・キャンセル）
  - Reconciler（起動時の状態復旧 / ポジション差分検出）
- リスク管理（RiskManager）
  - Gate 1: シグナルレベル（余力・重複・ポジション上限）
  - Gate 2: レート制限・サーキットブレーカー
  - Gate 3: ドローダウン監視（約定後）
- データ
  - calendar_management（JPX カレンダーの取得 / 営業日判定）
  - news_collector（RSS 収集と前処理。SSRF対策・XML安全処理等を採用）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境の作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール（例）

   必要な外部パッケージ（用途に応じて）:
   - duckdb
   - httpx
   - websocket-client
   - PyYAML (config の YAML 検証に使用)
   - defusedxml (RSS パーシングに使用)
   - その他（プロジェクトに依存するもの）

   例:

   ```
   pip install duckdb httpx websocket-client PyYAML defusedxml
   ```

   （プロジェクトに requirements.txt があればそれを使用してください）

4. .env を作成

   対話式ウィザードを使うと簡単です（後述の「使い方」を参照）。

5. DB ディレクトリ作成（デフォルトを使う場合）:

   ```
   mkdir -p data
   ```

---

## 環境変数（主要なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- オプション / 設定:
  - KABUSYS_ENV — execution モード: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番時の通知設定（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1，デフォルト 0)
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒，デフォルト 60）

設定は .env / .env.local（プロジェクトルート）から自動読み込みされます（OS 環境変数より低い優先度）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方

基本的な CLI 操作例を示します。いずれもプロジェクトルート（pyproject.toml や .git がある場所）で実行してください。

1. .env 作成ウィザード

   ```
   python -m kabusys.config_setup
   ```

   オプション: 保存パスを指定する場合

   ```
   python -m kabusys.config_setup --env-file path/to/.env
   ```

   ウィザードは既存 .env を読み込み、Enter で既存値を再利用できます。ウィザード終了後に .env が保存されます。

2. 設定検証

   .env を作成したら設定検証を実行します。

   ```
   python -m kabusys.validate_config
   ```

   厳密モード（警告も失敗扱い）:

   ```
   python -m kabusys.validate_config --strict
   ```

   validate_config は必須環境変数の未設定、プレースホルダ値、KABUSYS_ENV の不整合、LOG_LEVEL の不正値、DB パスの親ディレクトリ存在確認、config/*.yaml の存在および PyYAML によるパースチェック（PyYAML がインストールされていない場合はスキップ）などを行います。

3. Execution（発注エンジン）を起動

   Paper trading / development では MockBrokerClient を使用します（live は未実装の箇所があります）。

   ```
   python -m kabusys.run_execution
   ```

   実行前に .env の KABUSYS_ENV を適切に設定してください（paper_trading / development）。

   実行フロー:
   - PID ファイル書き出し（data/execution.pid など）
   - SQLite / DuckDB 接続
   - ブローカークライアント作成（Mock または Live）
   - ExecutionEngine.run_session() をスレッドで実行（シグナル処理／WebSocket ドレイン）

   停止:
   - プロセス外から data/stop_requested.flag を作成すると安全に停止します。
   - kill.flag による停止ロジックも存在（設定によって自動クリアを制御）。

4. Monitoring（監視）を起動

   ```
   python -m kabusys.run_monitoring
   ```

   MONITOR_POLL_INTERVAL によりポーリング間隔を調整できます（デフォルト 60 秒）。

5. 注意点

- KABUSYS_ENV=live のときは重要な追加チェックが入ります（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告など）。Live ブローカークライアントは未実装の箇所があるため、本番稼働は慎重に扱ってください。
- Paper Trading モードは本番 DB と分離され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
- validate_config は config/*.yaml（system_config.yaml 等）の存在をチェックしますが、これらはスクリプトで生成する想定（scripts/generate_config.py が示唆されています）。

---

## ディレクトリ構成（主要ファイル）

以下は本コードベースに含まれる主要なファイル・モジュールの概略です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード（.env / .env.local）と Settings クラス
  - config_setup.py
    - .env 対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 起動前設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine（発注エンジン）起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py
      - BrokerAPIProtocol、OrderRequest/Response/Status、例外、create_broker_api()
    - broker_factory.py
      - Settings に基づいてブローカークライアントを生成
    - kabu_client.py
      - KabuStationClient — kabuステーション REST & WebSocket 実装
    - mock_client.py
      - MockBrokerClient — テスト用モック（fill_mode 等を制御可能）
    - order_record.py
      - 注文状態モデルと状態遷移の検証
    - order_repository.py
      - SQLite を用いた永続化層（テーブル初期化含む）
    - order_manager.py
      - 発注フロー（作成・送信・同期・キャンセル）
    - execution_engine.py
      - ExecutionEngine — シグナル処理ループ、WebSocket ドレイン、kill switch 等
    - reconciler.py
      - 起動時リコンシリエーション（OrderSent 照合、ポジション差分検出）
    - risk_manager.py
      - 3段階リスクガード（Gate1/2/3）
  - data/
    - calendar_management.py
      - JPX カレンダー取得 / 営業日判定 / 夜間バッチ更新
    - news_collector.py
      - RSS 取得・前処理・DB 保存（SSRF / XML 漏洩対策を実装）
  - monitoring/
    - （monitoring_db.py, system_monitor.py 等が参照されていますが、ここに実装が存在します）
  - utils/
    - logging_setup.py
    - process_priority.py
    - （ユーティリティ関数群）

---

## 追加メモ / 運用上の注意

- .env は機密情報を含むため、絶対にバージョン管理にコミットしないでください。
- validate_config による事前チェックを CI に組み込むと安全です（--strict を CI で有効化する運用も可能）。
- ExecutionEngine の kill_switch は全 active 注文のキャンセルを試みますが、ブローカー API エラーや通信断時のリカバリに関しては設計上の注意点があります（Reconciler で復旧を補助します）。
- Live 環境での運用は慎重に。KabuStationClient の動作確認と十分なテストが必須です（現在のコードベースでは Live client の一部が未実装の可能性あり）。
- 必要に応じて依存パッケージのバージョン固定（requirements.txt）や Docker 化を検討してください。

---

README の内容や実行方法について不明点や補足したい項目があれば教えてください。README をプロジェクトの実際のファイル一覧や依存関係に合わせて調整できます。