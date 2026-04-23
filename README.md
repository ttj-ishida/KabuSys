# KabuSys

日本株自動売買システム（簡易版）

このリポジトリは、kabuステーション（および J-Quants）を利用した自動売買コンポーネント群を含むサンプル実装です。発注フロー、リスクガード、リコンシリエーション、監視、データ処理（マーケットカレンダー・ニュース収集）などの主要機能を提供します。開発 / ペーパートレード向けにモックブローカーを利用でき、本番（live）は慎重な扱いが必要です。

## 主な特徴（機能一覧）

- 環境設定ウィザード（.env を対話的に生成 / 更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の整合性チェック）
  - python -m kabusys.validate_config [--strict]
- ExecutionEngine：シグナルプル型の発注エンジン
  - シグナル処理（発注窓口） + WebSocket push ドレイン
  - Order 管理（OrderRecord, OrderRepository, OrderManager）
  - リスク管理（3段階ガード: Gate1/2/3）
  - リコンシリエーション（再起動時の OrderSent 同期・ポジション差分検出）
- Broker クライアント層
  - MockBrokerClient（テスト / ペーパー用）
  - KabuStationClient（kabuステーション REST / WebSocket 実装）
- 監視プロセス（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
- データユーティリティ
  - マーケットカレンダー管理（DuckDB を利用）
  - ニュース収集（RSS、安全対策実装）
- その他ユーティリティ
  - ログ設定・プロセス優先度設定・PID / kill フラグ管理など

## セットアップ手順

1. リポジトリを取得
   - git clone ... などで取得してください。

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - なければ最低限下記パッケージをインストールしてください:
     - pip install duckdb httpx websocket-client defusedxml PyYAML

   （必要に応じて他のパッケージも追加でインストールしてください）

4. data ディレクトリを作成
   - mkdir -p data

5. 環境変数の初期化（.env 作成）
   - 対話的ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を FAIL として扱う場合:
     - python -m kabusys.validate_config --strict

注意:
- 自動で .env をプロジェクトルートの `.env` / `.env.local` から読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `.env` は絶対に Git にコミットしないでください（秘密情報が含まれます）。

## 環境変数（主なキー）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / 任意:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL — kabuステーションのベース URL
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（任意）
- LINE_USER_ID — LINE 通知先ユーザー（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（0/1）
- PAPER_FILL_MODE — paper_trading 時のモックの約定動作（instant/partial/never/reject）

デフォルトの多くは `python -m kabusys.config_setup` のウィザードで入力できます。

## 使い方（実行方法）

- 環境ウィザード（.env 作成 / 更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を失敗扱い）:
    - python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書き: 環境変数 `MONITOR_POLL_INTERVAL`（秒）

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録します。
  - 注意: `live` 環境のブローカークライアントは未実装（NotImplementedError）。本番稼働には追加実装が必要です。

- 停止 / Kill フラグ
  - 停止用フラグ: data/stop_requested.flag（監視・実行ループでチェック）
  - Kill スイッチ: data/kill.flag。ExecutionEngine 起動前に kill.flag が存在すると起動を拒否（`KILL_FLAG_CLEAR_ON_START=1` の場合のみ起動時に自動クリアされます）。

## ディレクトリ構成（主要ファイル）

（プロジェクトルートの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - execution/               — 発注関連サブパッケージ
    - __init__.py
    - broker_api.py          — Broker API の Protocol / データモデル / ファクトリ
    - kabu_client.py         — kabuステーション REST/WebSocket クライアント
    - mock_client.py         — MockBrokerClient（テスト用）
    - broker_factory.py      — Settings に応じたブローカーファクトリ
    - order_record.py        — Order の状態遷移ロジック（純粋モデル）
    - order_repository.py    — SQLite 永続化層
    - order_manager.py       — Order 発行 / 送信 / 同期 / 取消 管理
    - execution_engine.py    — ExecutionEngine（メイン発注ロジック）
    - reconciler.py          — 再起動時のリコンシリエーション
    - risk_manager.py        — Gate1/2/3 を実装するリスク管理
  - data/                    — データ関連モジュール
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集（安全対策実装）
    - jquants_client.py      — （参照）J-Quants クライアント（実装想定）
  - monitoring/              — 監視関連（DB 初期化等を含む想定）
    - monitoring_db.py       — 監視 DB 初期化 / 書き込みユーティリティ
    - system_monitor.py      — システム監視ロジック（ポーリング）

（上記以外にも strategy / execution の補助モジュールが含まれます）

## 実装上の注意・設計ポイント

- 発注のクラッシュ安全性
  - OrderManager.send_order は OrderSent の永続化→ブローカー呼び出し→broker_order_id 永続化→OrderAccepted の順で 2 相永続化を行い、クラッシュ時でもリコンシリエーションで復旧可能にしています。
- リスクガード
  - Gate1（シグナル単位）: 余力・重複・ポジション上限をチェック
  - Gate2（実行単位）: トークンバケツによるレート制限・サーキットブレーカー
  - Gate3（約定後）: ドローダウン監視（一定閾値超過で kill_switch）
- MockBrokerClient によって paper_trading / 開発で現物環境に依存せずテスト可能
- KabuStationClient は REST と WebSocket をサポート（httpx / websocket-client を使用）
- カレンダーロジックは DuckDB の market_calendar を優先、未登録日は曜日ベースでフォールバック

## 推奨ワークフロー（初回セットアップ）

1. 仮想環境を作成し依存をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定を確認
4. data ディレクトリの作成・DB 初期化（監視 DB / orders テーブル等は各モジュールの init_* 関数で行われます）
5. python -m kabusys.run_monitoring を別プロセスで起動
6. python -m kabusys.run_execution を起動して発注セッションを運用（paper_trading でまず検証）

## ライセンス / 責任範囲

- 本リポジトリは教育・参考実装です。実際の資金を運用する場合は十分な監査とテスト、規制順守を行ってください。
- Live 環境（実際の発注）で利用する場合は安全措置（監査、フェイルセーフ、十分な監視）を必ず実装してください。kabuステーション連携や資金移動に関しては自己責任での運用になります。

---

何か追加で README に含めたい具体的な情報（例: 実際の config/*.yaml のフォーマット、CI 用のコマンド、テストの実行方法等）があれば教えてください。必要に応じて追記します。