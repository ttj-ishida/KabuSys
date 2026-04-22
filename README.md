KabuSys
======

バージョン: 0.1.0

概要
----
KabuSys は日本株自動売買システムのコアライブラリおよび起動スクリプト群です。  
本コードベースは以下の主要機能を提供します。

- 環境設定管理（.env 読み込み・ウィザード・検証）
- 発注エンジン（ExecutionEngine）：シグナルの読み込み→ブローカー発注→約定同期
- ブローカー抽象化（実運用向け KabuStationClient / テスト向け MockBrokerClient）
- 注文永続化（SQLite）と状態マシン（OrderRecord）
- リコンシリエーション（クラッシュ後の自動復旧）
- リスク管理（Gate1/2/3：重複・余力・レート制限・サーキットブレーカー・ドローダウン）
- 監視プロセス（SystemMonitor ポーリング）
- データユーティリティ（市場カレンダー管理、ニュース収集 等）
- 実行時の安全機構（kill flag / PID ファイル / サーキットブレーカー）

主な特徴
-------
- 環境ごとに挙動を切り替え（development / paper_trading / live）
- paper_trading / development モードでは MockBrokerClient により外部環境無しでテスト可能
- 発注・同期・キャンセルのクラッシュ耐性設計（OrderSent の扱い、二相コミット的保存）
- 起動時のリコンシリエーション機能により残留・不整合を自動検出・修復
- DuckDB（分析）＋SQLite（監視/永続）を併用するデータアーキテクチャ
- 安全対策：PID ファイル、kill.flag、KILL_FLAG_CLEAR_ON_START オプション

セットアップ手順
--------------
1. Python（推奨 3.10+）を用意します。

2. 必要な依存パッケージをインストールします（例: pip）:
   - 基本: httpx, websocket-client, duckdb, defusedxml, sqlite3 は標準
   - YAML の検証を有効にする場合: PyYAML
   - 例:
     pip install httpx websocket-client duckdb defusedxml PyYAML

   validate_config の YAML 検証は PyYAML の有無により動作が変わります（未インストールなら内容検証はスキップされます）。

3. リポジトリルートに data ディレクトリを作成しておくと便利です（デフォルト DB/フラグファイル保存先）:
   mkdir -p data

4. .env の作成:
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example 等を参照）。.env は Git にコミットしないでください。

5. 設定検証:
   - 基本検証:
     python -m kabusys.validate_config
   - 警告も失敗扱いにする（CI など）:
     python -m kabusys.validate_config --strict

使い方
------
- 環境設定ウィザード（.env 作成 / 更新）
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  --strict を付けると警告も exit(1) になります

- 実行エンジン起動（本番 / ペーパートレード）
  python -m kabusys.run_execution
  (設定により KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用します)

- 監視プロセス起動（SystemMonitor ポーリング）
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）

主要な環境変数
----------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意（デフォルトあり / 空可）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite ファイルパス（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル: DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabuステーション ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知トークン（任意）
- LINE_USER_ID — LINE 通知先ユーザーID（任意）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（0/1、デフォルト 0）
- PAPER_FILL_MODE — paper_trading 時の挙動: instant / partial / never / reject
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）

注意:
- 自動で .env をプロジェクトルートから読み込みます（OS 環境変数 > .env.local > .env）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env は絶対にリポジトリにコミットしないでください。

ディレクトリ構成（主なファイル）
-------------------------------
以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- __init__.py
  - パッケージ定義 / バージョン

- config.py
  - .env 読み込みロジック、Settings クラス（環境変数ラッパ）

- config_setup.py
  - 対話式ウィザードで .env を作成・更新

- validate_config.py
  - 起動前チェック CLI（必須環境変数、config/*.yaml の存在/パース、パス確認 等）

- run_execution.py
  - ExecutionEngine を起動するエントリポイント。kill.flag / PID ファイル管理、DB 接続の初期化

- run_monitoring.py
  - SystemMonitor をポーリングで定期実行するエントリポイント

- execution/
  - broker_api.py — BrokerAPIProtocol、データモデル、例外、ファクトリ
  - kabu_client.py — kabuステーション REST API 実装（httpx、WebSocket）
  - mock_client.py — テスト用 MockBrokerClient（fill_mode により挙動変更）
  - broker_factory.py — Settings に応じたブローカークライアント生成
  - order_record.py — 注文状態（OrderState）と OrderRecord（状態遷移ロジック）
  - order_repository.py — SQLite による永続化層（orders テーブル初期化含む）
  - order_manager.py — 外向き API（作成・送信・同期・キャンセル）
  - execution_engine.py — シグナル処理ループ、WebSocket ドレイン、kill_switch 実装
  - reconciler.py — 起動時のリコンシリエーション（OrderSent の突合、ポジション差分）
  - risk_manager.py — Gate1/2/3 リスクガード（レート制限・CB・ドローダウン 等）

- data/
  - calendar_management.py — JPX カレンダー管理、営業日判定、calendar_update_job
  - news_collector.py — RSS 収集・前処理・DB 保存ロジック（セキュリティ対策あり）
  - （jquants_client 等、外部 API クライアントが想定される）

- monitoring/
  - monitoring_db.py, system_monitor.py（監視DBや監視ロジック。実行時に sqlite を使用）

- utils/
  - logging_setup.py — ログ設定
  - process_priority.py — プロセス優先度設定

運用上のポイント / 安全対策
--------------------------
- KABUSYS_ENV=live 設定は本番挙動です。validate_config で live 時の警告が出ます。LINE 通知や kill flag 設定を必ず確認してください。
- kill.flag（デフォルト data/kill.flag）により起動中のプロセス停止や起動拒否が可能です。KILL_FLAG_CLEAR_ON_START=1 を本番で使うと危険です（自動クリアされ再起動してしまうため）。
- ExecutionEngine はリコンシリエーション機能を持ち、OrderSent の不整合を自動的に突合して回復します。
- paper_trading モードでは本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使用することを推奨します。

トラブルシューティング
---------------------
- PyYAML がないと validate_config の YAML 内容検証はスキップされます（警告）。YAML 検証を有効にするには PyYAML をインストールしてください。
- .env が読み込まれない場合はプロジェクトルート（.git または pyproject.toml を含むディレクトリ）で実行しているか確認してください。自動読み込みを無効にしている場合（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）も確認してください。
- data ディレクトリや親ディレクトリのパーミッションにより DB ファイルが作成できない場合があります。必要に応じて事前に作成してください。
- run_execution/run_monitoring 実行時は必ず validate_config を通すことを推奨します。

開発メモ
-------
- ブローカー実装はモジュール化されており、create_broker_api の mock フラグを切り替えることで KabuStationClient / MockBrokerClient を利用できます。
- リスク管理やリコンシリエーションのロジックはユニットテストを容易に書けるよう依存注入設計になっています（Settings / BrokerAPIProtocol / OrderRepository 等）。

ライセンス / 注意
----------------
- .env 等のシークレットファイルは絶対に Git 等のバージョン管理にコミットしないでください。
- 本リポジトリのコードはサンプル実装を含みます。実運用で利用する場合は必ず十分な検証と安全性確認（法令・証券会社ルール準拠）を行ってください。

問い合わせ／コントリビュート
---------------------------
- コントリビュートやバグ報告はリポジトリの issue や PR を通じて行ってください。README を拡張する提案も歓迎します。

以上です。README に追加してほしい例（.env の具体例や起動ログ例、CI 用手順など）があれば教えてください。