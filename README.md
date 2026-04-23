KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・リサーチ・モニタリングを目的とした Python ベースの小規模なシステム群です。  
主な責務は以下の通りです。

- 注文実行エンジン（ExecutionEngine）／リスク管理／約定ログの処理
- システム稼働監視・トレード監視・Kill Switch（停止フラグ）発動
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リサーチ用ファクター計算・ファクター評価（DuckDB を利用）
- Paper Trading 用の検証レポート生成
- ニュースを LLM（OpenAI）でスコアリングして AI スコアを生成／レジーム判定

主な機能
--------
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（専用 SQLite）と live（本番 DB）を切替
  - BrokerClientFactory を通じてブローカークライアントを生成、ExecutionEngine を起動
  - 停止フラグ（data/stop_requested.flag）や PID ファイル管理
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor、TradeMonitor、RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）へ永続化
- 設定関連 CLI
  - config_setup.py: 対話式ウィザードで .env を生成 / 更新
  - validate_config.py: .env と config/*.yaml の検証（--strict オプションあり）
- Research / AI
  - duckdb ベースのファクター計算（momentum/value/volatility 等）
  - news_nlp: OpenAI（gpt-4o-mini）でニュースをスコアリングして ai_scores に格納
  - regime_detector: ETF MA とマクロニュース（LLM）を合成して market_regime を判定
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（期間指定可能）
- ユーティリティ
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定ユーティリティ

動作要件（推奨）
----------------
- Python 3.10 以上（ソース内で | 型注釈や最新構文を使用）
- 必須パッケージ（代表例）
  - duckdb
  - psutil
  - openai
- 任意 / 機能による追加
  - PyYAML （validate_config の YAML 検証）
- 標準ライブラリ: sqlite3, logging, argparse など

セットアップ手順
----------------
1. リポジトリをクローン / 取得
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - 例:
     - pip install duckdb psutil openai
     - （検証に PyYAML を利用する場合）pip install PyYAML
   - （開発用に）pip install -e . が使える場合はプロジェクトルートに pyproject.toml があれば利用可能
4. ディレクトリ作成（必要に応じて）
   - data/ と logs/ を作成（実行時に自動作成されることもありますが、事前作成しておくと安全）
     - mkdir -p data logs
5. 環境変数の設定
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を手動で作成（下記「主要環境変数」参照）
6. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い

主要な環境変数（.env）
---------------------
（config_setup.py にある項目を要約）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルのパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading DB（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番用のアラート通知（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、production では 0 推奨）

重要な運用ファイル（デフォルトパス）
------------------------------------
- data/monitoring.db           — 監視ログ（SQLite）
- data/kabusys.duckdb          — 分析用 DuckDB
- data/paper_trading.db        — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading 時）
- data/execution.pid           — Execution の PID を記録（run_execution で使用）
- data/stop_requested.flag     — run_execution / run_monitoring の停止検知用フラグ
- data/kill.flag               — Kill Switch が発動した際に書き込まれるファイル

使い方（起動 / CLI）
-------------------

- 実行（Execution Engine を起動）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、data/paper_trading.db に記録されます
  - 実行前に .env を整備し、必要な API トークン等を設定してください
  - 停止方法:
    - data/stop_requested.flag を作成すると run_execution は安全に停止します
    - また Execution 側は kill.flag の存在を検出すると停止する設計（KillSwitch）

- 監視（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で調整:
    - MONITOR_POLL_INTERVAL=30  python -m kabusys.run_monitoring
    - デフォルトは 60 秒
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を使用して監視ログを書き込みます

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話式で .env を作成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告でも exit(1)

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要: 環境変数 OPENAI_API_KEY を設定
  - news_nlp.score_news, regime_detector.score_regime などの関数はプログラムから呼び出して利用します
  - 利用するモデル: gpt-4o-mini（ソース内で指定）

ログ・プロセス管理
------------------
- ログは kabusys.utils.logging_setup.setup_logging で統一的に設定され、stdout と logs/<app_name>.log（日次ローテート）に出力されます
- 起動スクリプトは起動直後に set_process_priority("high") を呼びプロセス優先度を上げます（psutil に依存）
- graceful stop: data/stop_requested.flag を作成することで run_* スクリプトはループを抜けて終了します

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

src/kabusys/utils/
- logging_setup.py         — ログ設定ユーティリティ
- process_priority.py      — プロセス優先度 / CPU affinity

src/kabusys/monitoring/
- monitoring_db.py         — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
- system_monitor.py
- trade_monitor.py         — （実装ファイルはリポジトリ内にあり、監視ロジックを実装）
- risk_monitor.py
- kill_switch.py
- monitoring_engine.py
- alert_manager.py         — （アラート送信ロジック等）

src/kabusys/execution/
- execution_engine.py      — ExecutionEngine 本体
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py
- broker_factory.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py

src/kabusys/ai/
- news_nlp.py
- regime_detector.py

src/kabusys/tools/
- paper_verification_report.py

注意点 / 運用上のヒント
---------------------
- 本番（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の扱いに注意してください。KILL_FLAG_CLEAR_ON_START=1 は本番では危険です。
- .env は機密情報を含むので絶対に Git にコミットしないこと（config_setup.py のヘッダにも注意書きあり）。
- OpenAI 等外部 API 呼び出しにはレート制限やエラーがあるため、既定でリトライやフォールバックロジックが組み込まれていますが、API キーとクォータ管理は運用で注意してください。
- DuckDB / SQLite のファイルパスは Settings で上書き可能です。分析用途の DuckDB と監視用 SQLite は分離されています。

補足
----
- ソースの多くは「DB の存在チェック」「冪等操作」「フェイルオープン」など運用を重視した実装になっています。まずは development モードで local DB を作成して動作確認してください。
- 追加のセットアップ手順（ブローカー接続の設定、strategy の登録など）は別ドキュメントや config/*.yaml に従ってください（validate_config で参照する config/*.yaml が準備されている想定です）。

問題・改善提案がある場合はソースコードの該当モジュール（例: monitoring/system_monitor.py, execution/*）を参照の上、Issue を立ててください。