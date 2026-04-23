# KabuSys

日本株自動売買システムの一部（設定、実行エンジン、監視、データ収集など）。  
このリポジトリは、発注フロー（ExecutionEngine）、リスクガード、ブローカー抽象化（実ブローカー／モック）、監視ループ、カレンダー・ニュース取得などのコンポーネントを含みます。

> 注: README はこのコードベースの主要な使い方と構成をまとめたものです。実際の運用前には .env を適切に設定し、テストを十分に行ってください。  
> .env は機密情報を含むため、絶対にバージョン管理に含めないでください。

## 特徴（Overview / Features）

- 環境設定ウィザード（.env の対話式作成）
  - python -m kabusys.config_setup
- 起動前設定検証 CLI（.env と config/*.yaml のチェック）
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine：シグナル読み取り → 発注（Signal Pull 型）＋ WebSocket push ドレイン
  - 発注フローはクラッシュ耐性を考慮した 2 相永続化を採用
  - リコンシリエーション（起動時の復旧）
  - 3 段階リスクガード（Gate1: シグナル、Gate2: 実行/レート制限/CB、Gate3: ドローダウン）
- Mock ブローカー実装でローカル開発・テストが可能
- System monitoring 用のポーリングループ（監視専用プロセス）
- データモジュール（マーケットカレンダー管理、ニュース収集等）
- 設定は環境変数 / .env を利用（Settings クラスで管理）

## 必要条件（Dependencies）

主要な依存パッケージ（抜粋）：
- Python 3.9+
- duckdb
- httpx
- websocket-client
- defusedxml
- PyYAML（config/*.yaml のパース検証を有効にする場合）
- そのほか標準ライブラリ（sqlite3 等）

インストール例（仮想環境を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb httpx websocket-client defusedxml PyYAML
```

（プロジェクトに requirements.txt があればそちらを使用してください）

## 主要コマンド / 使い方

1. .env を作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - 既存の .env を読み込んで編集できます。ウィザード終了後に .env が保存されます。

2. 設定を検証
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い
   ```
   - 必須環境変数や config/*.yaml の存在・YAML パースをチェックします（PyYAML があれば中身のパースも行います）。

3. 実行エンジン起動（本番/ペーパートレード／開発）
   ```bash
   # ペーパートレード（モックブローカー利用）
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution

   # ローカル開発（モック）
   export KABUSYS_ENV=development
   python -m kabusys.run_execution

   # 監視プロセス（poll interval を変更可能）
   export MONITOR_POLL_INTERVAL=30
   python -m kabusys.run_monitoring
   ```

- 注意: `BrokerClientFactory` は KABUSYS_ENV が `paper_trading` または `development` のときに MockBrokerClient を返します。`live` は未実装です（将来の実ブローカー実装想定）。

## 重要な環境変数

必須（起動前に設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

よく使う（オプション／デフォルトあり）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL — kabu station API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用（任意）
- LINE_USER_ID — LINE 通知先（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1。デフォルト 0。本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring）

設定手順の一般的な流れ:
1. python -m kabusys.config_setup で .env を作成
2. python -m kabusys.validate_config で検証
3. DB スキーマの初期化（下記参照）
4. python -m kabusys.run_execution / run_monitoring を実行

## DB 初期化（簡易手順）

- 監視・注文保存用の SQLite（.sqlite_path）と、DuckDB（analysis 用）が必要です。
- 監視用テーブル・orders テーブルは init 関数で作成できます。

例: orders テーブルを作成する（.env の設定を使う）
```bash
python - <<'PY'
from kabusys.config import settings
import sqlite3
from kabusys.execution.order_repository import init_orders_db
from kabusys.monitoring.monitoring_db import init_monitoring_db

conn = sqlite3.connect(str(settings.sqlite_path))
init_orders_db(conn)        # orders テーブルの作成
init_monitoring_db(conn)    # monitoring 用テーブルの作成（monitoring モジュールに定義）
conn.close()
print("SQLite 初期化済み:", settings.sqlite_path)
PY
```

- DuckDB 側は signals / portfolio_targets / market_calendar 等のテーブルが必要です。これらは別途データ投入スクリプトや外部データ取得処理（J-Quants 連携など）で準備してください。

## 高レベル設計（How it works）

- ExecutionEngine（run_execution）
  - セッション: 標準は 8:50 にシグナル処理（pull）を実行し、9:10 以降は WebSocket push をドレイン、15:30 にセッション終了する設計。
  - 発注フローは OrderManager を中心に実装。OrderRecord（状態遷移ロジック）と OrderRepository（SQLite 永続化）により堅牢性を確保。
  - 発注時は（順序の理由で）OrderSent を DB に保存してからブローカー API を呼び、broker_order_id を保存して OrderAccepted に遷移することで、クラッシュ時の復旧をサポート。
  - Reconciler により、起動時に OrderSent の不確定注文を照合して状態を回復。ポジション差分を検出してログ出力。
  - RiskManager による 3 段階ガードで安全性を確保。

- Monitoring（run_monitoring）
  - DB（SQLite）に監視イベントを記録し、定期的にシステムリソース閾値などをチェック。
  - MONITOR_POLL_INTERVAL によりポーリング間隔を制御（デフォルト 60s）。

- ブローカー抽象化
  - BrokerAPIProtocol でインターフェースを定義。create_broker_api により Mock/KabuStation 実装を切替可能。
  - MockBrokerClient により挙動（instant/partial/never/reject）を指定して単体テストが可能。

## セキュリティ / 運用上の注意

- .env は機密情報（API トークンやパスワード）を含むため、絶対に Git 等にコミットしないでください。
- KABUSYS_ENV=live を設定した場合は本番環境に相当します。validate_config では live のとき注意喚起が出ます。LINE の通知設定や KILL_FLAG_CLEAR_ON_START の設定をよく確認してください。
- kill.flag（デフォルト: data/kill.flag）を用いて外部から停止指示を出す設計があります。起動時にこのフラグが残っていると起動を拒否する動作（clear_on_start により上書き可）があります。

## ディレクトリ構成

（src 配下の主要ファイル・パッケージ）
- src/kabusys/
  - __init__.py
  - config.py                 — Settings クラス（.env / 環境変数読み込み）
  - config_setup.py           — .env 作成ウィザード（CLI）
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine のエントリポイント（プロセス起動スクリプト）
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - execution/                — 発注・注文管理関連
    - __init__.py
    - broker_api.py           — Broker API 型 / データモデル / ファクトリ
    - kabu_client.py          — kabu station REST API クライアント
    - mock_client.py          — テスト用モックブローカー
    - broker_factory.py       — 設定からブローカーを生成するファクトリ
    - order_record.py         — 注文状態モデル・遷移ロジック
    - order_repository.py     — SQLite 永続化層（orders テーブル）
    - order_manager.py        — 発注 API（OrderRecord + Repository + Broker）
    - execution_engine.py     — ExecutionEngine 本体（シグナル処理・push ハンドラ）
    - reconciler.py           — 起動時リコンシリエーション
    - risk_manager.py         — 3 段階リスク管理
    - その他（order_* 等）
  - data/                     — データ関連（calendar_management, news_collector, jquants_client など）
    - calendar_management.py  — マーケットカレンダー管理
    - news_collector.py       — RSS ニュース収集
    - jquants_client.py       — J-Quants API 連携（想定）
  - monitoring/               — 監視 DB / SystemMonitor 等（init_monitoring_db 等）
  - utils/                    — ロギング設定やプロセス優先度調整など（logging_setup, process_priority 等）

（実際のリポジトリでは上記に加えて scripts や config ディレクトリ、ドキュメント等が含まれる場合があります）

## 開発メモ / 注意点

- config の自動読み込みは、プロジェクトルート（.git または pyproject.toml を基準）を検出して .env/.env.local を自動で読み込みます。テスト時や特殊ケースでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- validate_config は PyYAML がない場合、YAML 内容検証をスキップします（ファイル存在はチェック）。
- ExecutionEngine は PID ファイルや kill.flag を用いて単一プロセス運用や外部停止をサポートします。PID ファイルのパス等は Settings で指定可能です。
- DuckDB 側のテーブル（signals, portfolio_targets, market_calendar, position_entries など）は運用側で事前準備が必要です（DataPlatform 相当のバッチで投入）。

---

必要であれば以下を追加で提供できます：
- requirements.txt（実際に動作確認したバージョン列挙）
- DB 初期化スクリプト（orders / monitoring / DuckDB schema 用のサンプル）
- 運用手順書（デプロイ／systemd / Supervisor 用ユニット例）
- 詳細な設計ドキュメント（Sequence Diagram / 状態遷移表）

ご希望があれば、どれを優先して追加するか教えてください。