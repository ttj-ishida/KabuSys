# KabuSys

日本株自動売買システムの簡易実装（ライブラリ/実行スクリプト群）。  
このリポジトリは注文発行・再突合（reconciliation）・監視・リスク管理など、実運用を想定した主要コンポーネントを含みます。テスト／開発時は Mock ブローカークライアントで動作させることで kabuステーションが不要です。

## プロジェクト概要
- 注文フロー（Signal → Order 作成 → Broker 送信 → 状態同期）を実装した ExecutionEngine。
- 注文の状態管理を行う OrderRecord / OrderManager / OrderRepository（SQLite ベース）。
- kabuステーション向け実クライアント（KabuStationClient）と、テスト用 MockBrokerClient。
- 起動時のリコンシリエーション（Reconciler）で OrderSent 状態の自動同期。
- 3段階のリスクガード（Gate1: シグナル検査 / Gate2: レート制限・サーキットブレーカー / Gate3: ドローダウン監視）。
- 監視用プロセス（run_monitoring）および監視データ保存（SQLite / DuckDB）。
- 環境設定ウィザード（.env 作成支援）と設定検証ツール（.env と config/*.yaml のチェック）。
- Data サブモジュール：マーケットカレンダー管理やニュース収集など（DuckDB ベースのデータ処理）。

## 主な機能一覧
- 環境変数読み込み（.env / .env.local、自動読み込み機能）
- .env 対応の対話式ウィザード（python -m kabusys.config_setup）
- 起動前の設定検証（python -m kabusys.validate_config）
- ExecutionEngine（シグナルを読み込み発注、WebSocket push ドレイン）
- OrderManager（注文作成・送信・同期・キャンセル）
- OrderRepository（SQLite 永続化、スキーマ自動作成用 init_orders_db）
- Broker クライアントファクトリ（Mock / 実クライアント切替）
- MockBrokerClient（テスト用。fill_mode: instant/partial/never/reject）
- Reconciler（起動時に OrderSent をブローカと照合し復旧）
- RiskManager（Gate1/2/3 実装）
- 監視プロセス（run_monitoring。ポーリング間隔は MONITOR_POLL_INTERVAL）
- Data モジュール：マーケットカレンダー、RSS ニュース収集等

## セットアップ手順（開発向け）
1. Python と仮想環境の作成（推奨）
   - Python 3.9+（コードは型ヒントや pathlib を使用）
   - 仮想環境を作成してアクティベートしてください。

2. 依存パッケージのインストール
   - requirements.txt がある場合:  
     pip install -r requirements.txt
   - 最低限の主要依存（例）:
     pip install duckdb httpx websocket-client PyYAML defusedxml

   ※ validate_config の YAML 検証には PyYAML が必要です。ニュース収集には defusedxml を利用します。

3. プロジェクトルートで .env を用意
   - 対話式ウィザードで作成するのが簡単です（次のセクション参照）。

4. .env の検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けると警告も FAIL 扱いになります。

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

任意 / よく使う設定（デフォルト値や説明）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)、デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス、デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 SQLite DB、デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（PAPER_TRADING モード）
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)、デフォルト: INFO
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（本番では必須に近い）

運用関連:
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）
- PID_FILE_PATH — PID ファイルパス（デフォルト data/execution.pid）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

Settings クラスが環境変数をラップしており、厳密な検証は Settings のプロパティで行われます。

## .env 作成（対話式ウィザード）
対話式で .env を作成または更新できます。

実行:
python -m kabusys.config_setup

- 既存 .env があれば読み込んで Enter で現値を再利用できます。
- シークレット項目（トークン・パスワード）はマスク表示されます。
- ウィザード完了後に .env を保存するか確認されます。

ウィザード後は設定検証を行ってください:
python -m kabusys.validate_config
（--strict オプションで警告をエラー扱いにできます）

## 使い方（実行例）
- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 環境設定ウィザード:
  python -m kabusys.config_setup

- 実行エンジン（Execution）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading または development の場合、MockBrokerClient が使われます。
  - paper_trading の場合は別 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 停止は data/stop_requested.flag の作成で行います（ランタイムはこのフラグを監視）。

- 監視プロセス:
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60）。

- 開発／テスト用に直接モジュールを import して単体テストすることも可能（MockBrokerClient、OrderRecord の状態遷移等）。

## 実行時のファイル/フラグ
- data/stop_requested.flag — 監視・実行ループの停止フラグ（存在で停止）
- data/execution.pid — ExecutionEngine が書き出す PID ファイル
- data/kill.flag — kill_switch 用フラグ（存在で起動拒否 unless KILL_FLAG_CLEAR_ON_START=1）
- DB:
  - DuckDB: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLite: SQLITE_PATH（監視、デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用）

## ディレクトリ構成
（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py                  — 環境変数読み込み・Settings
    config_setup.py            — .env 対話式ウィザード
    validate_config.py         — 起動前設定チェック CLI
    run_execution.py           — ExecutionEngine 起動スクリプト
    run_monitoring.py          — Monitoring 起動スクリプト
    execution/
      __init__.py
      broker_api.py           — Broker API 型定義・例外・ファクトリ
      broker_factory.py       — Settings に応じたクライアント生成
      kabu_client.py          — kabuステーション実装（httpx + websocket）
      mock_client.py          — テスト用モック実装
      order_record.py         — 注文状態モデル・遷移ロジック
      order_repository.py     — SQLite 永続化（init_orders_db を含む）
      order_manager.py        — 発注フロー（作成・送信・同期・キャンセル）
      execution_engine.py     — ExecutionEngine（シグナル処理／push ドレイン）
      reconciler.py           — 起動時リコンシリエーション
      risk_manager.py         — Gate1/2/3 リスク管理
      ...（他関連モジュール）
    monitoring/
      monitoring_db.py        — 監視 DB 初期化/ログ用 API
      system_monitor.py       — システムメトリクス収集
    data/
      calendar_management.py  — マーケットカレンダー管理（DuckDB）
      news_collector.py       — RSS ニュース収集
      jquants_client.py       — J-Quants API ラッパー（データ取得）
    utils/
      logging_setup.py        — ロギング初期化
      process_priority.py     — プロセス優先度操作ユーティリティ
config/
  system_config.yaml
  data_config.yaml
  strategy_config.yaml
  risk_config.yaml
  execution_config.yaml
  monitoring_config.yaml

プロジェクトルート:
  .env (生成推奨、絶対に Git に含めない)
  data/ (DB・pid・フラグなどを格納)
  README.md

## 開発時のポイント / 注意事項
- 本番（KABUSYS_ENV=live）を使う場合は設定を慎重に確認してください（validate_config は live での警告を出します）。
- .env は絶対にソース管理にコミットしないでください。
- MockBrokerClient の fill_mode によりテストシナリオを容易に再現できます:
  - instant: 即時全量約定
  - partial: 部分約定（fill_order で手動で全量にすることが可能）
  - never: 注文番号発行するが約定しない（pending 再現）
  - reject: 発注拒否を再現
- ExecutionEngine は PID ファイルを書き、stop フラグや kill.flag を監視します。運用監視時はこれらのフラグの扱いに注意してください。
- Reconciler は起動直後に OrderSent の状態を broker に照合して同期します。これによりクラッシュ復旧を試みます。

## よく使うコマンドまとめ
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring

---

問題報告や改善提案は Issue に記載してください。README の内容や起動方法で不明点があれば教えてください。