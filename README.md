# KabuSys

日本株自動売買システム（開発中） — この README はコードベースの主要機能・セットアップ・使い方を簡潔にまとめたものです。

主に以下のモジュールを含みます（抜粋）:
- 環境設定管理 / ウィザード: kabusys.config, kabusys.config_setup
- 設定検証 CLI: kabusys.validate_config
- 実行エンジン起動スクリプト: kabusys.run_execution
- 監視（Monitoring）起動スクリプト: kabusys.run_monitoring
- Execution 層（注文管理・ブローカ API 抽象化・リスク管理等）: kabusys.execution.*
- Data 層（カレンダー管理、ニュース収集等）: kabusys.data.*

---

## プロジェクト概要

KabuSys は、日本株の自動売買を目的としたシステム設計の実装例です。  
設計上の特徴:
- ブローカー API 抽象化（実装: MockBrokerClient / 将来: KabuStationClient）
- 発注の堅牢な状態遷移（OrderRecord を中心とした状態遷移検証）
- リスクガード（Gate1〜3: シグナル・実行・メトリクスレベル）
- 起動時の再同期（Reconciler）によるクラッシュ復旧
- .env ベースの設定管理と対話的ウィザード、起動前検証ツール

注意:
- KABUSYS_ENV=live（本番）モードはコード中で本格的なライブブローカー利用が未実装の箇所があります（BrokerClientFactory は live で NotImplementedError を投げます）。開発／ペーパートレードでの利用が想定されています。

---

## 機能一覧

- .env/.env.local からの自動ロード（OS 環境変数より低優先）
- 対話式 .env 生成ウィザード（python -m kabusys.config_setup）
- 起動前設定検証 CLI（必須環境変数・YAML ファイル・パス等をチェック）
- ExecutionEngine
  - シグナル読み込み（DuckDB）
  - Gate1/2/3 によるリスクチェック
  - 発注フロー（作成 → 送信 → 同期 → 取消）
  - WebSocket プッシュの受信・ドレイン
  - PID / kill.flag 制御
- Reconciler（起動時の OrderSent 注文照合・ポジション差分検出）
- MockBrokerClient（paper_trading・開発用のモック）
- Monitoring（SystemMonitor のポーリングループ）
- Data 層: マーケットカレンダー管理、ニュース収集（RSS）等

---

## 前提（推奨）環境

- Python 3.9+（型注釈などを利用）
- 推奨パッケージ（最低限）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（validate_config の YAML パースに必要、無くても動作するが検証は省略される）
  - defusedxml（news_collector で使用）
- SQLite（組み込み）/ DuckDB（分析用 DB）

requirements.txt がない場合は手動でインストールしてください（例）:
```
pip install duckdb httpx websocket-client pyyaml defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb httpx websocket-client pyyaml defusedxml
   ```

4. .env を作成
   - 対話式ウィザードを使うのが簡単です（次節参照）。
   - もしくはプロジェクトルートに手動で .env を配置します。

5. 初回実行前に必要なら DB 用ディレクトリを作成（デフォルトは data/）
   ```
   mkdir -p data
   ```

---

## 設定（.env）

自動ロード順序:
- OS 環境変数（最優先）
- .env （プロジェクトルート）
- .env.local（.env の上書き）

自動ロードを無効化するには:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な環境変数（必須 / 重要）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- LINE_CHANNEL_ACCESS_TOKEN（任意、監視通知）
- LINE_USER_ID（任意、監視通知）
- KILL_FLAG_CLEAR_ON_START（0/1、デフォルト: 0）

.kabusys/config_setup.py のウィザードで入力支援できます。

---

## 使い方

### 1) 環境設定ウィザード（.env を生成）
対話式で .env を作成・更新します。
```
python -m kabusys.config_setup
```
オプション:
```
python -m kabusys.config_setup --env-file path/to/.env
```

ウィザード完了後は、.env を保存してから validate を実行することを推奨します。

