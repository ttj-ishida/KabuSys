README — KabuSys（日本株自動売買システム）
========================

概要
----
KabuSys は日本株向けの自動売買・研究用ライブラリ群です。  
本リポジトリは、取引の実行エンジン（ExecutionEngine）、監視・アラート基盤（Monitoring）、ポートフォリオ構築・リスク制御、研究用ファクター計算、LLM を使ったニュース NLP などの機能を含みます。  
プロセス起動スクリプトや設定ウィザード / 検証ツールも提供します。

主な特徴
--------
- ExecutionEngine：本番 / ペーパートレード両対応（KABUSYS_ENV により切替）
- Monitoring：システム状態、注文ログ、リスク（ドローダウン・ポジション上限）を定期監視しログ/アラートを生成
- Portfolio モジュール：候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム補正
- Research：DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー）や特徴量評価ツール
- AI（OpenAI）連携：ニュースのセンチメントスコアリング / 市場レジーム判定（OpenAI API 必須）
- 設定ウィザード（.env 生成）と設定検証ツール（config/*.yaml の存在・環境変数チェック）
- ログは stdout と日次ローテーションファイル（logs/<app>.log）に出力

必要条件（主な依存）
-------------------
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定ファイル検証を行う場合、なくても実行は可能だが検証が省略される）

セットアップ（開発環境）
---------------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境の作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 実際のプロジェクトでは requirements.txt を用意している想定です。

環境変数（主要項目）
-------------------
重要（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD     — kabuステーション API パスワード（必須）

任意・デフォルトあり
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（"1" 有効、デフォルト "0"）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）※ run_monitoring 用
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時に必要）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant/partial/never/reject、デフォルト "instant"）

.env の自動読み込み
- プロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

設定作成 / 検証
---------------
1. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - .env の既存値読み込み・上書きに対応

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit 1）

起動・使い方（主要スクリプト）
----------------------------

1) ExecutionEngine（注文実行）
- 本番（KABUSYS_ENV=live）/ 開発（development）/ ペーパートレード（paper_trading）を環境変数で切り替え
- paper_trading 時は MockBrokerClient を使用し、データは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます

実行:
- python -m kabusys.run_execution

ポイント:
- 起動時に PID ファイル（デフォルト data/execution.pid）を扱います
- data/stop_requested.flag が存在すると起動を抑止または実行中に停止します
- Kill Switch（data/kill.flag）により外部から発注停止をトリガできます

2) Monitoring（監視ループ）
- システム状態、注文ログ、リスク監視をポーリングして DB に記録・アラートを送出します

実行:
- python -m kabusys.run_monitoring

オプション・動作:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）
- Monitoring は起動時に Settings から sqlite_path を取得し、本番 DB を参照します（環境にかかわらず）

3) Paper Trading 検証レポート（ツール）
- 過去期間のペーパートレード DB を解析して PASS/FAIL 判定レポートを出力

実行例:
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先）

4) AI（ニュース NLP / レジーム判定）
- OpenAI API を用いる機能（news_nlp.score_news / regime_detector.score_regime）は OPENAI_API_KEY を必要とします
- これらはライブラリ関数として使用することを想定（例: Python スクリプト内から呼び出し）

停止方法・フラグ
----------------
- run_execution / run_monitoring の停止は通常の KeyboardInterrupt（Ctrl+C）で可能
- 永続的に停止させたい場合はプロジェクトルートの data/stop_requested.flag を作成すると実行スクリプトが検知して終了します
- ExecutionEngine を外部から強制停止するために data/kill.flag を書き込む KillSwitch 機能があります（KillSwitch は監視側で評価し flag を書き込みます）
- kill.flag を自動でクリアする設定は KILL_FLAG_CLEAR_ON_START=1（本番では推奨しない）

ログ
----
- 標準出力（stdout）とファイル出力（logs/<app>.log）を併用します
- ログディレクトリは LOG_DIR、ログレベルは LOG_LEVEL で指定
- 日次ローテーション（30世代保存）

DB・マイグレーション
-------------------
- 監視用 DB（SQLite）は起動時に init_monitoring_db() で必要テーブル・インデックスを冪等に作成します
- DuckDB は分析用データベース（prices_daily などのテーブルを想定）

開発者向け注意
---------------
- .env は機密情報を含むため、Git にコミットしないこと
- 一部関数は実環境（OpenAI / kabu API / J-Quants）に依存するため、テスト時は適切にモックすること（例: news_nlp._call_openai_api を patch）
- process_priority、cpu_affinity の設定はプラットフォーム依存のため psutil の権限制約に注意

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要モジュール一覧と簡単な説明です。

- kabusys/__init__.py
  - パッケージ定義・バージョン

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番 / ペーパー切替、PID 管理、停止フラグ検出）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- config.py
  - 環境変数・設定取得（Settings クラス）、.env 自動読み込みロジック

- config_setup.py
  - 対話式 .env 作成ウィザード

- validate_config.py
  - 起動前の設定検証 CLI（環境変数・config/*.yaml 等のチェック）

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成ツール

- monitoring/
  - monitoring_db.py — SQLite に対する永続化層（テーブル初期化 + MonitoringDB クラス）
  - system_monitor.py — CPU/メモリ/Disk/プロセス/データ鮮度監視
  - trade_monitor.py — 注文滞留や異常約定の検出（コード上に存在）
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py — data/kill.flag による停止スイッチ
  - alert_manager.py —（アラート送信管理、LINE や他の通知基盤と連携する想定）

- execution/
  - broker_factory.py — BrokerClient の抽象化と Mock / 実実装の生成
  - execution_engine.py — ExecutionEngine（セッション管理・注文制御）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注・注文管理・整合性・リスク管理

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（単元株丸め・集計キャップ）
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — ファクター（momentum/value/volatility）計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン・IC・統計サマリー等

- ai/
  - news_nlp.py — OpenAI を用いたニュースセンチメントスコアリング（ai_scores へ書込）
  - regime_detector.py — ETF MA とマクロニュースを合成した市場レジーム判定

- utils/
  - logging_setup.py — 統一的なログ設定（stdout + 日次ファイル）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補足
----
- 設定ファイルテンプレート（.env.example や config/*.yaml の生成スクリプト）がある想定です（scripts 等）。validate_config は config/*.yaml の存在と YAML パース検証を行います（PyYAML が必要）。
- AI 機能は外部 API に依存するためレート制限や失敗に備えたリトライ・フォールバックロジックを組み込んでいます。

ライセンス・貢献
----------------
- 本ドキュメントではライセンス情報は含めていません。リポジトリの LICENSE ファイルを参照してください。  
- 貢献方法や開発フローは CONTRIBUTING.md 等をプロジェクトに追加することを推奨します。

以上。必要であれば README にサンプル .env、起動手順のスクリプト例（systemd / docker-compose）や、各モジュールの API 使用例（コードスニペット）を追加します。どの情報が欲しいか教えてください。