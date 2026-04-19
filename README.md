KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／リサーチを行うための Python ベースのプロジェクトです。  
市場データの集計・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、
AI を使ったニュースセンチメント評価などのコンポーネントを備えています。  
設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避」「フェイルセーフ（API失敗時の継続）」を重視しています。

主な特徴（機能一覧）
-------------------
- ExecutionEngine
  - 本番 / ペーパートレードの切替（KABUSYS_ENV）
  - リスク制御（RiskManager）や注文管理（OrderManager）を備えた発注基盤
- Monitoring（監視）
  - システム状態（CPU/メモリ/ディスク）・プロセス死活のポーリングとログ化
  - 注文ログ / リスクログ の永続化（SQLite）
  - Kill Switch（条件に応じて停止フラグを書き込み、Execution を停止）
  - 各種アラート送信（LINE 等のトークンを利用）
- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分・スコア加重、リスク調整（セクター上限）、株数決定（単元丸め）
- Research（リサーチ）
  - DuckDB を用いたファクター（モメンタム／バリュー／ボラティリティ）計算
  - 将来リターン・IC（情報係数）計算などの統計ツール
- AI 支援
  - ニュース記事を LLM（OpenAI）でスコア化（news_nlp）
  - マクロ + ETF MA200 乖離を使った市場レジーム判定（regime_detector）
- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools/paper_verification_report）

前提（Prerequisites）
--------------------
- Python 3.10+（型アノテーション等を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config yaml を検証する場合）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（OpenAI / ブローカー API を使う場合）

セットアップ手順
----------------

1. リポジトリをクローン、仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は必要パッケージを個別にインストール）
     - pip install duckdb psutil openai pyyaml

3. 初期設定（.env ファイル）
   - 対話ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - OpenAI を利用する場合:
     - OPENAI_API_KEY を設定してください（環境変数か config）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにするには --strict を付ける

5. ディレクトリ作成（必要に応じて）
   - data/ （SQLite や PID/flag を置く）
   - logs/ （ログ出力）
   - これらはスクリプトが自動作成する場合もありますが、権限等に注意してください。

使い方（起動・コマンド例）
-------------------------

- ExecutionEngine を起動
  - 本番（DEFAULT: KABUSYS_ENV を .env で指定）
    - python -m kabusys.run_execution
  - ペーパートレード（例）
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - ※ paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで監視ループを終了できます。

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- .env の作成/更新（対話ウィザード）
  - python -m kabusys.config_setup

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

環境変数（主要）
----------------
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で必要
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログの出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_PATH: Kill Switch の flag ファイルパス（既定: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（"1"で有効、開発向け。運用時は "0" を推奨）

停止・Kill Switch
-----------------
- 手動停止（監視プロセス・実行エンジン）:
  - プロジェクトルートの data/stop_requested.flag を作成するとループは検知して終了します。
- Kill Switch（自動停止条件）:
  - RiskMonitor 等の判定により data/kill.flag が書き込まれると ExecutionEngine 側で停止シグナルとして扱います。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag をクリアします（本番では推奨されません）。

ログ
----
- logging_setup を全起動スクリプトで利用しています：
  - コンソール（stdout）出力と日次ローテートされるファイル出力（logs/<app_name>.log）を併用。
- ログディレクトリが作成できない場合はファイルハンドラはスキップされ、コンソール出力のみになります。

簡単なトラブルシューティング
----------------------------
- 依存パッケージが足りない / モジュールが import できない
  - pip install を再度確認してください（duckdb, psutil, openai, pyyaml など）
- OpenAI API 呼び出しが失敗する
  - OPENAI_API_KEY の設定、レート制限、ネットワーク接続、API クォータを確認してください。ライブラリ例外はリトライ実装がありますが最終的にスキップすることがあります。
- プロセス優先度設定に失敗（Permission / Unsupported）
  - set_process_priority は OS に依存し、権限不足や未対応 OS の場合は警告ログを出してスキップします。
- DB ファイルのパーミッション
  - data/ 以下のファイルに対する読み書き権限を確認してください。
- .env 自動ロード
  - config.py はプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みします。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要ディレクトリ構成
-------------------
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理
  - config_setup.py        — .env 対話ウィザード
  - validate_config.py     — 起動前設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py     — ログ設定ユーティリティ
    - process_priority.py  — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py    — システム監視（CPU/メモリ/データ鮮度等）
    - risk_monitor.py      — ドローダウン / ポジション上限監視
    - trade_monitor.py     — （注文関連監視、ソース内参照）
    - kill_switch.py       — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 複数モニタを束ねるエンジン
    - alert_manager.py     — （アラート送信、ソース内参照）
  - execution/
    - execution_engine.py  — ExecutionEngine 本体（起動/セッション管理）
    - broker_factory.py    — ブローカークライアントファクトリ
    - order_manager.py     — 注文管理
    - order_repository.py  — 注文永続化（SQLite）
    - risk_manager.py      — 発注前リスクチェック
    - reconciler.py        — 注文状態同期
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py   — 株数計算・制限・単元丸め
    - risk_adjustment.py   — セクター上限 / レジーム乗数
  - research/
    - factor_research.py   — momentum/value/volatility 等の計算（DuckDB）
    - feature_exploration.py — IC / 統計サマリー等
  - ai/
    - news_nlp.py          — ニュース NLU / スコア化（OpenAI）
    - regime_detector.py   — 市場レジーム判定（MA200 + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

開発者向けメモ
---------------
- DuckDB は分析用のローカル SQL エンジンとして利用します。prices_daily / raw_financials / raw_news 等のテーブルを想定しています。
- モジュールはできるだけ副作用を避け、公開関数は引数で接続や API キーを受け取る（テスト容易性を配慮）。
- LLM 呼び出し部はリトライやレスポンス検証の工夫がされています。テスト時は各 _call_openai_api をモック可能です。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（無ければ別途設定してください）。

以上が README の概要です。必要であれば、導入手順（systemd / Docker / crontab での運用例）、より詳しい設定項目一覧（各環境変数の詳細）や運用チェックリストを追加で作成します。どの内容を優先して追記しましょうか？