KabuSys
=======

日本株向けの自動売買システム（プロジェクト断片）。  
このリポジトリには、取引エンジン起動スクリプト、監視（Monitoring）コンポーネント、ポートフォリオ構築・リスク制御ロジック、リサーチ／ファクター計算、AI を使ったニュース NLP 等のモジュール群が含まれます。

概要
----
KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 実行エンジン起動（ExecutionEngine）: 実際の発注を行う（本番／ペーパートレード対応）。
- 監視（Monitoring）: システム稼働状況、注文の滞留・約定異常、ドローダウン監視、Kill Switch の評価。
- ポートフォリオ構築: 候補選定・重み算出・ポジションサイズ計算・セクターキャップ等。
- リサーチ: DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー）と特徴量解析。
- AI モジュール: OpenAI を利用したニュースのセンチメントスコアリング（news_nlp）、及びマクロ情報と価格指標からの市場レジーム判定（regime_detector）。
- ユーティリティ: プロセス優先度や CPU affinity の設定、設定ウィザード・検証ツール、Paper Trading 検証レポート生成など。
- 永続化: DuckDB（分析）および SQLite（監視・発注ログ）を利用。

主な機能一覧
---------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading.db に切り分け。
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを記録。MONITOR_POLL_INTERVAL で間隔上書き可。
- 設定管理
  - config_setup.py: .env を対話式に作成/更新するウィザード。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI。
  - config.py: 環境変数の読み込み・ラッパー（Settings クラス）。
- 監視
  - monitoring/monitoring_db.py: SQLite へのテーブル初期化・読み書きユーティリティ（MonitoringDB）。
  - monitoring/system_monitor.py: CPU/メモリ/ディスク、プロセス生存・データ鮮度チェック。
  - monitoring/trade_monitor.py: 注文滞留・約定異常の検出と risk_logs への登録。
  - monitoring/risk_monitor.py: ドローダウン／ポジション上限監視と dashboard 更新。
  - monitoring/kill_switch.py: kill.flag を書いて ExecutionEngine 停止を要求するロジック。
  - monitoring/monitoring_engine.py: 上記モニタをまとめて定期実行、アラート通知呼び出し等。
- ポートフォリオ
  - portfolio/portfolio_builder.py: 候補選定・等重・スコア重み算出。
  - portfolio/position_sizing.py: 株数決定（risk_based / equal / score）、単元丸め、aggregate cap 処理など。
  - portfolio/risk_adjustment.py: セクター上限適用・レジーム乗数の算出。
- リサーチ
  - research/factor_research.py: モメンタム・ボラティリティ・バリュー等の計算（DuckDB 経由）。
  - research/feature_exploration.py: 将来リターン計算、IC（スピアマン）等。
- AI
  - ai/news_nlp.py: raw_news から銘柄ごとのセンチメントを OpenAI に投げて ai_scores へ書き込む。
  - ai/regime_detector.py: ETF の MA200乖離 とマクロニュースセンチメントを合成して market_regime を算出・保存。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から稼働率 / 注文成功率 / レイテンシ等の検証レポートを生成。

前提（依存）
--------------
以下は代表的なランタイム依存パッケージ（requirements.txt は付属しないが、手動でインストールしてください）:
- Python 3.10+ 推奨
- duckdb
- psutil
- openai
- PyYAML（config 検証時に利用。未インストールなら YAML 検証をスキップ）
- 標準ライブラリ: sqlite3, logging, argparse など

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai pyyaml

3. .env の作成:
   - 対話式で作る: python -m kabusys.config_setup
   - 生成後、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）が設定されているか確認してください。

4. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も異常扱い（exit 1）になります。

5. データディレクトリ等:
   - デフォルトでは data/ 以下に SQLite / DuckDB / PID /フラグファイル等が作成されます。必要に応じてパスは .env 内の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等で変更可能。

主な環境変数（代表）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュールで使用）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（ExecutionEngine 起動時に kill.flag を自動クリアするか。0/1、デフォルト 0）

使い方（主要コマンド）
---------------------
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV で切り替え
  - python -m kabusys.run_execution
  - ペーパートレード時は settings.is_paper により PAPER_TRADING_SQLITE_PATH を使い MockBrokerClient を利用（本番 DB と完全分離）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔変更: export MONITOR_POLL_INTERVAL=30 など

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

停止・フラグ
------------
- run_execution / ExecutionEngine 停止:
  - プロセスは data/stop_requested.flag の存在をポーリングして検知 -> 停止します（run_execution の実装）。
- Kill Switch:
  - monitoring の KillSwitch は data/kill.flag に理由テキストを書き込み、ExecutionEngine 停止を意図します。
  - ExecutionEngine 側の設定（Settings.kill_flag_path / KILL_FLAG_CLEAR_ON_START）に従って動作します。

実装上の注意点
----------------
- 設定自動読み込み: config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動ロードします。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等でテーブル作成・簡単なカラム追加マイグレーションを行います。
- AI 呼び出し: ai/news_nlp.py, ai/regime_detector.py は OpenAI API を使います。API 呼び出しはリトライやバックオフを行い、失敗時はフォールバックをする実装になっています（例: macro sentiment が取れない場合は 0.0 として続行）。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を最初に呼び出します（psutil による実装で、権限により失敗する場合はログ警告を出してスキップします）。

ディレクトリ構成
-----------------
（パッケージルート: src/kabusys 以下。代表的なファイル/モジュールを抜粋）

- src/kabusys/
  - __init__.py                  — パッケージ定義（バージョン等）
  - config.py                    — Settings クラス（環境変数のラッパー、自動 .env ロード）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（OpenAI を呼んで ai_scores を書く）
    - regime_detector.py         — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py           — （アラート送信用、実装ファイルあり）
  - execution/                    — ExecutionEngine 関連（OrderManager / BrokerFactory 等）
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
    - process_priority.py
    - __init__.py

補足
----
- この README はリポジトリ内コメント・ドキュメント文字列（docstring）を元に作成しています。実運用にあたっては各モジュールの実装・設定ファイル（config/*.yaml）や使用するブローカークライアントの詳細を確認してください。
- 本プロジェクトは取引システムであり、本番稼働時は API キーやパスワード等の管理・権限、テストと検証、十分な監視体制を事前に整えた上で実行してください。

必要であれば、README にインストール用の requirements.txt や systemd ユニット例、より詳細な運用手順（データ投入、DB の初期化、サンプル実行フロー）を追加で作成します。どの情報を優先して追加しますか？