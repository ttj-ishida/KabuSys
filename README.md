# KabuSys

日本株向けの自動売買システム（プロジェクト骨格）。  
このリポジトリは発注フロー、リスクガード、リコンシリエーション、監視ループ、データ処理（カレンダー・ニュース収集）などを含む実行系のコアを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のようなコンポーネントで構成される自動売買フレームワークです。

- 環境変数ベースの設定管理（.env 読み込み・ウィザード）
- 設定検証ツール（起動前チェック）
- 発注エンジン（ExecutionEngine）
  - Signal Queue から発注を行う（シグナル処理 + WebSocket push ドレイン）
  - Order の状態管理（OrderRecord / OrderRepository）
  - OrderManager によるクラッシュ安全な発注フロー
  - RiskManager による 3 段階ガード（Gate1/2/3）
  - Reconciler による再起動後の自動復旧
- ブローカークライアント抽象（KabuStationClient / MockBrokerClient）
- 監視ループ（SystemMonitor をポーリング）
- データモジュール（マーケットカレンダー管理、RSS ニュース収集 など）

本リポジトリはローカル開発やペーパートレードで動作することを念頭に設計されています（KabuStation 実ブローカは将来対応。現状は Mock を主に利用）。

---

## 主な機能一覧

- .env 対話式ウィザード（python -m kabusys.config_setup）
- .env / config/*.yaml の起動前検証（python -m kabusys.validate_config）
- ExecutionEngine（シグナルに基づく発注ループ、WebSocket ドレイン）
- Order の状態管理と DB 永続化（SQLite）
- Reconciler による起動時の注文状態・ポジション同期
- RiskManager（余力、重複、ポジション上限、レート制限、サーキットブレーカー、ドローダウン監視）
- ブローカーファクトリ（Mock/KabuStation クライアント切替）
- Monitoring 用ポーリングループ（run_monitoring）
- DuckDB を利用したデータ処理（シグナルやカレンダー）
- ニュース収集（RSS）モジュール（SSRF対策・前処理・冪等保存）

---

## 必要条件 / 依存

推奨 Python バージョン: 3.9 以上

主要な外部パッケージ（プロジェクトに requirements.txt がない場合の例）:

- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（任意、config/*.yaml のパース検証に使用）
- （標準ライブラリ: sqlite3, logging など）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml PyYAML
```

※ 実運用で kabuステーション を使う場合は該当ソフトウェアの動作環境が別途必要です。

---

## セットアップ手順

1. リポジトリをクローンして作業環境を作る

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb httpx websocket-client defusedxml PyYAML
```

2. .env を作成する（対話式ウィザード推奨）

```bash
python -m kabusys.config_setup
```

対話ウィザードは既存の `.env` を読み込み、Enter で既存値を再利用できます。ウィザード終了後 `.env` が保存されます。

3. 設定検証（起動前チェック）

```bash
python -m kabusys.validate_config
# 警告も FAIL 扱いにする:
python -m kabusys.validate_config --strict
```

4. データディレクトリ作成（必要に応じて）

デフォルトの DB パス等は `data/` 以下に配置されます。自動生成される場合もありますが、手動で作成して権限などを整えておくと安心です。

---

## 環境変数（主要）

必須:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / 推奨:

- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
  - paper_trading: MockBroker を使い、paper_trading 用 SQLite に記録
  - live: 本番（注意喚起あり）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring)（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API の base URL（default: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時 kill.flag を自動クリアするか（0/1、デフォルト 0）
- PAPER_FILL_MODE — ペーパートレード時の fill モード（instant/partial/never/reject）、デフォルト `instant`
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

.env の生成や編集は `python -m kabusys.config_setup` を使うと簡単です。

---

## 使い方 / 実行コマンド

- 環境設定ウィザード（.env 作成/更新）

```bash
python -m kabusys.config_setup
```

- 設定検証

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
```

- 実行エンジン起動（発注エンジン）

```bash
python -m kabusys.run_execution
```

- 監視ループ起動（SystemMonitor ポーリング）

```bash
python -m kabusys.run_monitoring
# MONITOR_POLL_INTERVAL を短くする例:
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 停止・制御フラグ
  - グレースフルな外部停止: プロジェクトの data ディレクトリに `stop_requested.flag` を作成すると run_monitoring/run_execution のループが終了します。
  - Kill Switch: `KILL_FLAG_PATH`（デフォルト `data/kill.flag`）が存在すると ExecutionEngine は起動拒否、または起動中に kill スイッチを発動します。`KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動でクリアする挙動になります（本番では注意）。

---

## 主要な設計ポイント / 注意事項

- Order の永続化は SQLite（orders テーブル）で行い、同一 signal_id の active 注文を DB レベルで部分ユニーク制約で防止しています。
- OrderManager は「OrderCreated → OrderSent → (broker_order_id 保存) → OrderAccepted」の 2 段階／2 相永続化を取り入れ、クラッシュ後に Reconciler が状態回復できるように設計されています。
- RiskManager は 3 層（Gate1/2/3）に分かれており、レート制限やサーキットブレーカー、ドローダウンの閾値管理機構を持ちます。
- MockBrokerClient によりペーパートレードや単体テストが可能。PAPER_FILL_MODE によって挙動を切り替えられます。
- config モジュールは独自の `.env` パーサを持ち、`.env` / `.env.local` の自動読み込みを行います（OS 環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- YAML 検証は PyYAML があれば config/*.yaml をパースして検査します（なくても動くが警告が出ます）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義、__version__
  - config.py — 環境変数 / Settings クラス（settings インスタンス）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（発注エンジン）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py — execution 層の公開 API
    - broker_api.py — BrokerAPIProtocol, データモデル、例外、ファクトリ
    - broker_factory.py — Settings に基づくブローカクライアント生成
    - kabu_client.py — kabuステーション REST クライアント（HTTP / WebSocket 実装）
    - mock_client.py — MockBrokerClient（テスト・ペーパートレード用）
    - order_record.py — OrderRecord と状態遷移ロジック（純粋ビジネスロジック）
    - order_repository.py — SQLite を用いた永続化層（orders テーブル）
    - order_manager.py — 外向け API（発注・キャンセル・同期）
    - execution_engine.py — ExecutionEngine 本体（シグナル処理 / push ドレイン / kill）
    - reconciler.py — 起動時の注文・ポジション照合（自動復旧）
    - risk_manager.py — 3 段階リスクガード
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集（前処理・SSRF対策）
    - (jquants_client 等、他のデータ関連モジュールが想定されます)
  - monitoring/
    - monitoring_db.py (参照元あり) — 監視用 DB 初期化 / ログ機能（実装ファイルが存在する想定）
    - system_monitor.py (参照元あり) — システム監視ロジック（実装ファイルが存在する想定）
  - utils/
    - logging_setup.py (参照元あり) — ロギング初期化ヘルパ
    - process_priority.py (参照元あり) — プロセス優先度設定

（実際のリポジトリには上記参照先のファイルが存在します。ここでは主要ファイルを抜粋して記載しています。）

---

## 開発メモ / 拡張ポイント

- Live broker（KabuStationClient）を本番で使う場合は設定と接続先の整備、本番のテストが必要です。BrokerClientFactory は将来的な切替を想定しています。
- ExecutionEngine のセッションスケジュールや Gate の閾値は EngineConfig / RiskConfig で調整できます。
- calendar_update_job は J-Quants からカレンダーデータを取得して DuckDB に保存する想定。J-Quants クライアント実装が必要です。
- テストのため MockBrokerClient を活用してください。fill_mode を使って各種ケース（reject / never / partial / instant）を再現できます。

---

README の内容に不足や追加説明が必要であれば、実際に含めたい運用手順や環境（CI/CD、デプロイ方法、systemd ユニット例など）を教えてください。それに合わせて README を拡張します。