# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI（ニュース NLP / レジーム判定）や解析ユーティリティをまとめたプロジェクトです。Production と Paper Trading を分離できる設計になっています。

---

## 概要

KabuSys は以下の主要機能を提供します。

- 戦略・ポートフォリオ構築ロジック（候補選定、重み計算、ポジションサイズ決定）
- 発注および注文管理（ExecutionEngine、OrderManager、RiskManager 等）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor、Kill Switch）
- AI を使ったニュースセンチメント（OpenAI）や市場レジーム判定
- 研究用モジュール（ファクター計算、特徴量探索、IC 計算）
- 運用用ユーティリティ（設定ウィザード・設定検証・紙トレ検証レポート等）
- DuckDB / SQLite を用いたデータ保存・解析

設計上のポイント：
- Paper Trading モードでは Mock ブローカーを用い、発注履歴は `data/paper_trading.db` に分離して記録します（本番 DB と完全に分離）。
- .env 自動読み込み機能あり（プロジェクトルートの `.env` / `.env.local` をロード）。無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 機能一覧

- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 / ペーパートレードを切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
- 設定周り
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml の事前検証 CLI
- 監視
  - monitoring_engine.py: 各 Monitor を束ねる
  - system_monitor.py, trade_monitor.py, risk_monitor.py: 個別監視実装
  - kill_switch.py: 条件を満たすと `data/kill.flag` を書いて ExecutionEngine を停止
  - monitoring_db.py: 監視用 SQLite スキーマ・永続化層
- 発注 / 実行
  - execution パッケージ: Engine, OrderManager, RiskManager, Reconciler 等（ブローカーファクトリで実環境／Mock を切替）
- ポートフォリオ構築
  - portfolio パッケージ: 候補選定、重み付け、リスク調整、ポジションサイズ決定
- 研究 / 解析
  - research: ファクター計算（モメンタム / ボラティリティ / バリュー）、特徴量探索、IC 計算
  - tools: paper_verification_report（Paper Trading の検証レポート生成）
- AI
  - ai.news_nlp: ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - ai.regime_detector: マクロ / ETF MA を組み合わせて市場レジーム判定

ユーティリティ:
- utils.logging_setup: 統一的なロギング設定（コンソール + 日次ローテートファイル）
- utils.process_priority: プラットフォーム非依存でプロセス優先度 / CPU affinity を設定

---

## セットアップ手順

前提:
- Python 3.10+ 推奨（パッケージの型・構文より）
- system 側に DuckDB、SQLite、psutil などをインストール可能であること

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は最低限以下を入れてください）
     - duckdb, psutil, openai, (PyYAML は validate_config の YAML 検証に必要)

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくはリポジトリの .env.example を参照し `.env` を手動作成

5. 設定検証
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトで使用するファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
     - PID / flag ファイル: data/execution.pid, data/stop_requested.flag, data/kill.flag
   - `utils.logging_setup` がログディレクトリを自動作成しますが、権限に注意してください。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

（AI 機能を使う場合）
- OPENAI_API_KEY

主なオプション環境変数
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL（例: INFO）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: instant | partial | never | reject

---

## 使い方

運用における簡単なコマンド例を示します。

1. ExecutionEngine を起動
   - 本番 / Paper は KABUSYS_ENV で切替:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - python -m kabusys.run_execution  # KABUSYS_ENV=development / live に応じて動作
   - 動作: プロセス優先度を `high` に設定し、指定 DB に接続して ExecutionEngine をデーモン実行します。
   - 停止は `data/stop_requested.flag` を作成することでエンジンスレッドに停止を促します。

2. Monitoring を起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

3. 設定ウィザード
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
   - デフォルト DB は `data/paper_trading.db`。`--db` でパス指定可能。

6. AI 関連（コードから直接呼び出す）
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")  # api_key optional（環境変数を参照）
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="...")

注意事項:
- `run_monitoring` は監視 DB（sqlite）に本番 sqlite_path を環境に関係なく使用します（監視は本番データ参照前提）。
- `run_execution` は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し発注履歴は `data/paper_trading.db` に記録されます。
- Kill Switch は RiskMonitor の結果等により `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります（Execution 起動時に設定でクリア可能）。

---

## 主要ファイル / ディレクトリ構成

（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み / Settings クラス（.env 自動読み込み）
  - config_setup.py
    - .env を対話式で生成・更新するウィザード
  - validate_config.py
    - 起動前の設定検証ツール
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - ai/
    - news_nlp.py
      - OpenAI を使ったニュースセンチメント集約・スコア書き込み
    - regime_detector.py
      - ETF MA とマクロニュースでレジーム判定
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ初期化・CRUD 用ラッパ
    - monitoring_engine.py
      - 各 Monitor を束ねてポーリング
    - system_monitor.py
      - CPU / メモリ / データ鮮度等のチェック
    - risk_monitor.py
      - ドローダウン / ポジション上限監視
    - trade_monitor.py (存在: 参照されるがコードベースで別ファイル)
    - kill_switch.py
      - kill.flag の生成 / 判定
    - alert_manager.py (存在: 参照されるがコードベースで別ファイル)
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
      - 発注 / 注文管理 / リスク管理関連（ブローカ抽象化）
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
    - paper_verification_report.py
    - __init__.py
  - utils/
    - logging_setup.py
      - 設定の統一化（Stream + TimedRotatingFile）
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定

最上位にあるファイル（プロジェクトルート）:
- .env（プロジェクト設定） — Git にコミットしないでください
- data/（DB / PID / flag ファイルを格納）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/stop_requested.flag
  - data/kill.flag
- logs/（ログファイルがここに出力されます）

---

## よく使う環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- OPENAI_API_KEY (AI 機能使用時)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading の場合の専用 DB)
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL (run_monitoring の秒間隔)

---

## 運用メモ / 注意点

- ログ: setup_logging は stdout と日次ローテートファイルに出力します。ログディレクトリに書き込み権限が必要です。
- PID / stop フラグ:
  - ExecutionEngine は pid_file を作成してプロセス管理に使います（設定でパス変更可）。
  - stop/kill フラグはファイル存在チェックで制御されます。運用側で手動作成・削除が可能です。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・マイグレーション（カラム追加）処理を行います。
- Paper Trading:
  - PAPER_FILL_MODE により MockBroker の挙動を変更できます（instant/partial/never/reject）。
  - Paper 用 DB は本番 DB と分離してください。

---

## 貢献 / 拡張ポイント

- strategy / execution 部分はプラグイン化しやすい設計を意識しています。ブローカクライアントの追加や
  position sizing の拡張（銘柄別単元サイズの扱い）等が想定されています。
- AI 呼び出しはリトライ / バリデーションを組み込んでいますが、プロンプトやモデルの変更・ロギング強化は容易です。
- DuckDB を用いたファクタ計算はスケーラブルで効率的です。追加ファクターやバックテスト機能の実装が可能です。

---

README は導入・運用の出発点です。具体的な API の使い方や ExecutionEngine / OrderManager の内部仕様、strategy の設計仕様は別ドキュメント（StrategyModel.md 等）を参照してください。質問や特定ファイルの詳細説明が必要であれば教えてください。