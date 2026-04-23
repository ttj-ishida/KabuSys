# KabuSys

日本株自動売買システム（ミニマム実装）  
このリポジトリは、発注エンジン、リスク管理、監視、カレンダー/ニュース収集などを含む自動売買基盤のコードベースです。設計はテスト可能性・クラッシュ耐性・再起動時リカバリ（リコンシリエーション）を念頭に置いています。

---

## プロジェクト概要

KabuSys は以下を提供します。

- 発注フロー（Signal → Order 作成 → Broker API 送信 → 状態同期）
- Order 状態機械（OrderRecord）と永続化（SQLite）
- ブローカークライアント抽象（実装: MockBrokerClient / KabuStationClient）
- リスク管理（Gate 1/2/3: シグナル検査、レート制限/サーキットブレーカー、ドローダウン監視）
- 起動時リコンシリエーション（OrderSent 状態の突合）
- 監視ループ（SystemMonitor をポーリング）
- 環境設定ウィザード（.env の対話式作成）
- 設定検証ツール（.env と config/*.yaml の事前チェック）
- マーケットカレンダー管理・ニュース収集などのデータ処理ユーティリティ

設計方針として、DB 操作とビジネスロジックを分離、API 呼び出しはクライアント層に集中させています。

---

## 主な機能一覧

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config (--strict オプションで警告を FAIL 扱い)
- 発注エンジン起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使い、本番 DB とは別の paper_trading DB を使用
- 監視ループ起動スクリプト: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
- Broker クライアント群:
  - KabuStationClient: kabuステーション REST API 実装（httpx, websocket-client を利用）
  - MockBrokerClient: 開発/テスト用のモック（fill_mode により挙動を変更可能）
- 注文永続化: SQLite（orders テーブル）と関連ユーティリティ（init_orders_db 等）
- リスク管理（RiskManager）: ポジション上限、余力、レート制限、サーキットブレーカー、ドローダウン監視
- データ処理:
  - マーケットカレンダー（DuckDB）
  - ニュース収集（RSS → raw_news、SSRF/サイズ制限考慮）

---

## セットアップ手順

前提: Python 3.10+

1. レポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install -r requirements.txt
   ```
   代表的な依存（requirements.txt がない場合の参考）:
   - duckdb
   - httpx
   - websocket-client
   - pyyaml (YAML 内容検証に使用; optional)
   - defusedxml
   - others: (標準ライブラリ以外のものは README や requirements に従ってください)

4. 初期設定 (.env) の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは既存の .env を読み込み、対話式で値を入力して .env を作成／更新します。
   - もしくは手動でプロジェクトルートに .env を作成（.env は絶対に Git にコミットしないでください）

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする:
   python -m kabusys.validate_config --strict
   ```

6. DB 初期化・起動
   - 実行スクリプト（run_execution/run_monitoring）は必要な初期テーブルを自動で作成します（init_monitoring_db / init_orders_db が呼ばれます）。
   - paper_trading モード使用時は PAPER_TRADING_SQLITE_PATH を確認してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / 任意（主なもの）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabu station ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番用アラート（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に既存の kill.flag を自動クリアするなら 1（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE — ペーパートレードの fill モード（instant | partial | never | reject）

設定は .env（.env.local があれば上書き）および OS 環境変数から読み込まれます。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。

---

## 使い方（起動例）

1. .env を作成・編集
   ```
   python -m kabusys.config_setup
   ```

2. 設定チェック
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

3. 発注エンジン起動（ローカルテスト: paper_trading）
   - 環境変数設定例:
     ```
     export KABUSYS_ENV=paper_trading
     export PAPER_FILL_MODE=instant
     ```
   - 起動:
     ```
     python -m kabusys.run_execution
     ```

   run_execution は:
   - Settings を読み、SQLite / DuckDB に接続
   - Broker クライアントを生成（paper_trading なら MockBrokerClient）
   - ExecutionEngine を起動してシグナル処理→push ドレイン→セッション終了まで動作

4. 監視ループ起動
   ```
   python -m kabusys.run_monitoring
   ```
   - MONITOR_POLL_INTERVAL を環境変数で変更可能（デフォルト 60 秒）

5. 停止
   - 実行中はプロジェクトルート/data に stop_requested.flag や kill.flag、pid ファイル等が作成されることがあります。これらを利用して外部から停止制御ができます。

注意:
- 本番（KABUSYS_ENV=live）では LINE の通知設定や KILL_FLAG の取り扱いなどを特に注意してください（validate_config で warn が出ます）。
- run_execution は起動時に既に stop_requested.flag が存在すると起動を行いません。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ宣言（バージョン等）
  - config.py — 環境変数読み込み / Settings クラス（アプリ設定）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — 発注エンジン起動スクリプト
  - run_monitoring.py — 監視ループ起動スクリプト
  - execution/
    - broker_api.py — Broker API 用データモデル、Protocol、ファクトリ
    - kabu_client.py — KabuStationClient（httpx/websocket 実装）
    - mock_client.py — MockBrokerClient（テスト用）
    - order_record.py — OrderRecord と状態遷移ロジック
    - order_repository.py — SQLite 永続化層（orders テーブル）
    - order_manager.py — Order 作成/送信/同期/取消を行う外向き API
    - execution_engine.py — シグナル処理と push ドレインのエンジン
    - reconciler.py — 起動時のリコンシリエーション（OrderSent 突合）
    - risk_manager.py — Gate1/2/3 のリスク制御
    - broker_factory.py — Settings に基づく Broker クライアント生成
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化・ログ関数（使用箇所あり）
    - system_monitor.py — 系統監視ロジック（ポーリング対象を集約）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB 機能）
    - news_collector.py — RSS ニュース収集（SSRF 対策等）
  - utils/
    - logging_setup.py — ログ初期化
    - process_priority.py — プロセス優先度の設定ユーティリティ
  - config/*.yaml — 各種設定テンプレート（存在しない場合は validate_config で警告）

---

## 実装上の注意 / 補足

- Settings は .env/.env.local と OS 環境変数を読み込みます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 注文送信の永続化設計はクラッシュ安全性を考慮しており、OrderSent 状態が残るケースを Reconciler が復旧します。
- MockBrokerClient は fill_mode（instant/partial/never/reject）により様々なテストシナリオを再現できます。
- YAML の内容検証は PyYAML がインストールされている場合のみ行われます（未導入でも警告でスキップ）。

---

## 開発 / デバッグのヒント

- ログレベルは LOG_LEVEL 環境変数で調整できます（DEBUG/INFO/...）。
- run_execution の動作を単体で検証する際は KABUSYS_ENV=development または paper_trading を使い、MockBrokerClient を利用すると kabu station をローカルで起動する必要がありません。
- DuckDB / SQLite のファイルパスは DUCKDB_PATH / SQLITE_PATH（および PAPER_TRADING_SQLITE_PATH）で制御できます。テスト用に新規パスを渡すと既存データに影響を与えません。

---

必要に応じて README にサンプル .env.example の追加や詳細な起動フロー（監視設定、LINE 通知セットアップ手順等）を追記できます。追記希望の項目があれば教えてください。