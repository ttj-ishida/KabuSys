README
======

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買フレームワークです。  
主にシグナルに基づく発注（ExecutionEngine）、ブローカー API 抽象化、監視（SystemMonitor）、
カレンダー管理やニュース収集などのデータ機能を備えています。  
設計上、環境ごとに実運用（live）／ペーパートレード（paper_trading）／開発（development）
を切り替え可能で、テスト用に Mock ブローカーを用いた分離された DB 処理もサポートします。

主な特徴
--------
- 環境ごとの設定管理（.env、自動読み込み）
- .env 作成ウィザード（対話式）
- 起動前設定検証ツール（validate_config）
- ExecutionEngine：シグナルの読み取り → リスクゲート → 発注フロー
- Reconciler：クラッシュ後の注文・ポジション照合（リコンシリエーション）
- RiskManager：Gate1/2/3 による多層リスクガード（重複、余力、レート制限、CB、ドローダウン）
- ブローカー抽象（BrokerAPIProtocol）と MockBrokerClient による検証容易性
- 監視ループ（run_monitoring）: 指定インターバルでメトリクス記録
- データ機能：マーケットカレンダー管理、RSS ニュース収集等
- DuckDB / SQLite を用いた永続化（デフォルトのファイルパスは data/ 以下）

動作要件（想定）
----------------
- Python 3.10 以上（型アノテーションの構文などから）
- 推奨パッケージ（主な依存）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml（設定ファイル YAML 検証用、未インストールでも動作可能だが警告が出ます）
  - defusedxml
  - その他標準ライブラリ外のパッケージ（requests 等が別途必要な場合あり）

セットアップ手順
----------------
1. リポジトリをクローン:
   - git clone <repo-url>

2. Python 仮想環境の作成（例）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール:
   - pip install duckdb httpx websocket-client pyyaml defusedxml
   - （requirements.txt がある場合は pip install -r requirements.txt）

4. .env の初期作成:
   - 対話式ウィザードで .env を生成するのが簡単です:
     - python -m kabusys.config_setup
     - 途中で止めたくなったら Ctrl+C（中断時は変更は保存されません）

5. 設定の検証:
   - python -m kabusys.validate_config
   - すべて問題なければ [OK] が表示されます。警告もエラー扱いにしたい場合は --strict を付けます:
     - python -m kabusys.validate_config --strict

6. DB 初期化（必要に応じて、実行スクリプト内で自動的に行われる箇所があります。）
   - 監視用 SQLite / DuckDB の親ディレクトリ data/ を作成しておくとよい:
     - mkdir -p data

基本的な使い方
--------------
- .env の作成・更新:
  - python -m kabusys.config_setup
  - 生成される .env の内容は Git 管理対象にしないこと（README にも記載）

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い（exit 1）

- 実行エンジン起動（発注処理）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading / development の場合、MockBrokerClient が使われます（実売買は行われません）。
  - KABUSYS_ENV=live は将来の実装（現状は NotImplementedError が投げられる箇所あり）。

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）。

停止・制御
----------
- 停止フラグ:
  - プロジェクトルートの data/stop_requested.flag の作成で、起動中のループは検知して安全に終了します。
- Kill Switch:
  - settings.kill_flag_path（デフォルト data/kill.flag）を用いて外部から kill スイッチを発動できます。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると既存の kill.flag は自動クリアされます（注意）。

主な環境変数
--------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション（またはブローカー）の API パスワード（必須）

任意 / 推奨（デフォルトがあるもの等）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite ファイルパス（監視用、デフォルト data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート通知設定（任意）
- PAPER_FILL_MODE — paper_trading 用の fill モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

サンプル .env（config_setup により生成される形式）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

ディレクトリ構成（主要ファイル）
------------------------------
以下はプロジェクト内の主なモジュールと役割の抜粋です（src/kabusys 以下を想定）。

- src/kabusys/
  - __init__.py
    - パッケージ定義（__version__ など）
  - config.py
    - .env 自動読み込み、Settings クラス（環境変数アクセスラッパー）
  - config_setup.py
    - .env を対話式に作成・更新するウィザード
  - validate_config.py
    - 起動前の設定検証 CLI（必須環境変数、config/*.yaml の存在/パース確認 等）
  - run_execution.py
    - ExecutionEngine の起動スクリプト（発注エンジン）
  - run_monitoring.py
    - SystemMonitor の起動スクリプト（監視ポーリングループ）
  - execution/
    - broker_api.py — ブローカー API の Protocol、データモデル、例外、ファクトリ
    - kabu_client.py — kabuステーション向け実装（HTTP + WebSocket）
    - mock_client.py — テスト用 MockBrokerClient（fill_mode 等で挙動を切替）
    - broker_factory.py — Settings に基づいてブローカークライアントを生成
    - order_record.py — Order の状態遷移モデル（純粋なビジネスロジック）
    - order_repository.py — SQLite を用いた永続化層（orders テーブル）
    - order_manager.py — 発注フロー（DB と broker を繋ぐ外向き API）
    - execution_engine.py — 発注セッションの主ループ（シグナル処理 + push ドレイン）
    - reconciler.py — 再起動時のリコンシリエーション（OrderSent の同期等）
    - risk_manager.py — Gate1/2/3 によるリスク管理
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB を利用）
    - news_collector.py — RSS ニュース収集・前処理（defusedxml、SSRF 対策等）
    - jquants_client.py — （参照あり、J-Quants API 連携用）
  - monitoring/
    - monitoring_db.py — 監視 DB 初期化 / ログ関係
    - system_monitor.py — システムメトリクス取得ロジック
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度操作ユーティリティ
  - config/
    - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
      - 各種設定ファイル（存在が期待される。validate_config が存在確認・YAML パース検証を行う）

開発メモ / 運用上の注意
---------------------
- KABUSYS_ENV によって DB の使い分けやブローカーの実装が変わります。paper_trading では paper_trading 用 SQLite を使用して本番 DB と分離します。
- validate_config は PyYAML が未インストールだと YAML の中身検証をスキップします（警告）。
- run_execution / run_monitoring は起動時に PID ファイルを書き込み、停止時に削除します。PID ファイルや kill.flag のパスは Settings から変更可能です。
- Live ブローカークライアント実装（KabuStationClient を本番で使う際）は API のベース URL とパスワード等を正しく設定してください。現状の BrokerClientFactory は live を未実装（NotImplementedError）としている箇所がありますので注意してください。
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも注記あり）。

よく使うコマンドまとめ
--------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring

補足
----
- config/*.yaml のテンプレートを生成するスクリプト（python scripts/generate_config.py）の呼び出しが README 内のコードで言及されています。リポジトリに存在する場合はそちらで初期ファイルを生成してください。
- 実際に証券会社 API（kabuステーション）を叩く場合は、テストネットや paper_trading で十分に検証してから live に移行してください。

以上です。運用・導入の際に必要な追加情報（例: 実際の依存関係一覧、CI / デプロイ手順、さらに詳しい設定項目の説明など）があれば補足して README を拡張します。