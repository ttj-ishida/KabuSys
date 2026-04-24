# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリ群および運用スクリプト群です。  
このリポジトリは、戦略のリサーチ（DuckDB ベース）、ポートフォリオ構築、ポジションサイズ計算、実行エンジン、監視、AI（ニュースセンチメント／レジーム判定）など、実運用を意識したモジュール群を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 動作要件
- セットアップ手順
- 環境変数（主要なもの）
- 使い方（コマンド例）
- ディレクトリ構成（抜粋）
- 運用上の注意

---

プロジェクト概要
- このプロジェクトは、日本株自動売買システム「KabuSys」のコアライブラリ群です。
- データ解析は DuckDB、永続化・軽量ログは SQLite を利用します。
- 発注は実口座（kabuステーション）またはペーパートレード（MockBroker）で分離可能。
- 監視と Kill Switch により運用上の安全策を提供します。
- ニュース記事のセンチメント評価や市場レジーム判定には OpenAI を用いた LLM 呼び出し機能を持ちます（外部 API キーが必要）。

---

主な機能一覧
- 設定読み込み・管理（kabusys.config）
- 対話式 .env 作成ウィザード（kabusys.config_setup）
- 起動前設定検証 CLI（kabusys.validate_config）
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し data/paper_trading.db に記録
  - 停止フラグ / pid ファイルの管理
- 監視ループ起動スクリプト（run_monitoring.py）
  - System / Trade / Risk の監視、Kill Switch 評価、アラート連携
  - MONITOR_POLL_INTERVAL によるポーリング間隔変更
- 監視 DB 操作（monitoring_db.py） — system_status, trade_logs, positions, risk_logs, dashboard
- リスク監視（risk_monitor.py）
- ポートフォリオ構築（portfolio: 候補選定・重み計算・ポジションサイズ計算）
- リサーチ（research: ファクター計算、特徴量探索、IC 計算）
- AI モジュール（ai.news_nlp, ai.regime_detector） — OpenAI API を利用
- 運用ツール（tools.paper_verification_report） — ペーパートレーディング検証レポート出力
- ロギング・プロセス優先度などのユーティリティ（utils.logging_setup, utils.process_priority）

---

動作要件
- Python 3.10 以上（型ヒントで | 演算子を使用しているため）
- 推奨パッケージ（機能に応じて）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイルの検証を行う場合）
- SQLite は標準ライブラリの sqlite3 を使用
- インターネット接続（OpenAI API を利用する場合）

---

セットアップ手順（ローカル開発環境の一例）
1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - (macOS/Linux) source .venv/bin/activate
   - (Windows) .venv\Scripts\activate

3. 必要なパッケージをインストール
   - 代表的に次をインストールしてください（requirements.txt がある場合はそれを使ってください）:
     - pip install duckdb psutil openai PyYAML

4. .env を作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
     - ウィザードは .env を生成します（.env は絶対に Git にコミットしないでください）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付ける

6. データディレクトリ / ログディレクトリの確認
   - デフォルトで data/（SQLite・PID・flag）と logs/（ログ）が使われます。必要なら作成してください。logging_setup は自動で作成を試みます。

---

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード
- 運用関連
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（KABUSYS_ENV=paper_trading 時に使用）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…）
  - PID_FILE_PATH — ExecutionEngine の pid ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch の flag ファイルパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）
  - OPENAI_API_KEY — OpenAI API キー（ai モジュールで必要）

注意: validate_config で必須環境変数の未設定を検出します。example は .env.example を参照してください。

---

使い方（主要コマンド例）

1. 対話式設定ウィザード
   - python -m kabusys.config_setup
   - 出力先を指定する場合:
     - python -m kabusys.config_setup --env-file /path/to/.env

2. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗にする: python -m kabusys.validate_config --strict

3. 実行エンジン起動
   - 本番/開発/ペーパーは KABUSYS_ENV で切替:
     - KABUSYS_ENV=development python -m kabusys.run_execution
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 停止制御:
     - run_execution はプロジェクトルート/data/stop_requested.flag を監視して停止します（外部から停止させるにはこのファイルを作成）
     - Kill Switch による停止は data/kill.flag を生成します（monitoring 側で生成）

4. 監視ループ起動
   - MONITOR_POLL_INTERVAL で間隔を調整:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は monitoring DB（settings.sqlite_path）を使用します。monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用する点に注意。

5. Paper Trading レポート生成（ツール）
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db か環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

6. AI（ニュース NLP / レジーム判定）
   - OpenAI API キーを環境変数に設定して使用
   - モジュールを直接呼ぶ例（スクリプト内から）:
     - from datetime import date
       from kabusys.ai.news_nlp import score_news
       # conn は duckdb connection を渡す
       # score_news(conn, date(2026, 4, 10), api_key="sk-...")
   - regime_detector も同様に score_regime を呼び出して market_regime テーブルへ書き込みできます。
   - AI 呼び出しは失敗時にフォールバック処理を持ち、部分失敗を許容する設計です。

7. ログ
   - デフォルトは logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
   - setup_logging はコンソール（stdout）と日次ローテートファイル出力を設定します。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — 監視 DB 層（SQLite）
    - monitoring_engine.py   — 各モニタの統合（ポーリング）
    - system_monitor.py
    - trade_monitor.py       — （省略したが存在を想定）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       — （アラート処理）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py

その他:
- data/ — 実行時に使用される SQLite ファイル、pid、flag など（デフォルトパス）
- logs/ — ログファイル（デフォルト）

（注）上記は本 README に含まれるコードファイルの抜粋ベースの構成です。リポジトリ全体の正確なツリーは実際のファイルを参照してください。

---

運用上の注意
- .env は秘匿情報を含むため絶対に Git にコミットしないでください。
- 本番運用（KABUSYS_ENV=live）の場合、LINE 通知等の設定や kill flag の自動クリア設定に注意してください（validate_config でチェックされます）。
- run_execution は stop_requested.flag の存在で起動を抑制・停止を行います。外部から安全に停止させるには data/stop_requested.flag を作成してください（運用手順を整備してください）。
- OpenAI API はコストとレート制限があります。AI 機能の運用は経済性・レート管理を考慮してください。

---

問題・改善提案・貢献
- バグ報告や改善提案は Issue を立ててください。Pull Request も歓迎します。

---

最小セットの実行例（まとめ）
1. 仮想環境作成・依存インストール
   - python -m venv .venv && source .venv/bin/activate
   - pip install duckdb psutil openai PyYAML

2. .env を作成
   - python -m kabusys.config_setup

3. 設定検証
   - python -m kabusys.validate_config

4. 監視プロセス起動（別ターミナル）
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

5. 実行エンジン起動
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

以上。README に不足してほしい点や、特定の操作（デバッグ方法・単体テストの実行など）について追記希望があれば教えてください。