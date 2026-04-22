# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／リサーチ基盤です。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（本番／ペーパートレード）および監視・アラート機能を備えています。DuckDB/SQLite をデータレイヤに使い、OpenAI を利用したニュース NLP / レジーム判定の統合も想定されています。

---

## 主な特徴（機能一覧）

- 発注エンジン（ExecutionEngine）
  - paper_trading 環境では MockBroker を使用し、ペーパートレード用 DB を利用して本番と完全分離
  - リスク管理・注文リコンサイル機能を内蔵
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）、プロセス生存監視、データ鮮度、注文ログ監視、リスク監視
  - kill.flag による安全停止（Kill Switch）
  - 監視ログの永続化（SQLite）
- ポートフォリオ構築（pure functions）
  - 候補選定、等金額 / スコア加重配分、リスク制限（セクターキャップ、レジーム乗数）、ポジションサイズ計算
- リサーチ（Research）
  - DuckDB を使ったファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計測、IC（Information Coefficient）計算、特徴量サマリ
- AI 統合
  - ニュース記事のセンチメントスコアリング（OpenAI）
  - マクロニュース + 指標に基づく市場レジーム判定（regime_detector）
- 運用支援ツール
  - .env 対話型ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール
- ロギング / プロセス優先度ユーティリティ
  - 統一的なログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## 前提条件

- Python 3.10 以上（型ヒントに | 記法を使用）
- システムにより追加の依存パッケージが必要:
  - duckdb
  - psutil
  - openai（AI機能を使う場合）
  - PyYAML（config 検証で YAML 内容検証を行う場合、無ければスキップされる）

（sqlite3 は標準ライブラリとして利用します）

---

## インストール（ローカル開発）

1. リポジトリをクローン／取得
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML

（プロダクションで使う場合は requirements.txt、Poetry 等で管理してください）

---

## 環境設定

本プロジェクトは .env / 環境変数で動作を制御します。起動時に自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

推奨フロー（初回セットアップ）:
1. 対話式ウィザードで .env を作成:
   - python -m kabusys.config_setup
2. 作成後、設定を検証:
   - python -m kabusys.validate_config
   - 必要なら --strict オプションで警告も失敗扱いに

重要な環境変数（抜粋）:
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development / paper_trading / live
- データベース
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- ログ / 動作
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR（ログ保存先、デフォルト: logs/）
  - PID_FILE_PATH（ExecutionEngine の pid ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（Kill Switch ファイル、デフォルト: data/kill.flag）
- OpenAI を使う場合
  - OPENAI_API_KEY

注意:
- .env は絶対にリポジトリにコミットしないでください（config_setup にも注意書きがあります）。
- KABUSYS_ENV=live の場合は設定ミスが致命的になる可能性があるため validate_config を必ず実行してください。

---

## セットアップ手順（例）

1. 仮想環境と依存のインストール（上記参照）
2. .env の作成
   - python -m kabusys.config_setup
3. 設定検証
   - python -m kabusys.validate_config
4. 必要なディレクトリを作成（もし自動で作られない場合）
   - mkdir -p data logs

---

## 使い方（起動・ツール）

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録します。
  - 実行はフォアグラウンドで動き、data/stop_requested.flag の作成で停止できます。

- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  - 監視は本番の sqlite_path を使って記録します（環境に依存しません）

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db でパス指定可能。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- プログラムからの利用例（Python REPL）
  - ポートフォリオ関数:
    - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  - Research / ファクター計算:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - AI スコアリング（OpenAI API キー必要）:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

---

## 運用・安全上の注意

- KABUSYS_ENV=live の設定は慎重に行ってください。validate_config は live 時に追加の警告を出します。
- Kill Switch（data/kill.flag）は ExecutionEngine 停止のための最重要安全機構です。本番では KILL_FLAG_CLEAR_ON_START を 0 にしてください。
- ログ・DB のディレクトリ作成権限に注意してください。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- process_priority（高優先度設定）は psutil の権限に依存します。設定に失敗しても警告が出て継続します。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルート直下の src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/Settings 管理（自動 .env ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI 連携
    - regime_detector.py     — レジーム判定（マクロ + ETF MA）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - position_sizing.py     — 株数決定・丸め・aggregate cap
  - research/
    - factor_research.py     — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py — forward return / IC / summary
  - monitoring/
    - monitoring_db.py       — SQLite のスキーマ初期化・読み書きラッパ
    - monitoring_engine.py   — 各モニタを束ねるポーリングエンジン
    - system_monitor.py      — システム状態監視
    - trade_monitor.py       — （注文ログ監視）※実装あり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — （通知管理）※実装あり
  - execution/
    - execution_engine.py    — ExecutionEngine 実体（起動・セッション管理）
    - broker_factory.py      — BrokerClient の生成（Mock / 実API）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/                    — スクリプト参照のデフォルト DB / PID / flag の場所
  - utils/
    - logging_setup.py       — ロギング設定（stdout + 日次ローテーション）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

（上記は主要モジュールの抜粋です。さらに細かい実装ファイルが含まれます）

---

## 参考コマンド一覧

- 仮想環境作成・有効化:
  - python -m venv .venv
  - source .venv/bin/activate
- 依存インストール:
  - pip install duckdb psutil openai PyYAML
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 起動（Execution / Monitoring）:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

必要であれば、README に含める具体的な環境変数一覧（デフォルト値や説明）や、systemd / Supervisor 向けの起動例、Dockerfile サンプル、requirements.txt を追記できます。どの情報を追加したいか指示してください。