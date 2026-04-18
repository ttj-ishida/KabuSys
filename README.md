# KabuSys

日本株向け自動売買 / 研究プラットフォームの軽量コアライブラリ群です。  
本リポジトリは、発注エンジン（ExecutionEngine）、監視サブシステム、ポートフォリオ構築、ファクター計算、LLM を用いたニュースセンチメント／レジーム判定、各種ユーティリティを含みます。

主な設計方針
- 本番・ペーパートレードを環境変数で切替可能（KABUSYS_ENV）
- DuckDB を用いた分析・研究、SQLite を監視ログ / 発注ログに利用
- OpenAI（gpt-4o-mini 等）を使ったニュース評価機能（API キー必要）
- .env ベースの設定管理（config_setup.py による対話式ウィザード）
- ログは stdout + 日次ローテーションファイルで管理

---

## 主な機能一覧
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV により paper_trading 切替）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前の設定検証 CLI（--strict オプションあり）
  - config.py — Settings クラスで環境変数を一元管理・自動読み込み
- モニタリング
  - monitoring_db.py — SQLite 監視 DB スキーマと永続化ロジック
  - system_monitor.py / trade_monitor.py / risk_monitor.py / monitoring_engine.py — 各種監視ロジック（Kill Switch 含む）
  - kill_switch.py — フラグファイルを書いて ExecutionEngine を停止する仕組み
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定、重み計算、株数算出、セクター制約、レジーム乗数
- 研究 / ファクター計算
  - research/factor_research.py — Momentum / Value / Volatility 等のファクター計算（DuckDB 接続を受ける）
  - research/feature_exploration.py — 将来リターン計算、IC 計算、統計サマリ
- AI（LLM）連携
  - ai/news_nlp.py — ニュース記事のセンチメントスコアリング（OpenAI API 経由）
  - ai/regime_detector.py — マクロセンチメントと ETF MA を合成して市場レジーム判定、DB 書き込み
- ユーティリティ
  - utils/logging_setup.py — 統一ログ設定（stdout + TimedRotatingFileHandler）
  - utils/process_priority.py — プラットフォーム非依存のプロセス優先度設定
- ツール
  - tools/paper_verification_report.py — Paper Trading 検証レポート生成（発注・稼働率・レイテンシ等）

---

## 前提 / 推奨環境
- Python 3.10+
- 必要な Python パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時、任意）
- SQLite は標準ライブラリで利用
- 環境変数 / .env による設定管理を想定

例（仮想環境作成・依存関係のインストール）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードが .env を生成します。機微データ（API トークン等）は絶対に Git にコミットしないでください。

4. 設定検証（起動前に必ず実行）
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリの準備（自動作成されるケースが多いですが手動で作ることも可能）
   ```bash
   mkdir -p data logs
   ```

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（J-Quants API 用）
- KABU_API_PASSWORD（kabuステーション API 用）
- OPENAI_API_KEY（AI 機能を使う場合）
オプション / 重要な環境変数
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（DEBUG/INFO/...）
- LOG_DIR（ログ出力先。デフォルト: logs/）

.env 自動ロード
- 起動時にプロジェクトルート（.git または pyproject.toml を探索）から .env を自動読み込みします。
- 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要コマンド）

- ExecutionEngine を起動
  - 本番/ペーパートレードは KABUSYS_ENV に依存
  ```bash
  python -m kabusys.run_execution
  ```

  ペーパートレード用に明示的に設定する例:
  ```bash
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Monitoring を起動（ポーリング監視）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）でオーバーライド可能。デフォルト 60 秒。
  ```bash
  python -m kabusys.run_monitoring
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- 研究用関数の呼び出し（Python REPL / スクリプト内）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 4, 10))
  ```

- AI ベースのスコアリング（プログラムから）
  ```python
  from kabusys.ai import score_news
  # DuckDB 接続を渡し、target_date と API キーを指定
  score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
  ```

注意点
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
- Kill Switch（data/kill.flag）や停止フラグ（data/stop_requested.flag）を用いてプロセス停止が可能です。
- 起動時にプロセス優先度を "high" にセットします（set_process_priority）。

---

## 主要モジュール説明（概要）

- kabusys.config
  - Settings クラスで環境変数をラップ。自動 .env ロード、型変換、値検証を行う。
- kabusys.utils.logging_setup
  - アプリ全体のログ出力を統一（stdout + 日次ローテーション）。
- kabusys.utils.process_priority
  - Windows / POSIX を吸収したプロセス優先度／CPU affinity 設定。
- kabusys.monitoring
  - monitoring_db.py: SQLite スキーマ初期化 / CRUD
  - system_monitor.py: CPU/メモリ/Disk/データ鮮度/実行プロセス監視
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: フラグ書き込みによる安全停止
  - monitoring_engine.py: 各 Monitor を束ねるループ
- kabusys.execution (エンジン関連)
  - BrokerFactory、ExecutionEngine、OrderManager 等（発注ロジック）
- kabusys.portfolio
  - 候補選定、重み計算、株数決定、セクター制約、レジーム乗数
- kabusys.research
  - DuckDB を利用したファクター計算・特徴量解析
- kabusys.ai
  - news_nlp.py: ニュース→センチメント（OpenAI）
  - regime_detector.py: ETF MA + マクロニュース合成→レジーム判定
- kabusys.tools
  - paper_verification_report.py: ペーパートレード検証レポート

---

## ディレクトリ構成
（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - monitoring_engine.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py (参照あり)
  - execution/
    - (ExecutionEngine, broker_factory, order_manager 等)
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
  - tools/
    - paper_verification_report.py

プロジェクトルートには以下のようなディレクトリ・ファイルが想定されます:
- .env (機密、Git にはコミットしない)
- data/ (SQLite DB, pid/flag ファイル)
  - monitoring.db
  - paper_trading.db
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/ (ログファイル)
- config/
  - 各種 YAML 設定テンプレート（system_config.yaml 等）

---

## トラブルシューティング / よくある注意点
- .env 未設定で起動すると必須変数が欠けるため validate_config による事前チェックを行ってください。
- OpenAI API 呼び出しはネットワーク障害・レート制限等を考慮したリトライ実装がありますが、API キー・料金管理には注意してください。
- DuckDB / SQLite のパスは環境変数で指定できます（開発・本番で分離してください）。
- run_monitoring は常に本番用の sqlite_path（monitoring DB）を参照します（監視ログは環境を跨っても一貫して本番 DB を使用する仕様）。

---

README はここまでです。追加で「インストール用 requirements.txt を作る」「各コンポーネントの設計ドキュメント（UML/Sequence）」や、特定モジュールの詳しい API 仕様（関数引数・戻り値のサンプル）を作成することも可能です。必要があれば教えてください。