### 2) 起動前設定検証
.env および config/*.yaml の不備を検出します。
```
python -m kabusys.validate_config
# 警告も FAIL 扱いにする場合
python -m kabusys.validate_config --strict
```
- PyYAML がインストールされていると config/*.yaml の YAML パース検証も行います。
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）やパスの存在などをチェックします。

### 3) Execution エンジンを起動（本番的なセッション）
通常は paper_trading（モックブローカー）か development で実行します。
```
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
挙動:
- paper_trading では MockBrokerClient を使い、paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
- 起動時に data/execution.pid を書き、停止時は削除します。
- 停止要求はプロジェクトルート下の data/stop_requested.flag の作成で行えます。
- 起動前に data/kill.flag があると、KILL_FLAG_CLEAR_ON_START によって挙動が変わります（0: 起動拒否、1: 自動クリアして起動）。

注意: live モードは未実装箇所があります（BrokerClientFactory 参照）。

### 4) Monitoring を起動（監視ループ）
```
python -m kabusys.run_monitoring
```
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定（デフォルト: 60）。
- 監視は sqlite_path（settings.sqlite_path）と duckdb_path を使用します。
- 停止は data/stop_requested.flag を作成してください。

---

## 実装上のポイント / 運用上の注意

- 発注フローは二相永続化を採用（OrderSent を DB に保存してから broker 呼び出し）しており、クラッシュ後は Reconciler が復旧を試みます。
- OrderRecord.transition_to により状態遷移を厳密に検証します。不正な遷移は例外になります。
- RiskManager は 3 段階のガード（シグナル、実行、メトリクス）で安全性を高めます。サーキットブレーカーやレート制限も組み込まれています。
- 本番（live）運用はリスクが高く、LINE などの通知設定を必ず確認してください（validate_config は live の場合に警告を出します）。

---

## ディレクトリ構成（抜粋）

プロジェクトルート（省略）  
├─ config/  
│   ├─ system_config.yaml  
│   ├─ data_config.yaml  
│   ├─ strategy_config.yaml  
│   ├─ risk_config.yaml  
│   ├─ execution_config.yaml  
│   └─ monitoring_config.yaml  
├─ data/  (デフォルトの DB / PID / フラグを置く場所)  
└─ src/  
   └─ kabusys/  
      ├─ __init__.py
      ├─ config.py                   # 環境変数読み込み / Settings 定義
      ├─ config_setup.py             # .env ウィザード（CLI）
      ├─ validate_config.py          # 設定検証 CLI
      ├─ run_execution.py            # Execution 起動スクリプト
      ├─ run_monitoring.py           # Monitoring 起動スクリプト
      ├─ execution/
      │   ├─ __init__.py
      │   ├─ broker_api.py
      │   ├─ broker_factory.py
      │   ├─ kabu_client.py
      │   ├─ mock_client.py
      │   ├─ order_record.py
      │   ├─ order_repository.py
      │   ├─ order_manager.py
      │   ├─ execution_engine.py
      │   ├─ reconciler.py
      │   └─ risk_manager.py
      ├─ data/
      │   ├─ calendar_management.py
      │   ├─ news_collector.py
      │   └─ jquants_client.py (想定)
      ├─ monitoring/
      │   └─ monitoring_db.py, system_monitor.py (想定)
      └─ utils/
          ├─ logging_setup.py
          └─ process_priority.py

（上記はコード抜粋に基づく概略構成です。実際のリポジトリではさらにファイルやサブパッケージがあります。）

---

## よくある操作とトラブルシューティング

- validate_config が YAML パースをスキップする:
  - PyYAML がインストールされていないためです。`pip install pyyaml` を行ってください。

- 実行しても発注されない / モックしか使われる:
  - KABUSYS_ENV が `paper_trading` または `development` の場合、MockBrokerClient が選ばれます。`live` は未実装領域があるため注意。

- 起動後にすぐ終了する:
  - data/kill.flag が存在する場合、KILL_FLAG_CLEAR_ON_START により挙動が異なります（0: 起動拒否、1: クリアして起動）。

- ポーリング間隔を変更したい:
  - Monitoring: `MONITOR_POLL_INTERVAL` を秒数で指定します。

---

もし README に加えたい具体的なサンプル .env、運用手順（systemd ユニット例など）、あるいは各モジュールの詳細設計ドキュメントが必要であれば教えてください。必要に応じて追記・テンプレート作成します。