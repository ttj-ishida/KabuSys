KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買 / 研究 / 監視ツール群（KabuSys）です。  
以下はコードベースの概要、セットアップ方法、実行方法、主要コンポーネントの説明です。

プロジェクト概要
---------------
KabuSys は以下を目的としたモジュール群を含む小規模な自動売買フレームワークです。

- 注文実行（ExecutionEngine）とリスク管理
- 監視（System / Trade / Risk）と Kill Switch（フラグファイルによる安全停止）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- リサーチ（ファクター計算、特徴量探索、将来リターン・IC 計算）
- AI 経由のニュース NLP（OpenAI を用いた銘柄別センチメント算出）
- Paper Trading 用の検証レポート出力ツール
- .env ウィザード / 設定検証 CLI

主な設計方針：
- DuckDB（分析用） + SQLite（監視・発注履歴等）を使用
- Paper trading は本番 DB と分離（専用 SQLite）
- 外部 API（OpenAI 等）は環境変数でキーを指定し安全に呼び出す
- ルックアヘッドバイアスを避ける設計（target_date を明示渡し、date.today() を直接参照しない等）

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
  - PID ファイル管理、停止フラグ検出
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor（プロセス・CPU/メモリ/DISK・データ鮮度）
  - TradeMonitor（滞留注文・約定異常）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（条件により data/kill.flag を書いて Execution を停止）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- 環境設定ウィザード（config_setup.py）: 対話式に .env を生成・更新
- 設定検証 CLI（validate_config.py）: .env や config/*.yaml の妥当性チェック
- Paper Trading 検証レポート（tools/paper_verification_report.py）
- ポートフォリオ構築ユーティリティ（portfolio/*）
- リサーチ（research/*）：ファクター計算、IC、統計要約
- AI: news_nlp（銘柄別センチメント → ai_scores へ書き込み）、regime_detector（市場レジーム判定）
- ユーティリティ: process_priority（プロセス優先度 / CPU affinity 設定）

前提条件（推奨）
---------------
- Python 3.10+
- 必要なパッケージ（少なくとも）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の検証を行う場合に必要）
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワーク接続（OpenAI / kabuステーション / J-Quants 等を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトで requirements.txt があれば pip install -r requirements.txt）

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは手動でプロジェクトルートに .env を作成

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
--------------------
必須:
- JQUANTS_REFRESH_TOKEN  — J-Quants API トークン
- KABU_API_PASSWORD      — kabuステーション API パスワード

主要（任意含む）:
- KABUSYS_ENV            — 実行環境: development / paper_trading / live （デフォルト development）
- DUCKDB_PATH            — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading モード時）
- OPENAI_API_KEY         — OpenAI API キー（ai モジュール利用時）
- PAPER_FILL_MODE        — Paper Trading 時の約定モード（instant|partial|never|reject）
- LOG_LEVEL              — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

.env の自動ロード:
- プロジェクトルートに .env / .env.local がある場合、自動で読み込まれます（OS 環境変数を上書きしない挙動）。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要コマンド）
----------------------

1) 環境ウィザード（.env の作成）
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになる

3) 実行エンジン起動（Execution）
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBroker を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
     - PID ファイル: data/execution.pid（Settings.pid_file_path）
     - 起動時に data/stop_requested.flag が存在する場合は起動せず終了
     - 実行中に data/stop_requested.flag が作成されるとエンジンに停止命令を送る

4) 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を変更可能（デフォルト 60）
   - 監視は常に本番用の sqlite_path を使用（環境にかかわらず監視 DBは production path）
   - 監視中に条件を満たすと data/kill.flag を書き、ExecutionEngine の停止を促す

5) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数で指定することも可）

主要ファイル・動作の補足
- Kill / Stop フラグ:
  - stop_requested.flag: run_execution/run_monitoring が参照して起動/ループ停止に使用（data/stop_requested.flag）
  - kill.flag: 監視モジュール（KillSwitch）が書き込み、ExecutionEngine に停止を促す（path は Settings.kill_flag_path、デフォルト data/kill.flag）
- Paper trading の分離:
  - KABUSYS_ENV=paper_trading のときは本番 DB に書き込まず、paper_trading 用 SQLite を使用
  - PAPER_FILL_MODE で約定の挙動（instant/partial/never/reject）を指定可能
- OpenAI の呼び出し:
  - news_nlp.py / regime_detector.py が OpenAI を利用（OpenAI API キーを OPENAI_API_KEY または引数で指定）
  - API 呼び出しはリトライ・エラーハンドリング（429, 5xx, タイムアウト等）を行い、失敗時は安全側のデフォルト値で継続する設計
- DB:
  - DuckDB: 分析・prices_daily 等の大量データ格納用（デフォルト data/kabusys.duckdb）
  - SQLite: 監視ログ・取引ログ等（monitoring.db / paper_trading.db）
- ログレベル: LOG_LEVEL 環境変数で制御

ディレクトリ構成（主要モジュール）
---------------------------------
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視用）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （注）alert_manager の実装ファイルが存在（アラート送信機能）

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - tools/
    - __init__.py
    - paper_verification_report.py

  - utils/
    - __init__.py
    - process_priority.py     — プロセス優先度・CPU affinity 設定

注意事項 / よくある質問
-----------------------
- Python バージョン:
  - 本コードは型注釈で |（PEP 604）を使っているため Python 3.10+ を想定しています。
- .env の扱い:
  - .env は絶対に Git にコミットしないでください（シークレットが含まれます）。
  - config_setup.py が .env テンプレートを生成します。
- 本番運用:
  - KABUSYS_ENV=live を使うと本番モードになります。LINE 通知設定等を必ず確認してください（validate_config が追加チェックを行います）。
  - KILL_FLAG_CLEAR_ON_START を誤って 1 にしておくと Kill Switch が自動でクリアされるため運用上危険です（本番では 0 を推奨）。
- OpenAI など外部 API:
  - 使用する際はレートリミットやコストに注意してください。ニュース NLP 系はバッチ & リトライ済みの設計ですが、API キー設定は必須です。
- テスト:
  - モジュールは外部副作用を分離する方針（DB 接続/クライアント注入）で実装されているため、ユニットテスト用にモックしやすくなっています。

サンプル .env（抜粋）
-------------------
以下は .env の例（実際は secret を埋めてください）。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

最後に
------
本 README はコードベースの主要機能と運用フローの概要を載せています。実運用や外部 API 連携を行う場合は、各モジュール（特に execution/*、monitoring/*、ai/*）の内部実装と設定ファイル（config/*.yaml）を詳細に確認してください。必要があれば README を追記していきます。