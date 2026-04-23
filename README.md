# KabuSys

日本株自動売買システム（簡易版） — 設定管理・実行・監視の基盤コンポーネント群を含むリポジトリの README。

この README はプロジェクト内の主要な CLI／モジュールの使い方、セットアップ手順、ディレクトリ構成を説明します。

---

## 概要

KabuSys は日本株向けの自動売買システムを構成する基盤ライブラリです。  
主に以下の役割を担います。

- 環境変数／YAML 設定の対話的生成および検証（.env ウィザード / バリデータ）
- ExecutionEngine によるシグナル駆動の発注処理（本番／ペーパートレード対応）
- Broker クライアント（kabu station 実装 ＆ Mock 実装）
- 注文管理（状態遷移、永続化、再同期／Reconciliation）
- 監視プロセス（SystemMonitor）および監視 DB へのログ記録
- データ処理ユーティリティ（マーケットカレンダー、ニュース収集など）

このリポジトリは、実際の証券会社 API（kabu station）を用いることを想定しつつ、テスト・開発用に Mock クライアントを備えています。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
  - .env を対話的に作成・更新
- 設定検証 CLI（python -m kabusys.validate_config）
  - .env および config/*.yaml の存在や整合性を起動前にチェック
  - --strict オプションで警告も失敗扱いに
- 実行エンジン（python -m kabusys.run_execution）
  - シグナル読込み → Gate1/Gate2 → 発注 → Push ドレインループまでのセッション実行
  - paper_trading 環境では MockBrokerClient を利用し本番 DB と分離
- 監視ループ（python -m kabusys.run_monitoring）
  - SystemMonitor のポーリングループ、MONITOR_POLL_INTERVAL により間隔変更可能
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
  - 状態遷移の検証、SQLite による永続化、Uncertain レコード検出
- リスク管理（RiskManager）
  - Gate1（シグナルレベル） / Gate2（レート制限・CB） / Gate3（ドローダウン監視）
- ブローカークライアントファクトリ（BrokerClientFactory）
  - 環境に応じたクライアント生成（Mock / 将来 Live）

---

## 前提・必須事項

- Python 3.10 以上（型アノテーションの構文 Path | None などを使用）
- 主要依存パッケージ（例）:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config/*.yaml のパース検証を行う場合）
- SQLite は標準ライブラリで利用
- kabuステーション（実機接続）を使う場合は kabu station アプリが PC 上で稼働している必要あり

（requirements.txt はリポジトリに含めることを推奨します。上記は代表的なパッケージの一覧です）

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate

2. パッケージをインストール
   - pip install duckdb httpx websocket-client defusedxml PyYAML

3. プロジェクトルートの確認
   - リポジトリルート（.git / pyproject.toml がある場所）からコマンドを実行してください。
   - config/*.yaml は必要に応じて生成・編集します（validate_config は PyYAML を利用してパース検証を行います）。

4. .env の作成（推奨: ウィザードを利用）
   - python -m kabusys.config_setup
     - 対話形式で .env を生成します（デフォルト: プロジェクトルート/.env）
   - 直接作成する場合の最小例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```

5. 設定検証
   - python -m kabusys.validate_config
   - すべて OK なら exit code 0。--strict を付けると警告も失敗（exit 1）扱いになります。

6. データディレクトリの準備（自動生成されることもありますが事前作成推奨）
   - mkdir -p data

---

## 使い方（主要 CLI）

- 環境設定ウィザード（.env の生成・更新）
  - python -m kabusys.config_setup --env-file path/to/.env

- 設定検証
  - python -m kabusys.validate_config
  - 警告を FAIL 扱いにする: python -m kabusys.validate_config --strict
  - この CLI は .env と config/*.yaml の存在や一部の値（KABUSYS_ENV, LOG_LEVEL, DB パス等）を検査します。
  - PyYAML 未インストール時は YAML 内容検証をスキップし、警告が出ます。

- 実行エンジン（セッション実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV により挙動が変わります:
    - development / paper_trading: MockBrokerClient を使用（paper は専用 SQLite を使用）
    - live: 本番ブローカークライアント（現状未実装で NotImplementedError を返す箇所あり）
  - stop 制御:
    - 起動中にプロセスを停止させたい場合、プロジェクトの data/stop_requested.flag を作成するとループが検出して終了します。
    - kill スイッチ（危急停止）フラグ: data/kill.flag（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動クリアされます）

- 監視プロセス（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - 監視は常に sqlite_path（監視用 DB）を使用（環境にかかわらず）

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）

- 任意 / 推奨
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1, デフォルト 0）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）

- 自動読み込み
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動的に読み込みます。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。

---

## 実装と内部コンポーネント（簡易説明）

- config.py / Settings
  - 環境変数の読み込みと Settings オブジェクトを提供（settings.jquants_refresh_token 等）
  - .env の自動ロード機能（プロジェクトルートを探索）

- config_setup.py
  - .env を対話式に作成・更新するウィザード

- validate_config.py
  - 起動前チェック（必須 env, KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルのパースチェック）

- execution/
  - broker_api.py — BrokerAPIProtocol（型）・データモデル・例外・create_broker_api()
  - kabu_client.py — kabu station REST API 実装（httpx）
  - mock_client.py — MockBrokerClient（テスト用）
  - broker_factory.py — Settings に応じてクライアントを生成
  - order_record.py — 注文状態モデルと遷移ロジック（DB 非依存）
  - order_repository.py — SQLite による永続化（orders テーブルの初期化含む）
  - order_manager.py — OrderRecord と Repository をつなぐ外向け API（create/send/sync/cancel）
  - execution_engine.py — セッションのワークフロー（シグナル処理・WebSocket push ドレイン）
  - reconciler.py — 再起動時のリコンシリエーション（OrderSent の突合せ、ポジション照合）
  - risk_manager.py — Gate1/2/3 のリスク判定

- data/
  - calendar_management.py — マーケットカレンダー管理（J-Quants 連携想定）
  - news_collector.py — RSS ニュース収集（セキュアな XML パース / URL 正規化等）

- monitoring/
  - monitoring_db, system_monitor など（監視 DB 初期化 / ポーリングロジック。run_monitoring から使用）

- utils/
  - logging_setup.py, process_priority.py などの補助ユーティリティ（ログ設定・プロセス優先度制御）

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル・ディレクトリ（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - execution/
      - __init__.py
      - broker_api.py
      - broker_factory.py
      - kabu_client.py
      - mock_client.py
      - order_record.py
      - order_repository.py
      - order_manager.py
      - execution_engine.py
      - reconciler.py
      - risk_manager.py
      - ...
    - data/
      - calendar_management.py
      - news_collector.py
      - jquants_client.py (参照先)
      - ...
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - ...
    - utils/
      - logging_setup.py
      - process_priority.py
      - ...

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- .env, .env.local (プロジェクトルートに配置)

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定・権限を慎重に管理してください。validate_config は live の場合に追加警告を出します（LINE 設定未設定など）。
- kill.flag（KILL_FLAG_PATH）を使った安全停止の運用設計があります。KILL_FLAG_CLEAR_ON_START=1 を本番で使用すると危険な場合があるためデフォルトは 0 を推奨します。
- SQLite / DuckDB のパスはデフォルトで data/ に置かれます。バックアップやパスの管理に注意してください。
- Reconciler（起動時の突合せ）は OrderSent の不確定状態に対して自動復旧を試みますが、手動確認が必要なケース（broker 側に注文が存在しない等）もあります。

---

## 開発者向けメモ

- 設定は Settings クラス（kabusys.config.settings）を通して取得してください。
- Broker の実装は Protocol（BrokerAPIProtocol）に従うため、Mock を差し替えて単体テストが可能です。
- OrderRecord は DB を直接操作せず、ビジネスロジックと状態遷移を分離しています。

---

この README はコードベースの主要な箇所をまとめたものです。詳細な API 使用方法や追加の設定ファイル（config/*.yaml）のスキーマについては該当ファイルやドキュメント（別途用意されている場合）を参照してください。問題や改善提案があれば Issue を立ててください。