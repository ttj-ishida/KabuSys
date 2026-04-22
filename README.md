# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ＋起動スクリプト集）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的とした小規模なシステム群です。  
主な機能は次の通りです:

- 発注エンジン（ExecutionEngine） — リスク管理・オーダー管理を統合して発注を行う
- 監視コンポーネント（MonitoringEngine） — システム状態・注文状態・リスクを定期チェック、アラート/kill switch を管理
- ポートフォリオ構築ユーティリティ — 候補選定、重み付け、ポジションサイズ計算、セクター制限など
- リサーチモジュール — ファクター計算（モメンタム・バリュー・ボラティリティ）や特徴量解析
- AI モジュール — ニュースの NLP スコアリング / レジーム判定（OpenAI API を使用）
- 各種ユーティリティ & CLI スクリプト（.env ウィザード・設定検証・レポート生成 等）
- 永続化レイヤー：SQLite（監視ログ等）および DuckDB（時系列データ・分析用）

設計上の方針として、以下を重視しています：
- 本番／ペーパートレードの分離（paper_trading 環境では専用 DB / モックブローカーを使用）
- ルックアヘッドバイアス防止（AI / リサーチ関数は日付を外部入力として受け取る）
- フェイルセーフ（外部 API 失敗時に処理を継続する）

---

## 機能一覧（主なモジュール）

- 起動スクリプト
  - run_execution.py — 発注エンジンを起動（KABUSYS_ENV によるペーパー/本番切替）
  - run_monitoring.py — 監視プロセスを起動（ポーリングで SystemMonitor を実行）
- 設定関連
  - config.py — 環境変数 / 設定アクセスラッパー（Settings）
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 設定の自動検証 CLI
- 監視
  - monitoring/monitoring_db.py — SQLite へ監視ログ永続化（テーブル作成・CRUD ユーティリティ）
  - monitoring/system_monitor.py — CPU/メモリ/ディスク、データ鮮度、プロセス PID 監視
  - monitoring/trade_monitor.py — （コードベースに含まれる想定監視ロジック）
  - monitoring/risk_monitor.py — ドローダウン・ポジション数の監視とアラートログ
  - monitoring/kill_switch.py — 条件を満たした場合に data/kill.flag を作成して Execution 停止を指示
  - monitoring/monitoring_engine.py — 各モニタの統合とアラート送信
