# KabuSys

日本株自動売買システムのコアライブラリ (開発中)

バージョン: 0.1.0

概要
- KabuSys は、日本株の自動売買を想定した小規模な実装フレームワークです。
- 発注フロー（ExecutionEngine）、注文状態管理、リスクガード、リコンシリエーション、監視ループ、データ処理（カレンダー・ニュース収集）などをモジュール化しています。
- 実環境では kabuステーション API を利用しますが、テスト／開発用に MockBrokerClient を用いた paper_trading モードを提供します。

主な特徴（機能一覧）
- 環境設定ウィザード（.env の対話的作成 / 更新）
  - python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の事前チェック）
  - python -m kabusys.validate_config [--strict]
- 実行エンジン（ExecutionEngine）
  - シグナルプル型発注、WebSocket push ドレイン、Kill Switch、PID 管理
  - python -m kabusys.run_execution
- 監視ループ（SystemMonitor 起動）
  - sqlite に監視ログを記録、ポーリング間隔の環境変数上書き可
  - python -m kabusys.run_monitoring
- ブローカー抽象化（BrokerAPIProtocol）
  - 本番用 KabuStationClient（kabuステーション REST API）
  - テスト用 MockBrokerClient（paper_trading / development 向け）
- 注文状態機構（OrderRecord / OrderManager / OrderRepository）
  - 状態遷移の検証、DB による永続化、安全な send_order フロー設計（クラッシュ耐性）
- リスク管理（3 段階ガード: Gate1/2/3）
  - 余力・重複・ポジション上限 / レート制限・サーキットブレーカー / ドローダウン監視
- リコンシリエーション（起動時の自動同期）
  - OrderSent 状態の突合せ、ポジション差分検出
- データユーティリティ
  - マーケットカレンダー管理（DuckDB 使用）
  - ニュース収集と前処理（RSS）

動作要件
- Python 3.10+
  - 型アノテーション（|）などを使用しているため 3.10 以上を想定しています
- 推奨依存パッケージ（プロジェクトの requirements.txt にて管理する想定）
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパースチェックで利用、任意）
- 標準ライブラリ: sqlite3, logging, threading, os, pathlib など

セットアップ手順
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml pyyaml
   - （requirements.txt がある場合は pip install -r requirements.txt）
4. .env を作成
   - 対話的ウィザードを使う:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考にする）
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります

主要な環境変数（代表）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / デフォルトあり
  - KABUSYS_ENV — 実行環境 (development / paper_trading / live)（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 sqlite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/...）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番通知用（任意）

使い方（よく使うコマンド）
- 環境ウィザード（.env を作成）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン（発注処理を開始）
  - 簡易（paper_trading 推奨）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - development でも MockBrokerClient を使用
  - live は現時点で本番クライアント未実装（BrokerClientFactory が NotImplementedError を投げます）
- 監視ループの起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- 起動制御
  - 停止フラグ: data/stop_requested.flag を作成すると監視／実行ループが検出して終了します
  - Kill Switch: data/kill.flag を作成すると ExecutionEngine が全 active 注文をキャンセルして停止します

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py — パッケージ定義、バージョン
    - config.py — 環境変数の読み込み・Settings（自動 .env ロード機能含む）
    - config_setup.py — .env 対話式ウィザード
    - validate_config.py — 起動前設定検証 CLI
    - run_execution.py — ExecutionEngine 起動スクリプト（main エントリ）
    - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
    - execution/ — 発注・注文管理・ブローカー層
      - broker_api.py — Protocol / データモデル / ファクトリ
      - kabu_client.py — kabuステーション REST API クライアント実装
      - mock_client.py — MockBrokerClient（テスト/開発用）
      - broker_factory.py — Settings に基づいてクライアントを生成
      - order_record.py — Order 状態モデルと遷移ロジック
      - order_repository.py — SQLite に対する永続化層
      - order_manager.py — 注文作成 / 送信 / 同期 / キャンセルの外向き API
      - execution_engine.py — セッション管理・シグナル処理・push ドレイン
      - reconciler.py — 起動時リコンシリエーション
      - risk_manager.py — Gate1/2/3 のリスクロジック
      - ...（他補助モジュール）
    - data/ — データ関連モジュール
      - calendar_management.py — マーケットカレンダー管理（DuckDB）
      - news_collector.py — RSS ニュース収集・前処理
    - monitoring/ — 監視 DB / SystemMonitor（監視関連コード）
    - utils/ — ロギング設定やプロセス優先度設定等のユーティリティ
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  - （config/*.yaml は存在しない場合、validate_config で警告。generate_config.py 参照の旨メッセージあり）
- data/
  - *.db（DUCKDB / SQLite / PID / flag ファイル等を配置）
- .env, .env.local — 環境変数ファイル（.env は絶対に Git にコミットしないこと）

設計上の注意点
- Settings は自動でプロジェクトルートの .env を読み込みます（OS 環境変数より下位）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading / development モードでは MockBrokerClient を使い、実際の発注は行われません。テストと実運用の DB を分離するため paper_trading 用 SQLite を別ファイルに保存します。
- ExecutionEngine の発注フローはクラッシュ耐性を考慮した二相的な永続化（OrderSent 保存 → broker 呼び出し → broker_order_id 保存 → OrderAccepted へ遷移）を採用しています。
- live 環境は運用リスクが高く、環境変数のチェックや LINE 通知などの設定漏れに注意が必要です（validate_config は live 時に追加警告を出します）。

開発者向けメモ
- 注文状態遷移の整合性は OrderRecord.transition_to() と _ALLOWED_TRANSITIONS で厳密に管理しています。テストでは状態遷移の網羅を推奨します。
- リコンシリエーション（Reconciler）は起動時に OrderSent の不確定注文をブローカーと照合し、ポジションの差分をログに記録します。
- calendar_management は DuckDB の market_calendar を参照します。DB にデータがない場合は曜日ベースのフォールバックを行います。

ライセンス・貢献
- （ここにプロジェクトのライセンスやコントリビュート手順を記載してください）

お問い合わせ
- プロジェクト内のコードコメントや docstring に設計意図が記載されています。わからない点は issue を立てるか、リポジトリの担当者に問い合わせてください。

以上がこのリポジトリの README です。追加でサンプル .env のテンプレートや requirements.txt、起動スクリプトの systemd ユニット例などを追記したい場合は教えてください。