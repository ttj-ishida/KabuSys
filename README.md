# KabuSys

日本株自動売買システム (KabuSys) — 軽量な発注エンジン・監視・設定管理を備えたプロジェクトです。  
（この README は src/ 以下のコードを基に作成しています）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の要素を含む自動売買基盤です。

- シグナルを読み取って発注する ExecutionEngine（発注ロジック、リスクガード、リコンシリエーション）
- kabuステーション API 用クライアント（実装: KabuStationClient）とテスト用の Mock クライアント
- 注文状態を表す OrderRecord / OrderRepository（SQLite 永続化）
- 起動時・運用時の安全装置（Kill Switch、サーキットブレーカー、レートリミット、ドローダウン監視）
- 監視プロセス（SystemMonitor）と監視 DB（SQLite）
- 環境設定ウィザード（.env の対話的生成）と設定検証 CLI
- データ処理ユーティリティ（DuckDB を用いたマーケットカレンダー、ニュース収集など）
- 設定は環境変数（.env/.env.local）中心で管理

設計方針として、API クライアント層・ビジネスロジック層・永続化層を分離し、クラッシュ安全性（2相永続化、リコンシリエーション）や運用時の保護（kill.flag 等）を重視しています。

---

## 主な機能一覧

- 環境設定
  - config_setup: 対話式ウィザードで .env を作成・更新（python -m kabusys.config_setup）
  - validate_config: 起動前に .env と config/*.yaml の妥当性をチェック（python -m kabusys.validate_config [--strict]）
- 発注 / 実行
  - ExecutionEngine: シグナル処理ループ + WebSocket push ドレインループで発注を実行
  - OrderManager: 注文作成・送信・同期・キャンセルの一連処理（状態遷移の検証）
  - Broker クライアント:
    - MockBrokerClient（テスト用）
    - KabuStationClient（kabuステーション REST API 実装）
  - Reconciler: 再起動時に未確定注文を照合・同期、ポジション差分の検出
- リスク管理
  - RiskManager: Gate1 (信号レベル: 余力/重複/ポジション上限)、Gate2 (レート制限・サーキットブレーカー)、Gate3 (ドローダウン監視)
- 永続化
  - OrderRepository: SQLite による注文テーブル/インデックス管理・CRUD
  - DuckDB を利用した分析用・データ処理（カレンダー、シグナル読み込みなど）
- 監視
  - run_monitoring: SystemMonitor ポーリングループ（MONITOR_POLL_INTERVAL で間隔調整）
  - 監視用 DB（SQLite）にイベントを記録
- データ処理モジュール
  - calendar_management: JPX カレンダーの取り扱い・次営業日判定等
  - news_collector: RSS 収集・前処理・保存ロジック（SSRF 対策、XML の安全パース）

---

## セットアップ手順（開発・ローカル実行向け）

前提: Python 3.10+ を想定（型注釈に | を使用）。プロジェクトルートに `src/` がある構成です。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 無ければ最低限必要な主なパッケージを個別にインストール:
     - pip install httpx websocket-client duckdb defusedxml
     - オプション: PyYAML（config/*.yaml 内容検証に使用）
       - pip install pyyaml

   （コード内で使われているライブラリ: httpx, websocket-client, duckdb, defusedxml, PyYAML（任意））

4. data ディレクトリを作成（デフォルトパスを利用する場合）
   - mkdir -p data

5. .env の作成（対話式）
   - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example がある場合は参照）

6. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする: python -m kabusys.validate_config --strict

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（よく使うもの）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し paper_trading 用 SQLite に保存
  - live: 本番（注意: live 用ブローカークライアントは未実装の箇所があります）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB (SQLite) のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に既存 kill.flag を自動クリア（0 推奨）

運用用（監視・実行）:
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

重要: .env ファイルは絶対に Git にコミットしないでください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（対話式、.env を生成/更新）
  - python -m kabusys.config_setup
  - オプション: --env-file を指定して保存先を変更可能

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - すべての警告をエラー扱いにして終了コード 1 を返す: --strict

- 実行エンジン起動（1日分のセッションを実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV による挙動:
    - development / paper_trading: MockBrokerClient を使用
    - live: 本番挙動（注意: 未実装部分あり）

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を上書き可能

運用上のファイルフラグ:
- data/stop_requested.flag: 存在すると実行ループが停止する（run_execution/run_monitoring が検出）
- kill.flag（デフォルト KILL_FLAG_PATH=data/kill.flag）:
  - 存在すると ExecutionEngine は起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアして起動）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールとファイルです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/.env の自動読み込み・Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — 実行エンジン起動スクリプト
  - run_monitoring.py — 監視ループ起動スクリプト

  - execution/
    - __init__.py
    - broker_api.py — BrokerAPIProtocol, データモデル, 例外, ファクトリ
    - kabu_client.py — KabuStationClient（kabuステーション REST 実装）
    - mock_client.py — MockBrokerClient（テスト用）
    - broker_factory.py — Settings に基づくクライアント生成
    - order_record.py — OrderRecord と状態遷移ロジック
    - order_repository.py — SQLite 永続化層（orders テーブル）
    - order_manager.py — 外向き注文 API（create/send/sync/cancel）
    - execution_engine.py — ExecutionEngine（シグナル処理・push ドレイン）
    - risk_manager.py — RiskManager（Gate1/2/3）
    - reconciler.py — 再起動時リコンシリエーション

  - monitoring/
    - monitoring_db.py — 監視用 DB 初期化・ログ
    - system_monitor.py — システム監視ロジック

  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py — RSS ニュース収集
    - jquants_client.py — J-Quants API 連携（参照される想定）

  - utils/
    - logging_setup.py — ロギング初期化ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ

- その他
  - config/*.yaml — 設定テンプレート（存在チェックあり）
  - .env, .env.local — 環境変数（ローカルで管理）

---

## 運用上の注意 / トラブルシューティング

- .env を誤ってコミットしないでください（README 内でも何度も警告しています）。
- validate_config は PyYAML が未インストールだと YAML 内容検証をスキップします（警告のみ表示）。PyYAML を導入すれば config/*.yaml のパース検証が有効になります。
- KABUSYS_ENV=live の場合は本番挙動になります。LINE 通知などの設定を忘れるとアラートが届きません。validate_config で警告が出ます。
- 起動時に kill.flag が存在すると起動が拒否されます（KILL_FLAG_CLEAR_ON_START=1 で自動クリア可能）。
- run_execution はデータベース接続（SQLite / DuckDB）を行います。paths（DUCKDB_PATH, SQLITE_PATH）が適切に設定されているか確認してください。
- MockBrokerClient はテスト用に発注の挙動を模擬します（fill_mode: instant / partial / never / reject）。
- Reconciler は OrderSent の未確定注文を broker 側と照合して回復するため、クラッシュ後は起動時に Reconciler を実行することが重要です（ExecutionEngine は起動時に実行します）。

---

## 開発者向けメモ

- 注文の状態遷移は OrderRecord.transition_to で検証され、不正遷移は InvalidStateTransitionError を発生させます。
- OrderManager.send_order はクラッシュ耐性を考え、OrderSent の永続化を broker 呼び出しの前後で分離した 2 相永続化を採用しています（broker_order_id を先に保存 → 状態遷移を保存）。
- RiskManager はトークンバケツ方式でレート制限を実装し、サーキットブレーカーはエラー回数・ウィンドウで管理します。
- calendar_management は DuckDB の market_calendar テーブルが存在しない場合は曜日ベースでフォールバックします。

---

必要であれば README にサンプル .env（サニティチェック用の雛形）、実行例のログ出力例、さらに細かな設定パラメータの説明（RiskConfig の各値の意味）などを追加できます。どの情報を追加しますか？