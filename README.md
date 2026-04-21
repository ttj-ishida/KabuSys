KabuSys — 日本株自動売買システム
=================

概要
----
KabuSys は日本株の自動売買を目的とした小規模なフレームワークです。  
主な目的は以下のとおりです。

- シグナルに基づく発注（ExecutionEngine）
- 発注状態管理（OrderRecord / OrderRepository / OrderManager）
- リスクガード（3段階の RiskManager）
- 再起動時の自動復旧（Reconciler）
- モニタリング（SystemMonitor 用ループ）
- データ収集（マーケットカレンダー、ニュース収集）
- kabuステーション実装クライアント + テスト用 Mock クライアント

開発・テスト用途では MockBrokerClient を使って実際の証券APIを不要にし、paper_trading 環境で安全に動作検証できます。

主な機能
--------
- 設定ウィザード（.env の対話式生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の存在・整合チェック）: python -m kabusys.validate_config
- ExecutionEngine: シグナル処理、WebSocket push ドレイン、発注フロー
- Order 管理: OrderRecord（状態遷移検証）、OrderRepository（SQLite 永続化）、OrderManager（送信/同期/キャンセル）
- RiskManager: Gate1（シグナル検査）/ Gate2（レート制限・CB）/ Gate3（ドローダウン監視）
- Broker クライアント:
  - KabuStationClient（kabuステーション REST API 実装）
  - MockBrokerClient（テスト用）
- Reconciler: 再起動時の OrderSent 照合・ポジション差分検出
- 監視ループ（run_monitoring）: SystemMonitor のポーリング
- データモジュール: 市場カレンダー更新、RSS ニュース収集（SSRF 対策・XML 脆弱性対策済み）

要件
----
- Python 3.10 以上（`|` 型注釈などの構文を使用）
- 以下の主なパッケージ（プロジェクトに合わせてインストールしてください）:
  - duckdb
  - httpx
  - websocket-client
  - pyyaml (config/*.yaml のパース検証に必要)
  - defusedxml (ニュース収集で利用)
- SQLite は標準ライブラリで使用

セットアップ手順
----------------
1. リポジトリをクローン:
   - git clone <repository-url>
   - cd <repo>

2. 仮想環境を作成して有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）:
   - pip install duckdb httpx websocket-client pyyaml defusedxml

   もし requirements.txt があれば:
   - pip install -r requirements.txt

4. .env を作成:
   - python -m kabusys.config_setup
     - 対話式で .env を生成または更新します。
     - 生成後は必ず .env を Git にコミットしないでください（README 内にも注意書きあり）。

5. 設定を検証:
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備:
   - デフォルトでは data/ ディレクトリに DB ファイル等を置きます。必要に応じて DUCKDB_PATH / SQLITE_PATH を .env で上書きしてください。

使い方
------
基本的な実行例:

- 設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告で終了）: python -m kabusys.validate_config --strict

- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading または development の場合は MockBrokerClient を使用します。live は未実装（実運用での live ブローカークライアントは別実装が必要）。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更したい場合:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring

主な環境変数（重要）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意/上書き可能:
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - KABU_API_BASE_URL (kabuステーション API のベースURL)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID （本番のアラート送信用）
  - KILL_FLAG_CLEAR_ON_START (0/1): 起動時の kill.flag 自動クリア（開発のみ注意）
- 実行例（paper_trading で起動）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

注意点 / 運用メモ
- paper_trading と本番（live）は DB を分離する設計です:
  - paper_trading では paper_trading.db（PAPER_TRADING_SQLITE_PATH）を使用します。
- kill.flag / PID 管理:
  - ExecutionEngine は PID ファイルを書き、settings.kill_flag_path（デフォルト data/kill.flag）を参照します。kill.flag が存在すると通常は起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合は自動クリアする）。
- Reconciler によりクラッシュ後の OrderSent 状態の注文を broker と突合して回復を試みます。
- 実ブローカー利用（live）を行う場合はセキュリティ・テストを十分に行い、LINE 等通知設定を確実に設定してください（validate_config は live 時の注意点を警告します）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/.env 自動読み込みと Settings
  - config_setup.py              — 対話式 .env 作成ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine の起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py              — Broker API のデータモデル・Protocol・ファクトリ
    - kabu_client.py             — kabuステーション REST API 実装
    - mock_client.py             — テスト用 MockBrokerClient
    - broker_factory.py          — Settings に応じたクライアント生成
    - order_record.py            — 注文状態モデルと状態遷移（純粋ロジック）
    - order_repository.py        — SQLite 永続化層
    - order_manager.py           — 外向き注文 API（OrderState Machine 制御）
    - execution_engine.py        — 発注エンジン（シグナル処理 / push ドレイン）
    - reconciler.py              — 起動時のリコンシリエーション
    - risk_manager.py            — Gate1/2/3 のリスクガード
  - monitoring/                   — 監視関連（monitoring_db 等） ※詳細ファイル省略
  - data/
    - calendar_management.py     — 市場カレンダー管理・更新ジョブ
    - news_collector.py          — RSS ニュース収集（SSRF/defusedxml対策あり）
  - utils/                        — ロギング設定、プロセス優先度設定等ユーティリティ（実装参照）

設定ファイル
- config/*.yaml — システム設定（存在チェックと YAML のパース検証を validate_config がサポート）。PyYAML 未インストール時は内容検証をスキップして警告になります。

ライセンスとその他
------------------
- 現行コード内にライセンス表記がない場合はリポジトリのトップレベルでライセンスを明示してください。
- .env に機密情報（API トークン等）を保存する際は必ず .gitignore に登録し、リポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。

よくある質問（FAQ）
------------------
Q. 本番（live）環境でそのまま動かせますか？  
A. KabuStationClient の基礎実装はありますが、live 用の完全な運用確認（安全性・通知・実運用テスト）は必須です。BrokerClientFactory は現状 paper_trading / development を優先する設計です。

Q. テストはどうすれば良いですか？  
A. MockBrokerClient を使えば発注・約定フローやリコンシリエーションのユニット/統合テストが行えます。設定読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化にも対応しています。

フィードバック / 貢献
------------------
バグ報告や改善提案は Issue を立ててください。プルリクエスト歓迎です。変更を加える際はテストと静的解析（type check / linters）の実行を推奨します。

以上。README に不足している点や追記して欲しい章（例: サンプル .env のテンプレート、実行フロー図、テスト手順など）があれば教えてください。