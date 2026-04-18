# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ README。  
このドキュメントはコードベース（src/kabusys 以下）を元に、セットアップ／起動／主要コンポーネントの使い方をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買（本番 / ペーパートレード）・監視・リサーチ・AI（ニュース NLP / レジーム判定）機能を備えたシステムです。  
主な目的は以下：

- 戦略に基づくシグナル生成 → 発注（ExecutionEngine）
- システム稼働状況・注文状況・リスク監視（Monitoring）
- ペーパートレード結果検証レポート生成
- DuckDB を用いたファクター計算・リサーチ
- OpenAI を使ったニュースセンチメント評価・市場レジーム判定

設計上の特徴：
- 環境変数 / .env による設定管理（Settings）
- 本番・ペーパー環境の分離（PAPER_TRADING_SQLITE_PATH 等）
- ログは stdout と日次ローテートファイル（logs/<app>.log）に出力
- フェイルセーフ（API リトライ、部分失敗時の冪等書き込みなど）

---

## 機能一覧

- Execution（発注エンジン）
  - 実際のブローカー／モックブローカーでの発注
  - リスク管理（RiskManager）・オーダー管理（OrderManager）・再整合（Reconciler）
  - 起動停止フラグ（data/stop_requested.flag, data/kill.flag）による制御
- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの監視
  - TradeMonitor, RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限の監視
  - KillSwitch: 条件により ExecutionEngine に停止シグナル（kill.flag）を発行
- Research（リサーチ）
  - ファクター計算（momentum / volatility / value など）
  - 将来リターン・IC 計算・統計サマリー
- AI
  - news_nlp: OpenAI を用いたニュースのセンチメントスコア化（ai_scores テーブルへ書込み）
  - regime_detector: ETF（1321）の MA200 とマクロニュースの組合せで市場レジーム判定
- ユーティリティ
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提：
- Python 3.10+（型ヒント・Union 表記などを想定）
- 標準的な OS（Linux / macOS / Windows）で動作。プロセス優先度・CPU affinity はプラットフォーム差分を吸収します。

1. リポジトリをクローン / 取得
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   必要なパッケージ（例）：duckdb, psutil, openai, （開発用）PyYAML  
   requirements.txt がある場合はそれを使うのが便利です。ない場合の例：
   ```
   pip install duckdb psutil openai
   # optional: pip install pyyaml
   ```
   （パッケージバージョンはプロジェクトの要件に合わせてください）

4. 初期設定（.env ファイル作成）  
   対話式ウィザードで .env を生成できます：
   ```
   python -m kabusys.config_setup
   ```
   もしくは .env.example を参考に手動で作成してください。  
   主要な環境変数（必須）：
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   重要な変数（任意 / デフォルトあり）：
   - KABUSYS_ENV: development / paper_trading / live
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
   - OPENAI_API_KEY: AI 機能を使う場合必須
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方（起動・コマンド）

- ExecutionEngine（発注エンジン）を起動
  - paper_trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、ペーパー DB（data/paper_trading.db）に記録されます。
  ```
  python -m kabusys.run_execution
  ```
  注意:
  - 起動前に data/stop_requested.flag が存在すると起動せず終了します（安全措置）。
  - 実行中に data/stop_requested.flag を作成すると Engine に停止指示が送られます。

- Monitoring（監視）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルを初期化します（監視ログの永続化先は Settings.sqlite_path）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- AI 機能（ライブラリ関数として利用）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
  - これらは DuckDB 接続オブジェクト（kabusys.data.pipeline 等で得られる）と target_date, api_key を受け取ります。

停止方法（運用上）:
- 停止フラグファイル：
  - data/stop_requested.flag: run_* スクリプトの外部停止フラグ（ループを抜ける）
  - data/kill.flag: KillSwitch（監視側）から ExecutionEngine に対する停止命令（ExecutionEngine 側で検知して停止）
  - 手動でこれらを作成／削除して制御できます。起動時に KILL_FLAG_CLEAR_ON_START が `1` のとき kill.flag を自動的にクリアする設定もあります（本番では `0` 推奨）。

ログ:
- デフォルトは logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30日保持）と stdout。setup_logging をすべての起動スクリプトで呼び出しています。

---

## 主な設定項目（環境変数）

主要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能を使う場合)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定モード）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
- PID_FILE_PATH / KILL_FLAG_PATH 等のパス指定も可能

詳細は `src/kabusys/config.py` を参照してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なモジュールツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数読み込み・Settings
    - config_setup.py                # .env 対話ウィザード
    - validate_config.py             # 設定検証 CLI
    - run_execution.py               # ExecutionEngine 起動スクリプト
    - run_monitoring.py              # SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py # Paper Trading 検証レポート
    - execution/                      # 実行関連（Engine, BrokerFactory, OrderManager...）
      - ...
    - monitoring/
      - monitoring_db.py             # SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - ai/
      - news_nlp.py                  # OpenAI を使ったニュース NLP
      - regime_detector.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - utils/
      - logging_setup.py
      - process_priority.py

- config/
  - system_config.yaml (運用向けテンプレート)
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- data/   （実行時に DB やフラグが置かれる。デフォルト）
  - monitoring.db (SQLITE_PATH デフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH デフォルト)
  - kabusys.duckdb (DUCKDB_PATH デフォルト)
  - stop_requested.flag
  - kill.flag
  - execution.pid
- logs/   （ログ出力先）

---

## 運用上の注意 / 推奨

- 本番環境（KABUSYS_ENV=live）では設定値・認証情報を慎重に管理し、LINE 通知や kill_flag_clear_on_start の値を確認してください。validate_config は live 時に追加警告を出します。
- .env は決してリポジトリにコミットしないでください（config_setup も README にその旨を出力しています）。
- AI 機能を利用する場合は OPENAI_API_KEY を用意してください。API 失敗時はフェイルセーフ（0.0 等）で継続するよう設計されていますが、API レートやコストに注意してください。
- ログディレクトリに書き込めないとファイル出力が無効になり、コンソールのみの出力になります。必要に応じて LOG_DIR を設定してください。
- ペーパートレードは実際の発注を行わないため、まず paper_trading モードで十分に検証してください。

---

## 参照・補足

- 各モジュールの詳細な実装は `src/kabusys` 配下の各ファイルを参照してください（monitoring_db.py, system_monitor.py, news_nlp.py などに設計上の注釈があります）。
- config/*.yaml が必要な場合は `python -m kabusys.validate_config` でファイル存在やパースのチェックができます（PyYAML がインストールされている場合に内容をチェックします）。

----

問題や補足したい点があれば、利用シーン（ローカル検証 / 本番導入 / CI 用など）を教えてください。必要に応じて起動例や運用手順をさらに具体化します。