- 発注/実行（execution/*）
  - ExecutionEngine、OrderManager、RiskManager、Reconciler、BrokerClientFactory 等（発注に関する主要コンポーネント）
- ポートフォリオ（portfolio/*）
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・制限・単元丸め・集計キャップ
  - risk_adjustment.py — セクター上限・レジーム乗数
- 研究（research/*）
  - factor_research.py — モメンタム/ボラティリティ/バリューの計算（DuckDB を利用）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- AI（ai/*）
  - news_nlp.py — ニュースのセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.py — ETF MA とマクロニュースを組み合わせて市場レジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成
- ユーティリティ
  - utils/logging_setup.py — 統一ログ設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

前提
- Python 3.10 以上（コード内で「|」型注釈等を使用）
- システムに sqlite3 が利用可能（通常 Python に同梱）
- optional: Docker / systemd などでプロセス管理する場合は適宜設定

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai
   - 任意（YAML 検証など）:
     - PyYAML
   例:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそちらを使用してください）

3. プロジェクトルートの .env を初期作成
   - python -m kabusys.config_setup
     - 対話式に必要な環境変数を設定できます
   - あるいは手動で .env を作成。主なキー:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意、通知用)

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 本番前は --strict を推奨（警告も失敗扱い）

5. データディレクトリの作成
   - デフォルトで logs/ と data/ を使用します。必要なら手動で作成:
     mkdir -p logs data

6. DB（初回は自動作成される）
   - monitoring 用の SQLite（デフォルト data/monitoring.db）は run_* スクリプトでテーブルが作成されます。
   - DuckDB（デフォルト data/kabusys.duckdb）は必要に応じてデータをロードしてください。

注意: .env は機密情報を含むため Git 管理しないでください（config_setup.py のヘッダに注意書きあり）。

---

## 使い方（起動・主要コマンド例）

- 発注エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 説明: KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。停止は data/stop_requested.flag を作成することで指示できます。稼働時は data/execution.pid に PID が書き込まれます。

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path を常に使用（監視 DB は環境にかかわらず本番 sqlite_path を参照）

- .env 対話式セットアップ
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 本番確認は python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または指定 DB を使う: --db path/to/paper_trading.db

- AI 機能（プログラム的利用）
  - OpenAI API キー (OPENAI_API_KEY) を設定してから、kabusys.ai.score_news 等の関数を呼び出す
  - 例: from kabusys.ai import score_news

ログ出力
- デフォルト: stdout と logs/<app_name>.log（日次ローテート、30 日保持）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で指定

停止／Kill Switch
- 監視側で一定条件を満たすと data/kill.flag を作成して Execution を停止させる仕組みがあります。kill.flag は Settings.kill_flag_path で指定可能。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動で消去されます（本番では 0 を推奨）。

プロセス優先度
- 起動スクリプトは set_process_priority("high") を呼び出します。psutil が権限を許可していない場合は警告を出して継続します。

環境変数（要チェック一覧）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨/重要:
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (例: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB)
  - OPENAI_API_KEY (AI を使う場合)
  - LOG_LEVEL
  - LOG_DIR
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - PAPER_FILL_MODE (instant | partial | never | reject)
- 一時的/挙動制御:
  - MONITOR_POLL_INTERVAL（監視ループの睡眠秒数）
  - PAPER_TRADING_SQLITE_PATH（上書き）

---

## ディレクトリ構成（主要ファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py — Settings / .env 自動ロードロジック
    - config_setup.py — .env 対話式ウィザード
    - validate_config.py — 設定検証 CLI
    - run_execution.py — 発注エンジン起動スクリプト
    - run_monitoring.py — 監視ポーリング起動スクリプト
    - utils/
      - logging_setup.py — ログ設定ユーティリティ
      - process_priority.py — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py — SQLite テーブル初期化 / 永続化 API
      - system_monitor.py — システム状態 / データ鮮度監視
      - trade_monitor.py — 注文状態監視（滞留・約定異常等）
      - risk_monitor.py — ドローダウン・ポジション上限監視
      - kill_switch.py — kill.flag 管理
      - monitoring_engine.py — 各モニタの統合
      - alert_manager.py — （アラート配送管理）
    - execution/  — 発注ロジック関連（BrokerFactory / Engine / OrderManager 等）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/ — （実行時に使用する data ディレクトリ：monitoring DB / paper DB / stop flag 等）
    - tools/
      - paper_verification_report.py

---

## 補足・注意事項

- セキュリティ:
  - .env は機密情報を含むため決してリポジトリにコミットしないでください（config_setup.py にも明記あり）。
- 本番環境:
  - KABUSYS_ENV=live の場合は設定を慎重に確認してください（validate_config で警告が出ます）。
  - Kill Switch の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番での誤動作リスクがあるため通常は無効（0）にしてください。
- AI 機能:
  - OpenAI API を呼ぶ箇所はレートリミットや一時的エラーを考慮してリトライ実装がありますが、API キーの管理と料金には注意してください。
- 開発:
  - research/ と portfolio/ の関数群は純粋関数として設計されており、テストしやすく、DuckDB 接続や引数で日付を受け取るため再現性のあるテストが可能です。

---

必要であれば、README に以下を追加できます：
- 依存パッケージの厳密なバージョン（requirements.txt 生成）
- systemd / Docker 用の起動ユニット / Dockerfile サンプル
- 単体テストの実行方法（pytest 等）
- 発注フロー図・ER 図 などのアーキテクチャ図

どの追加情報が欲しいか教えてください。