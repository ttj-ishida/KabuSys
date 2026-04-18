README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究基盤を目的とした Python パッケージです。  
戦略のファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、ニュース NLP によるセンチメントスコアリング、レポート生成等のコンポーネントを含みます。

特徴（機能一覧）
----------------
- ExecutionEngine（実際の発注またはペーパートレード）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB に記録して本番 DB と分離
  - リスク管理（ポジション上限・ドローダウン等）
  - 発注履歴の永続化
- Monitoring（システム状態・注文状態・リスク監視）
  - CPU/メモリ/ディスク監視、データ鮮度チェック、滞留注文・約定異常等の検出
  - Kill Switch（条件を満たすと data/kill.flag を書き込んで Execution を停止）
  - ポーリングループ（間隔は MONITOR_POLL_INTERVAL で上書き可、デフォルト 60 秒）
- Portfolio（銘柄選定・重み計算・ポジションサイズ計算）
  - 等配分、スコア加重、リスクベース配分、セクター上限、レジーム乗数など
- Research（DuckDB を用いたファクター計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算
  - forward returns、IC（Information Coefficient）、統計サマリ
- AI（ニュース NLP / 市場レジーム判定）
  - OpenAI (gpt-4o-mini) を用いたニュースセンチメント、マクロセンチメントでレジーム判定
  - バッチ処理・リトライ・レスポンスバリデーションを実装
- ツール
  - Paper Trading の検証レポート生成スクリプト（paper_verification_report）
- 設定ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup）
  - 起動前チェック（validate_config）


前提条件 / 依存ライブラリ
-------------------------
主な依存（最低限）
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config/*.yaml の内容検証を行う場合）

インストール例（仮想環境を推奨）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージのインストール（例）
  - pip install duckdb psutil openai pyyaml

（注）requirements.txt は本リポジトリに含まれていないため、プロジェクトで使うパッケージを必要に応じて用意してください。


環境設定 (.env)
----------------
- 本プロジェクトは .env/.env.local から環境変数を自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化）。
- 読み込み優先順位:
  1. OS 環境変数（既存の環境変数は上書きされません）
  2. .env.local（存在すれば .env の値を上書き）
  3. .env
- 推奨: .env は絶対に Git にコミットしないでください。

主な環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading: 発注はモック。paper_trading 用 DB に記録。
  - live: 本番
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB, デフォルト: data/paper_trading.db)
- LOG_LEVEL (例: INFO, DEBUG)
- LOG_DIR (ログ出力先ディレクトリ、デフォルト: logs/)
- MONITOR_POLL_INTERVAL (監視ループのポーリング間隔秒、デフォルト: 60)
- PAPER_FILL_MODE (ペーパートレードの約定モード: instant | partial | never | reject)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)


セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. .env を作成
   - 対話式ウィザードを利用: python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い: python -m kabusys.validate_config --strict


使い方（主要スクリプト）
-----------------------

設定ウィザード
- python -m kabusys.config_setup
  - 対話式に .env を作成 / 更新します。

設定検証
- python -m kabusys.validate_config
  - .env と config/*.yaml の基本チェックを行います。
  - PyYAML が無ければ YAML の検証はスキップします。

ExecutionEngine（発注エンジン）起動
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録し、MockBrokerClient を使用します。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動しません。
  - 停止シグナル: data/stop_requested.flag を作成するとエンジンは安全に停止します。
  - 実行中は data/execution.pid が利用されます。

Monitoring（監視）起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト: 60 秒）
  - Monitoring は環境にかかわらず本番の sqlite_path を使用して監視ログを記録します（設計上の注意）
  - 停止シグナル: data/stop_requested.flag を作成すると監視ループを終了します。

Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数か --db で DB を指定できます。
  - 出力: 稼働率、注文成功率、レイテンシ、判定（PASS/FAIL）

AI 関連（ニュース NLP / レジーム判定）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と target_date を与えてニュースセンチメントを ai_scores に書き込みます。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 1321 の MA200 乖離とマクロニュースの LLM スコアを合成し market_regime テーブルに書き込みます。

Kill Switch / 停止フラグ
- KillSwitch はリスク条件（ドローダウン超過・ポジション数上限等）を満たすと data/kill.flag に理由文字列を書き込みます。
- Execution 側は kill.flag を検知して安全停止するように設計されています（KILL_FLAG_CLEAR_ON_START により起動時の自動クリアが可能）。

ログ
---
- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日分保持）に出力されます。
- LOG_DIR 環境変数でログディレクトリを指定できます。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で設定できます。

運用上の注意
-------------
- .env は機微な情報（APIキー等）を含むため絶対にリポジトリにコミットしないこと。
- KABUSYS_ENV=live 設定時は特に注意深く設定を検証してください（validate_config の警告や LINE 通知設定等）。
- Monitoring は監視用 DB に対して本番 sqlite_path を使います（環境に依らず）。paper_trading と実 DB を完全に分離したい場合は設定を確認してください。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼び出します。環境によっては権限不足で変更できない場合があります（警告ログのみ）。

ディレクトリ構成（概要）
----------------------
以下は主なモジュールと簡単な説明です（src/kabusys 以下）:

- __init__.py
  - パッケージのバージョン等

- config.py
  - 環境変数読み込み・Settings クラス（.env 自動読み込みロジック含む）

- config_setup.py
  - .env を対話式に生成するウィザード

- validate_config.py
  - 起動前設定チェック CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト

- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - 発注エンジン関連の実装

- monitoring/
  - monitoring_db.py      : SQLite による監視ログ永続化
  - system_monitor.py      : CPU/メモリ/データ鮮度監視
  - trade_monitor.py       : 発注ログ監視（滞留注文・異常約定等）
  - risk_monitor.py        : ドローダウン・ポジション上限監視
  - kill_switch.py         : kill.flag の作成/管理
  - alert_manager.py       : アラート送信（LINE 等を想定）
  - monitoring_engine.py   : 各モニタを束ねる実行ループ

- portfolio/
  - portfolio_builder.py   : 候補選定・重み算出
  - position_sizing.py     : 株数算出（リスク制限・単元丸め）
  - risk_adjustment.py     : セクター上限・レジーム乗数

- research/
  - factor_research.py     : Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py : forward return / IC / summary

- ai/
  - news_nlp.py            : ニュースセンチメント集計（OpenAI 経由）
  - regime_detector.py     : マクロ + ETF MA によるレジーム判定

- tools/
  - paper_verification_report.py : ペーパートレード検証レポート生成スクリプト

- utils/
  - logging_setup.py       : 統一的ログ設定ユーティリティ
  - process_priority.py    : プロセス優先度・CPU affinity 設定ヘルパ

- data/ (実行時に作成される想定)
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kill.flag, stop_requested.flag, execution.pid 等の制御ファイル

補足（代表的なコマンド例）
-------------------------
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動（デフォルト environment に従う）:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
（この README にはライセンス情報は含まれていません。プロジェクトに対応する LICENSE ファイルを参照してください。）

お問い合わせ / 開発
-------------------
設計方針や各関数のドキュメントはソース内の docstring を参照してください。開発時はユニットテストや validate_config を活用して設定ミスを早期に検出してください。

以上。README に記載してほしい追加情報や特定のコマンド例があれば教えてください。