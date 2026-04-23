# KabuSys

日本株自動売買システムの小規模実装（ライブラリ + 起動スクリプト群）

このリポジトリは、kabuステーション等のブローカー API と連携する自動売買エンジンの主要コンポーネントを含みます。ローカル開発／ペーパートレード用途を重視して設計されており、設定ウィザードや設定検証、監視プロセス、発注エンジンなどが実装されています。

- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能

- 環境設定ウィザード（.env の対話式作成・更新）
  - `python -m kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の事前チェック）
  - `python -m kabusys.validate_config [--strict]`
- 実行エンジン（ExecutionEngine）
  - シグナル読み込み → Gate1/Gate2 のリスクガード → 発注 → WebSocket プッシュの処理ループ
  - paper_trading / development では MockBrokerClient を利用（本番ブローカーは未実装）
- 発注周りの堅牢性設計
  - OrderRecord（状態遷移ロジック）
  - OrderRepository（SQLite 永続化）
  - OrderManager（DB と Broker の橋渡し、クラッシュ安全性考慮）
  - Reconciler（起動時に OrderSent の不整合をブローカーと照合して復旧）
- リスク管理（3段階: Gate1/Gate2/Gate3）
  - ポジション・余力・重複・レート制限・サーキットブレーカー・ドローダウン監視
- 監視プロセス（SystemMonitor のポーリングループ）
  - `python -m kabusys.run_monitoring`
- ブローカークライアント群
  - MockBrokerClient（テスト／開発用）
  - KabuStationClient（kabuステーション REST / WebSocket クライアント：同期 httpx + websocket-client）
- データユーティリティ
  - 市場カレンダー管理（DuckDB + J-Quants 連携想定）
  - ニュース収集（RSS 収集・前処理・DB 保存想定、XML/SSRF 対策あり）

---

## 必要環境（例）

- Python 3.9+（型注釈と一部の標準ライブラリ機能を利用）
- 推奨パッケージ（代表例）:
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml のパース検証で使用。未インストールでも動作はするが警告が出る）
  - defusedxml

パッケージの正確な依存関係は requirements ファイル等にまとめてください（本リポジトリには含まれない場合があります）。

---

## セットアップ手順（開発向けの基本）

1. リポジトリをクローンし、仮想環境を作成して有効化します。
   - 例（Unix/macOS）:
     - python -m venv .venv
     - source .venv/bin/activate
2. 依存パッケージをインストールします（プロジェクトに requirements.txt があればそれを使用）。
   - pip install duckdb httpx websocket-client defusedxml PyYAML
3. .env を作成します（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   - もしくはルートに .env ファイルを手動で用意する（.env.local を使ってローカル上書きも可能）
4. 設定検証を行います:
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     - python -m kabusys.validate_config --strict

注意: .env は絶対に Git にコミットしないでください（ウィザードもヘッダーでその旨を出力します）。

---

## 重要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意／設定例:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KILL_FLAG_CLEAR_ON_START — 本番での kill.flag 自動クリア（0/1）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート通知（任意）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると自動で .env をロードしません（テスト等で使用）

.env の自動ロード順序:
- OS 環境変数 > .env.local > .env
- プロジェクトルートの判定は .git または pyproject.toml を基準に行います

---

## 使い方（主要コマンド）

- 環境設定ウィザード（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - オプション: --strict（警告でも exit(1)）
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）
- 実行エンジン起動（発注プロセス）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV により MockBrokerClient（paper_trading / development）か本番クライアントになる（本番クライアントは未実装で NotImplementedError）

実行中の停止は、ルートの data/stop_requested.flag ファイル検知または kill.flag による仕組みで行います。PID ファイルや kill.flag の挙動は Settings で制御します。

---

## 設計上のポイント（運用メモ）

- 発注のクラッシュ安全性:
  - OrderManager.send_order は「OrderSent を DB に永続化 → ブローカー呼び出し → broker_order_id を DB にコミット → OrderAccepted へ更新」という二相的に近い永続化戦略で不整合を軽減しています。
  - Reconciler による起動時同期で OrderSent の未確定注文を照合し、可能な限り回復します。
- リスクガード:
  - Gate1: シグナルごとの余力／重複／ポジション上限
  - Gate2: レート制限（トークンバケツ）／サーキットブレーカー
  - Gate3: ドローダウン監視（約定後のポートフォリオ監視）
- paper_trading と本番 DB は分離:
  - paper_trading では PAPER_TRADING_SQLITE_PATH を使用し、本番の sqlite_path を汚さないようにしています。
- WebSocket:
  - KabuStationClient は WebSocket の push を受け取り、ExecutionEngine の _push_queue に投入することで推移通知を処理します。

---

## ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — .env 読み込みと Settings
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 起動前設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor 起動スクリプト
    - data/
      - calendar_management.py  — 市場カレンダー管理（DuckDB + J-Quants）
      - news_collector.py       — RSS ニュース収集
      - jquants_client.py       — （想定）J-Quants API クライアント
    - execution/
      - __init__.py
      - broker_api.py           — BrokerAPI のデータモデル / Protocol / ファクトリ
      - broker_factory.py       — Settings に従う Broker クライアント生成
      - kabu_client.py          — kabuステーション REST/WebSocket クライアント
      - mock_client.py          — テスト用モッククライアント
      - order_record.py         — 注文状態モデル（状態遷移）
      - order_repository.py     — SQLite 永続化
      - order_manager.py        — 発注フロー管理（OrderState machine の外向き API）
      - execution_engine.py     — 発注エンジン（セッション・ループ）
      - reconciler.py           — 起動時リコンシリエーション
      - risk_manager.py         — 3段階リスクガード
      - ...（その他コンポーネント）
    - monitoring/
      - monitoring_db.py        — 監視 DB 初期化・ログ関数（実装参照）
      - system_monitor.py       — システム監視ロジック
    - utils/
      - logging_setup.py        — ロギング設定ユーティリティ
      - process_priority.py     — プロセス優先度設定ユーティリティ
    - ...（他の補助モジュール）

---

## 開発・運用上の注意

- .env ファイルは機密情報を含むため絶対にリポジトリにコミットしないでください。
- config/*.yaml（system_config.yaml 等）は存在しない場合ウィザードや generate スクリプトで生成する想定。PyYAML がないと中身の検証はスキップされます。
- KABUSYS_ENV=live を指定する場合は特に注意してください（validate_config は live を検出すると警告を出します）。LINE 通知や kill flag 設定など本番向けの追加チェックがあります。
- 本番ブローカークライアント（KabuStationClient）を使うには kabuステーション® が適切に稼働していること、および API パスワード等の設定が必要です。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。

---

## 参考コマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン:
  - python -m kabusys.run_execution
- 監視ループ:
  - python -m kabusys.run_monitoring

---

この README はコードベースの主要機能と運用の概要をまとめたものです。詳細な API や DB スキーマ、運用手順（デプロイ、バックアップ、監視、リカバリ）については別途ドキュメント化することを推奨します。質問や補足説明が必要であれば教えてください。