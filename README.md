# KabuSys

日本株の自動売買プラットフォーム（軽量版） — 環境設定管理、発注エンジン、監視、データ取得などの主要コンポーネントを含むモジュール群です。

---

## プロジェクト概要

KabuSys は、kabuステーション API（あるいはモック）を用いた自動発注エンジンと、監視・リコンシリエーション・データ処理のためのユーティリティを備えた Python パッケージです。設計はモジュール化されており、以下の特徴があります。

- 環境変数 / .env による設定管理（自動ロード機能付き）
- 対話式ウィザードでの .env 作成・更新
- 起動前設定検証 CLI（必須変数の未設定や YAML のパースチェック）
- 発注エンジン（ExecutionEngine）と注文状態管理（OrderRecord / OrderRepository / OrderManager）
- Mock ブローカーによるペーパートレード動作サポート
- 起動時のリコンシリエーション（Reconciler）によるクラッシュ復旧
- 3 段階のリスクガード（Gate1/2/3）
- 監視プロセス（SystemMonitor）および監視 DB へのログ記録
- データ関連ユーティリティ（マーケットカレンダー、ニュース収集等）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証ツール（python -m kabusys.validate_config）
  - --strict オプションで警告も失敗扱いにする
- 実行エンジン起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV による paper_trading / development / live の切替（live は未実装箇所あり）
- 監視スクリプト起動（python -m kabusys.run_monitoring）
  - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で調整可能（デフォルト 60 秒）
- 注文状態管理（OrderRecord、OrderManager、OrderRepository）
- ブローカー抽象化（BrokerAPIProtocol）とモック実装（MockBrokerClient）
- リスク管理（RiskManager）: 余力 / 重複 / ポジション上限 / レート制限 / サーキットブレーカー / ドローダウン
- マーケットカレンダー管理（data.calendar_management）
- ニュース収集（data.news_collector）

---

## 前提条件・依存パッケージ（例）

- Python 3.9+（型ヒントと pathlib を前提）
- 推奨パッケージ（用途に応じて）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（config/*.yaml のパースチェックを行う場合）
  - defusedxml（ニュース収集）
- （開発用）venv の作成を推奨

例（pip インストール）:
pip install duckdb httpx websocket-client pyyaml defusedxml

※ リポジトリに requirements.txt があればそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して有効化します。
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストールします（上記参照）。
   - 例: pip install duckdb httpx websocket-client pyyaml defusedxml

3. .env を作成します（推奨: ウィザードを使用）。
   - python -m kabusys.config_setup
   - 既存の .env があれば読み込まれ、Enter で既存値を再利用できます。

4. 設定検証を実行して問題がないか確認します。
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     python -m kabusys.validate_config --strict

5. 実行:
   - 実注文を伴うエンジン起動（paper_trading / development / live による挙動差あり）
     - python -m kabusys.run_execution
   - 監視ループ起動
     - python -m kabusys.run_monitoring

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（主要なもの）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート向け
- KILL_FLAG_CLEAR_ON_START: 0/1（起動時 kill.flag を自動クリアするか）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）

.env の自動ロード順序:
- OS 環境変数 > .env.local > .env
- 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意:
- .env は絶対に Git へコミットしないでください（config_setup も同様に注意喚起あり）。

例 (.env の抜粋)
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

---

## 使い方（主要コマンド）

- 環境設定ウィザード（対話式）
  - python -m kabusys.config_setup
  - --env-file で保存先を変更可能

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ書き込まれます。
    - 成功時は PID ファイルを書き、stop flag（data/stop_requested.flag）を検出すると安全停止します。
    - kill.flag（デフォルト data/kill.flag）が存在すると起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動可）。

- 監視ループ
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を調整可能（デフォルト 60 秒）。
  - 停止は data/stop_requested.flag を作成すると次サイクルで検出して終了します。

---

## 運用上のポイント / 注意事項

- KABUSYS_ENV=live 設定時は本番扱いであるため、LINE 通知や kill-switch 設定などの確認を強く推奨します。
- 本番では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って kill.flag をクリアして起動するリスクを避けるため）。
- ペーパートレードは本番 DB と分離されています（paper_trading 用 SQLite を使用）。
- 設計上、OrderSent の状態遷移はクラッシュ耐性を考慮して 2 相永続化を行います（OrderManager の実装を参照）。
- YAML 構成ファイル（config/*.yaml）のパースチェックは PyYAML が必要です。未インストール時は警告になります。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 自動ロードと Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 起動前設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor 起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py               — BrokerAPI の Protocol / データモデル / ファクトリ
    - broker_factory.py           — Settings に基づくクライアント生成
    - kabu_client.py              — kabuステーション REST クライアント
    - mock_client.py              — テスト用 Mock ブローカー
    - order_record.py             — OrderState / OrderRecord（状態遷移ロジック）
    - order_repository.py         — SQLite 永続化層
    - order_manager.py            — OrderState の外向け API（作成 / 送信 / 同期 / 取消）
    - execution_engine.py         — 発注エンジン（セッション管理）
    - reconciler.py               — 起動時リコンシリエーション
    - risk_manager.py             — Gate1/2/3 のリスク制御
  - data/
    - calendar_management.py      — マーケットカレンダー管理（DuckDB）
    - news_collector.py           — RSS ニュース収集
    - jquants_client.py           — （参照される J-Quants クライアント実装想定）
  - monitoring/
    - monitoring_db.py            — 監視 DB 初期化 / ログ用ユーティリティ（参照あり）
    - system_monitor.py           — 監視ロジック（参照あり）
  - utils/
    - logging_setup.py            — ロギング設定ユーティリティ（参照あり）
    - process_priority.py         — プロセス優先度設定ユーティリティ（参照あり）
  - config/                       — 設定用 YAML（system_config.yaml 等、存在推奨）
  - data/                         — デフォルトの DB / pid / flag 用ディレクトリ（runtime）

---

## 開発者向けメモ

- 設定の自動ロードは project root（.git または pyproject.toml を探索）を基準としています。テスト時などで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OrderRecord は純粋なビジネスロジック（DB 非依存）として設計されています。状態遷移や検証はここに集約されています。
- Reconciler は起動時に OrderSent の不確定注文を整理し、ローカル推定ポジションとブローカーのポジション差分を報告します。
- マーケットカレンダーは DuckDB に保存し、未登録日は曜日ベースでフォールバックするためデータ欠損時も挙動が安定します。

---

必要があれば、README に含めるサンプル .env ファイルや、各モジュール（ExecutionEngine、RiskManager、Reconciler 等）の利用例・シーケンス図、テスト方法の詳細を追加します。どの部分を詳しく書きたいか指示してください。