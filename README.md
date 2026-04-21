# KabuSys

日本株自動売買システムのコードベース（README 日本語版）

## プロジェクト概要
KabuSys は日本株向けの自動売買・研究・監視ツール群です。  
主な機能群は以下のとおりです。

- Execution Engine: 発注・オーダー管理・リスク管理（本番 / ペーパートレード対応）
- Monitoring: システム健康、注文・リスクの監視と Kill Switch
- Research: DuckDB を使ったファクター計算・特徴量解析
- AI モジュール: OpenAI を利用したニュースの NLP スコアリング / 市場レジーム判定
- Portfolio モジュール: 候補選定・重み計算・ポジションサイズ計算
- CLI ツール: .env 作成ウィザード、設定検証、ペーパートレード検証レポート 等

この README は、利用開始までのセットアップ、主要機能の使い方、ディレクトリ構成の説明を含みます。

---

## 機能一覧（抜粋）
- config 管理
  - .env の自動読み込み（.env / .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行（Execution）
  - run_execution: ExecutionEngine 起動スクリプト
  - paper_trading モードでは MockBroker を使用し DB を分離（data/paper_trading.db）
  - PID ファイル管理、停止フラグ監視
- 監視（Monitoring）
  - run_monitoring: SystemMonitor のポーリングループ起動
  - system / trade / risk の各モニター、監視 DB（SQLite）永続化
  - Kill Switch（data/kill.flag）で ExecutionEngine を安全に停止
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒）
- AI
  - news_nlp.score_news: raw_news から LLM により銘柄別センチメント（ai_scores テーブルへ挿入）
  - regime_detector.score_regime: MA とマクロニュースの組合せで日次レジーム判定
  - OpenAI（gpt-4o-mini）を利用。OPENAI_API_KEY 必須（AI 機能利用時）
- Research & Portfolio
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン / IC 計算 / ファクター統計
  - ポートフォリオ構築（候補選定・重み計算）・ポジションサイズ算出（単元丸め等）
- ツール
  - kabusys.tools.paper_verification_report: ペーパートレード検証レポート生成（期間指定可）

---

## 必要条件（推奨）
- Python 3.10+
  - typing の |（Union 簡略記法）などを使用しているため 3.10 以上を推奨します
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（config YAML の検証を行う場合）
- 推奨インストール例:
  - pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
   - プロジェクトルートに `src/` と `.env` 等が配置されている想定です。

2. Python 環境準備
   - 仮想環境推奨:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - 必要パッケージをインストール:
     - pip install duckdb psutil openai pyyaml

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成
   - 自動ロード:
     - kabusys.config ではプロジェクトルートの `.env` と `.env.local` を自動で読み込みます（環境変数が優先）。
     - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - OPENAI_API_KEY （AI 機能を使う場合）
   - 他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL などはオプションまたはデフォルトあり

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を指定すると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルト DB/ログファイル等は `data/` や `logs/` に置かれます。必要に応じてディレクトリを作成してください。

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動（本番/ペーパー共通スクリプト）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）へ記録します。
    - 起動時に `data/stop_requested.flag` が存在すると起動しません。
    - プロセス停止は stop flag 書き込み（stop_requested.flag）や kill.flag による制御があります。

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使います（monitoring は環境にかかわらず本番 sqlite_path を使用）。

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱い

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラム上で呼び出す）
  - ニュース NLP（銘柄ごとスコア付け）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - これらは OPENAI_API_KEY（または引数で api_key）を必要とします。モデルは gpt-4o-mini を想定。

---

## 主要設定項目（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）
- OPENAI_API_KEY: OpenAI を使う場合に必要

---

## ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging によって統一管理されます。
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: execution.log, monitoring.log）
- 日次ローテーション（30 日分保持）

---

## 注意点 / 運用上のヒント
- Monitoring は監視用 SQLite を常に本番 sqlite_path で開く設計になっています（環境変数に関係なく）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使って本番データと分離します。
- Kill Switch（kill.flag）は Settings.kill_flag_path（デフォルト data/kill.flag）に書き込むことで ExecutionEngine に停止信号を与えます。運用時は kill_flag_clear_on_start の設定を慎重に（本番では 0 推奨）。
- AI 機能は外部 API（OpenAI）へ依存するため、API レート制限やネットワークエラーを考慮した設計（リトライ・フェイルセーフ）が組み込まれています。ただし API キー管理やコストは運用者の責任です。
- DuckDB / prices_daily / raw_financials 等のテーブルは research/ai の関数が参照します。これらのテーブルを用意してから実行してください。

---

## ディレクトリ構成（主なファイル）
以下は `src/kabusys` 以下の主なファイル／モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照される)
    - kill_switch.py
    - alert_manager.py (参照される)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py (参照される)
    - stats.py (参照される)
  - ai/
    - news_nlp.py
    - regime_detector.py

（上記は実装済みの主要モジュールを示しています。プロジェクトの全ファイルを見る場合はリポジトリツリーを参照してください。）

---

## よく使うコマンド例

- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視起動（ポーリング間隔を 30 秒に設定）:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア（プログラム内呼び出し）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="・・・")

---

## ライセンス・貢献
（ここではライセンスやコントリビュートルールを必要に応じて追記してください）

---

README に含めるべき追加の情報（例: requirements.txt の位置、CI/CD の使い方、運用手順書等）があれば教えてください。必要に応じて追記・詳細化します。