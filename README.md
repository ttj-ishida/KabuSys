# KabuSys

日本株自動売買システム（プロトタイプ）

このリポジトリは、kabuステーション / J‑Quants 等を利用した自動売買システムのコア部分を切り出したものです。Execution（発注エンジン）、Monitoring（監視）、Data（ニュース収集/カレンダー管理）などのコンポーネントを備え、ローカル開発向けに Mock ブローカーを使ったペーパートレードが可能です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方
- 環境変数一覧（主要）
- ディレクトリ構成
- 補足・トラブルシューティング

---

プロジェクト概要
- シグナルに基づく発注（ExecutionEngine）
- 発注の状態管理／永続化（SQLite）
- リスクガード（3段階: Gate1/Gate2/Gate3）
- 起動時リコンシリエーション（Reconciler）
- kabuステーション実装（KabuStationClient）とテスト用 Mock（MockBrokerClient）
- 監視プロセス（SystemMonitor をポーリングする run_monitoring）
- 環境設定ウィザード（.env 生成）と事前検証ツール（validate_config）
- DuckDB を使ったデータ（シグナル / ポートフォリオ / カレンダー / ニュース）処理

主な機能
- .env ウィザード（config_setup）による対話的な初期設定作成
- 設定検証 CLI（validate_config）で起動前に環境不備を検出
- ExecutionEngine：シグナルプル型発注 + WebSocket push のドレイン処理
- OrderState マシン / OrderRepository（SQLite）による堅牢な注文管理
- Reconciler によるクラッシュ復旧とブローカー照合
- RiskManager によるレート制限・サーキットブレーカー・ドローダウン監視
- MockBrokerClient によるペーパートレード/ローカルテスト
- Data モジュール（カレンダー管理・ニュース収集）によるデータ基盤処理

セットアップ手順（開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - 以下は本プロジェクトで使用されている主要パッケージの例です（requirements.txt が無ければ手動で）。
     - pip install duckdb httpx websocket-client defusedxml pyyaml
   - 注: PyYAML が無い場合、validate_config は YAML 内容検証をスキップします（存在チェックのみ）。
4. データディレクトリ作成
   - mkdir -p data
   - run_monitoring/run_execution 実行時に自動作成されますが、手動で用意しておくと安全です。
5. .env ファイルを作成
   - 対話型ウィザードを利用する:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - python -m kabusys.validate_config --strict  （警告も失敗扱い）

使い方（主な CLI / スクリプト）
- 環境設定ウィザード（.env 生成 / 更新）
  - python -m kabusys.config_setup
  - オプション: --env-file で .env の保存先を指定可能
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit(1) 扱いで終了
- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV が paper_trading / development の場合は MockBrokerClient を使用
  - 起動前に .env を作成・検証してください
- 監視プロセス
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を設定可能（デフォルト 60 秒）

主要な環境変数（要件）
- 必須
  - JQUANTS_REFRESH_TOKEN — J‑Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード
- 推奨 / 任意
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
  - LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
  - KABU_API_BASE_URL — kabu API ベース URL（例: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
  - PAPER_FILL_MODE — paper_trading 用の fill モード（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill フラグを自動クリアするか（0|1。デフォルト 0。本番は 0 推奨）
- 自動読み込み
  - .env はプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みされます
  - OS 環境変数 > .env.local > .env の順で優先
  - 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

データベースとファイル
- DuckDB（分析用）: デフォルト data/kabusys.duckdb
- SQLite（監視/注文履歴）: data/monitoring.db（paper_trading 時は data/paper_trading.db に分離可能）
- PID / フラグ
  - pid: data/execution.pid（PID 書き込み）
  - stop フラグ: data/stop_requested.flag（存在でループ停止）
  - kill フラグ: data/kill.flag（存在で起動拒否 unless KILL_FLAG_CLEAR_ON_START=1）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込みと Settings クラス（アプリケーション設定）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — Execution エントリポイント
  - run_monitoring.py        — Monitoring エントリポイント
  - execution/
    - __init__.py
    - broker_api.py          — ブローカー API の Protocol / データモデル / 例外 / ファクトリ
    - kabu_client.py         — KabuStationClient（httpx/websocket 実装）
    - mock_client.py         — MockBrokerClient（テスト用）
    - broker_factory.py      — Settings に応じたクライアント生成
    - order_record.py        — OrderState マシンと OrderRecord（純粋ロジック）
    - order_repository.py    — SQLite 永続化層（orders テーブル）
    - order_manager.py       — 外向き注文 API（create/send/sync/cancel）
    - execution_engine.py    — ExecutionEngine（シグナル処理 + push ドレイン）
    - reconciler.py          — 起動時リコンシリエーション
    - risk_manager.py        — 3 段階リスクガード実装
    - ...（その他 execution 関連コンポーネント）
  - monitoring/
    - monitoring_db.py       — 監視 DB 初期化・ロギング関数
    - system_monitor.py      — システム監視ロジック（使用される）
  - data/
    - calendar_management.py — マーケットカレンダー管理（J‑Quants 連携）
    - news_collector.py      — RSS ベースのニュース収集
    - jquants_client.py      — J‑Quants API ラッパ（参照あり）
  - utils/
    - logging_setup.py       — ロギング初期化
    - process_priority.py    — プロセス優先度設定（プラットフォーム依存処理）
  - config/*.yaml            — 設定用 YAML（system_config.yaml 等。存在チェックあり）

補足・注意事項 / トラブルシューティング
- validate_config:
  - PyYAML がインストールされていないと YAML の内容検証はスキップされ、ファイルの存在チェックのみ行われます（警告表示）。
  - --strict を指定すると警告もエラー扱いになります。
- .env の自動ロード:
  - OS 環境変数が優先されます。CI 等でローカル .env を無視したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番環境:
  - KABUSYS_ENV=live を設定すると警告が多く出ます。LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値（0 推奨）などを特に確認してください。
- MockBrokerClient:
  - paper_trading / development では Mock が使われ、PAPER_FILL_MODE によって挙動（instant/partial/never/reject）を切り替えられます。テスト時の挙動確認に便利です。
- セキュリティ:
  - .env は絶対に Git にコミットしないでください（config_setup の冒頭にも注意書きがあります）。
- 依存パッケージ:
  - 実行に必要な外部ライブラリは環境によって異なります（duckdb, httpx, websocket-client, defusedxml, pyyaml など）。用途に応じてインストールしてください。

最後に
- まずは python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config で検証することを推奨します。
- ペーパートレード（安全なローカル動作確認）には KABUSYS_ENV=paper_trading を使用してください。

もし README に追加してほしい内容（例: より詳細なデプロイ手順、CI 設定例、各モジュールの API リファレンスなど）があれば教えてください。必要に応じて追記します。