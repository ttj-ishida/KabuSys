# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリ群です。戦略・ポートフォリオ構築、実行エンジン、監視・アラート、研究用ファクター計算、AI を使ったニュース解析など、運用に必要な主要コンポーネントを含みます。

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要項目）
- 停止 / Kill Switch の仕組み
- ディレクトリ構成（主要ファイル説明）
- テスト / 開発時のヒント

---

## プロジェクト概要

KabuSys は、取引所 API（kabuステーション 等）や外部データ（J-Quants、ニュース）を組み合わせて日本株の自動売買を行うためのモジュール群です。設計方針としては以下を重視しています。

- 本番・ペーパートレード（paper_trading）・開発（development）の環境切替
- DB（SQLite / DuckDB）を用いたデータ永続化と分析
- 監視（Monitoring）機能による自動停止（Kill Switch）とアラート
- AI（OpenAI）を用いたニュースセンチメントやマクロ判定（オプション）
- 解析・研究（Research）用のファクター計算ユーティリティ

---

## 主な機能

- ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - 本番/ペーパーの切替。paper_trading 時は MockBroker を使用し専用 DB に記録。
- Monitoring（run_monitoring.py）
  - システム状態、注文滞留、リスク（ドローダウン等）を定期ポーリングしてログ保存・アラート発行。
- Config ウィザード（config_setup.py） & 設定検証（validate_config.py）
  - .env の対話的生成 / 設定検証ツール。
- Portfolio モジュール
  - 候補選定、重み付け、ポジションサイズ計算、セクター上限やレジーム調整。
- Research モジュール
  - ファクター計算（Momentum/Value/Volatility 等）、将来リターン、IC 計算、統計要約。
- AI モジュール（任意）
  - news_nlp: OpenAI を用いたニュースセンチメント評価 → ai_scores 書込
  - regime_detector: MA およびマクロニュースを使った市場レジーム判定
- Tools
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを出力

---

## 前提条件

- Python 3.9+
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
  - PyYAML（validate_config の YAML 検証を行う場合に任意）
- SQLite は標準で利用可能

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
# または requirements.txt があれば pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を準備する。
2. 必要パッケージをインストール（上記参照）。
3. .env の準備（対話ウィザード推奨）:
   ```
   python -m kabusys.config_setup
   ```
   - これによりプロジェクトルートに `.env` が作成されます（出力先は指定可）。
4. 設定の妥当性チェック:
   ```
   python -m kabusys.validate_config
   # 警告も失敗にする場合:
   python -m kabusys.validate_config --strict
   ```
5. DB ファイル（デフォルトは data/ 配下）を作成・配置する。DuckDB / SQLite ファイルは必要に応じて初期データを投入してください。
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - 注意:
    - KABUSYS_ENV 環境変数により動作モードが変わります。
    - paper_trading の場合、MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動時に data/execution.pid が作成されます（pid ファイルのパスは Settings.pid_file_path で上書き可）。
    - 起動直後に data/stop_requested.flag が存在する場合は起動せず終了します。

- Monitoring 起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で変更可能（デフォルト 60 秒）。
  - 監視は monitoring DB（Settings.sqlite_path）へ書き込み、KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。
  - ループを停止させるにはプロジェクトルートの data/stop_requested.flag を作成するか、Ctrl+C。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで別の DB を指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定できます。

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーを設定:
    ```
    export OPENAI_API_KEY="sk-..."
    ```
  - news_nlp.score_news / regime_detector.score_regime を呼ぶ（スクリプト呼び出しのラッパーは用意されていませんが、モジュール API を利用できます）。
  - 失敗時はフェイルセーフ設計により致命的にはならない実装になっていますが、API キーは必須です。

---

## 主要な環境変数

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant | partial | never | reject）
- OPENAI_API_KEY: OpenAI を利用する場合に必須
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ...）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill Switch の flag ファイルパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で消すか（"1" で有効、開発用）

---

## 停止 / Kill Switch の仕組み

- 強制停止フラグ（ExecutionEngine 停止）
  - Kill Switch: `data/kill.flag` を書き込むことで ExecutionEngine に対する停止要求（Kill）を送信します。
  - KillSwitch は監視モジュール（RiskMonitor 等）の評価結果に応じて `kill.flag` を作成します。
  - ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると自動的に kill.flag を削除します（本番環境では 0 推奨）。

- 監視・停止フラグ（run_* スクリプトの自停止）
  - `data/stop_requested.flag` が存在すると、run_monitoring / run_execution のポーリングループは検知して終了します。外部からの安全なシャットダウンに使えます。

---

## ディレクトリ構成（主要ファイル説明）

（リポジトリの `src/kabusys` 配下を想定）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス。.env 自動読み込み機構あり。
  - config_setup.py
    - .env 対話的ウィザード（python -m kabusys.config_setup）
  - validate_config.py
    - 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（発注エンジン）。paper_trading の DB 分離等を実施。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔調整可能。
  - utils/
    - process_priority.py
      - プロセス優先度（nice / Windows priority）と CPU affinity 設定ユーティリティ。
  - execution/  (発注関連: Engine, OrderManager, BrokerFactory 等)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py, order_record.py, ...
  - monitoring/
    - monitoring_db.py
      - SQLite を使った監視ログ永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
      - CPU/メモリ/ディスク/プロセス・データ鮮度をチェックする Monitor
    - trade_monitor.py
      - 注文の滞留・約定異常価格の検出
    - risk_monitor.py
      - ドローダウン・ポジション上限の監視と Dashboard 更新
    - kill_switch.py
      - flag ファイルに基づく ExecutionEngine 停止ロジック
    - monitoring_engine.py
      - 各 Monitor を束ねて定期実行・アラート判定を行う
    - alert_manager.py
      - アラート送信（LINE 等）を担う（実装に依存）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - （ポートフォリオ構築・ウェイト計算・リスク制御）
  - research/
    - factor_research.py
    - feature_exploration.py
    - （DuckDB ベースのファクター計算・IC・統計）
  - ai/
    - news_nlp.py
      - ニュースの LLM ベースセンチメント集計（ai_scores へ書込）
    - regime_detector.py
      - ETF MA とマクロニュース LLM を組合せた市場レジーム判定
  - tools/
    - paper_verification_report.py
      - ペーパートレード DB を集計して検証レポートを出力

---

## 開発時のヒント / 注意点

- .env を決してリポジトリにコミットしないでください（config_setup のヘッダにも記載）。
- validate_config は必須環境変数の未設定やパスの不整合を事前検出できます。運用前に必ず実行してください。
- OpenAI を使う機能は API コストが発生します。ローカルテスト時はモック（unittest.mock）で外部呼び出しを差し替えることを推奨します。
- Monitoring の DB マイグレーション処理は簡易的に行われます（カラム追加等）。手動での DB 管理が必要な場面では注意してください。
- run_execution / run_monitoring は process priority を高める処理を行います（psutil を使用）。権限やプラットフォームにより失敗する場合は警告になります。

---

README の補足・変更など希望があれば教えてください。必要であれば、各サブモジュール（execution, monitoring, ai, research）のより詳細なドキュメント（API 仕様、関数例、絵やフロー図）も作成します。