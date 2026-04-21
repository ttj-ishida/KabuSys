# KabuSys

日本株自動売買システムのコードベース（ライブラリ＋起動スクリプト群）です。  
この README はリポジトリ内のモジュール群（監視・実行エンジン、ポートフォリオ構築、ファクター計算、AI 補助など）に基づいて作成しています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動例・CLI）
- ディレクトリ構成
- 重要な環境変数・ファイル
- 運用上の注意

---

プロジェクト概要
----------------
KabuSys は日本株の自動売買システムを想定した Python モジュール群です。主な役割は次のとおりです。

- 実行エンジン（ExecutionEngine）: ブローカーとやり取りし、発注・注文管理・リスク管理を行う
- 監視エンジン（MonitoringEngine）: システム状態、注文状態、リスク（ドローダウン等）を定期チェックし、アラートや Kill Switch を管理する
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ算出、セクター制約など純粋関数群
- リサーチ: DuckDB 上の株価・財務データからファクター計算、将来リターン、IC 計算など
- AI 補助: OpenAI を用いたニュースのセンチメント（ai_scores）や市場レジーム判定
- ユーティリティ: ロギング設定、プロセス優先度 / CPU affinity 設定、設定ウィザード / バリデータ等
- 運用ツール: Paper Trading の検証レポート生成スクリプト など

設計上の特徴:
- DuckDB（分析用）と SQLite（監視・履歴用）を併用
- 本番/ペーパートレードの DB 分離（KABUSYS_ENV による）
- .env を使った設定管理・対話式ウィザード
- ログは stdout と日次ローテートファイル（logs/*.log）へ出力

---

主な機能一覧
--------------
- run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading モードで MockBroker を利用）
- run_monitoring: SystemMonitor のポーリングループを起動（監視ログを書き込む）
- config_setup: .env の対話式生成・更新ウィザード
- validate_config: 起動前チェック（必須環境変数や config/*.yaml の存在・簡易検証）
- tools.paper_verification_report: Paper Trading の検証レポートを生成（稼働率・注文成功率・レイテンシ等）
- portfolio.*: 候補選定・重み付け・単元丸め・ポジションサイズ計算
- research.*: ファクター計算（モメンタム、バリュー、ボラティリティ等）、IC / 統計サマリ
- ai.news_nlp / ai.regime_detector: OpenAI を用いたニュースセンチメントと市場レジーム判定
- monitoring.*: DB 永続化（monitoring_db）、System/Trade/Risk モニタ、KillSwitch、アラート管理
- utils.logging_setup / utils.process_priority: 起動時の統一ロギング設定・プロセス優先度設定

---

セットアップ手順
----------------

前提
- Python 3.10+（typing 表記から推定）
- SQLite は標準ライブラリで利用可
- DuckDB, psutil, openai などの外部ライブラリが必要（下記）

推奨的な依存パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config の内容検証を行う場合）
- その他（必要に応じて実行環境で追加）

インストール例（venv を使う例）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml
   （実際の requirements.txt / pyproject.toml がある場合はそちらを使用してください）
4. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   ウィザードに従って J-Quants / kabuAPI / DB パス等を設定してください。
5. 設定検証
   - python -m kabusys.validate_config
   --strict オプションで警告も失敗扱いにできます。

データディレクトリ
- デフォルトでは data/ 配下に各種ファイルを作成します（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）
- ログは logs/ に出力（デフォルト）。LOG_DIR 環境変数で変更可。

---

使い方（起動例・CLI）
---------------------

基本的な起動コマンド（パッケージルートで実行）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モードは環境変数 KABUSYS_ENV で指定:
    - development: 開発（発注なし）
    - paper_trading: ペーパートレード（MockBrokerClient を使用、DB: data/paper_trading.db）
    - live: 本番
  - 起動時に data/stop_requested.flag が存在すると起動をスキップ
  - 実行中止は data/stop_requested.flag を作成するか、Execution 側で kill.flag を検出して停止します

- 監視ループ起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず本番 DB を見る設計）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止制御（運用）
- stop_requested.flag:
  - run_monitoring / run_execution のループは data/stop_requested.flag の存在を見て終了します。
  - 運用側で安全に停止したい場合はこのファイルを作成してください。
- Kill Switch:
  - monitoring モジュールはリスク条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側がこれを検知してセーフシャットダウンします。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 推奨）。

ログ
- setup_logging により stdout（StreamHandler）と日次ローテーションログ（logs/<app_name>.log）が設定されます。
- LOG_LEVEL, LOG_DIR 環境変数で挙動を変更できます。

---

主な環境変数（抜粋）
-------------------
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モードで使用）
- PAPER_FILL_MODE: MockBroker の約定挙動（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログディレクトリ（default: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動削除するか（"1"=削除, デフォルト "0"）

サンプル .env（ウィザードで生成されます）
- .env には上記のキーを設定します（絶対に Git にコミットしないでください）。

---

ディレクトリ構成
----------------

リポジトリ（src/kabusys）内の主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境・設定管理（.env 自動ロード含む）
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py           — 共通ロギング設定
    - process_priority.py        — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py           — SQLite 監視 DB 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (ランタイムで生成される)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb
    - kill.flag / stop_requested.flag / execution.pid など
  - tools/
    - paper_verification_report.py

（上記は要点のみ。詳細は各ファイルの docstring を参照してください。）

---

運用上の注意 / ベストプラクティス
---------------------------------
- .env を絶対に Git にコミットしない（config_setup でも注意書きを表示）
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨
- run_monitoring は本番の monitoring DB（sqlite_path）を参照します。テスト時は環境変数で別 DB を指定するか、config を調整してください。
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）および利用料金に注意してください。LLM 呼び出し失敗時は安全側でフォールバックする実装になっていますが、API コストやレート制限は運用で管理してください。
- ログディレクトリは権限やディスク容量を監視してください。TimedRotatingFileHandler が使用され、デフォルトで 30 日分を保持します。
- プロセス優先度設定（set_process_priority）は OS により動作が異なります（権限不足で設定失敗する可能性あり）。

---

その他
-----
- 各モジュールの詳細（引数・戻り値・副作用）はソースコード内の docstring に豊富な説明があります。実装を理解する際は該当ファイルを参照してください。
- config/*.yaml（system_config.yaml 等）が必要な場合、validate_config が存在をチェックします。生成スクリプト（scripts/generate_config.py）がある場合はそちらを使って雛形を作成してください（現リポジトリにない場合は手動で配置してください）。

---

お問い合わせ / コントリビュート
------------------------------
バグ報告・機能追加提案は Issue にお願いします。プルリクエストは歓迎します。コード貢献の際は既存のコーディング規約・テスト習慣に従ってください。

--- 

README は以上です。必要があれば「起動手順の詳しい例」や「よくあるトラブルシューティング（ログが出ない／DB 作成エラー／OpenAI の認証エラー）」の追加を作成します。どの情報を補足しますか？