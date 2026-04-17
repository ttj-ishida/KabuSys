# KabuSys

日本株向けの自動売買システム（簡易版）。  
取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、LLM を用いたニュース NLP / レジーム判定などのコンポーネントを含みます。

注意: このリポジトリは学習・開発用途を想定しています。本番稼働させる場合はリスク管理・セキュリティ・法令遵守等を十分に確認してください。

## 概要

- 発注ロジック（ExecutionEngine）とそれを監視する Monitoring コンポーネントを持つ。
- Paper Trading モードをサポートし、本番 DB と分離して動作可能（MockBrokerClient を使用）。
- ニュースのセンチメント評価や市場レジーム判定に OpenAI（gpt-4o-mini 等）を利用できる（APIキー必須）。
- DuckDB を分析用途の時系列データに、SQLite を監視・注文ログやペーパートレード記録に使用する。
- 設定ウィザード・検証ツール、ペーパートレード検証レポート生成ツールを提供。

## 主な機能（抜粋）

- Execution
  - ExecutionEngine（発注処理、リスク管理、オーダー管理、リコンシリエーション）
  - Paper Trading モード（環境変数により MockBrokerClient を使用）
- Monitoring
  - SystemMonitor（プロセス死活、CPU/メモリ/ディスク、データ鮮度）
  - TradeMonitor（滞留注文、約定価格の異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件を満たしたら stop flag を書き込み、エンジン停止）
  - MonitoringEngine（各 Monitor を束ねてポーリング）
- Portfolio
  - 候補選定、重み付け、単位株丸め、リスク調整（セクター制限、レジーム乗数）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索、IC 計算、統計サマリー
- AI
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores テーブルに書込み
  - regime_detector: ETF の MA とマクロニュースの LLM 評価を合成して市場レジームを判定
- Tools
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

## 必要要件

- Python 3.9+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- 標準ライブラリ: sqlite3, logging, pathlib など

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai PyYAML
```

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化し、依存をインストール（上記参照）

3. .env の初期作成（ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成します（デフォルト: プロジェクトルートの .env）。機密トークンは表示されずマスクされます。

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL としたければ:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリを作成（必要に応じて）
   デフォルト DB パスは以下（すべて relative path）:
   - DuckDB: data/kabusys.duckdb
   - Monitoring SQLite: data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db

   例:
   ```bash
   mkdir -p data
   ```

6. OpenAI を使う機能を使用する場合は環境変数 OPENAI_API_KEY を設定。

## 使い方（起動コマンド）

- ExecutionEngine を起動（デフォルト環境に従う）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading.db に記録します（本番 DB と完全分離）。
  - 起動時にプロセス優先度を high に設定します。
  - 起動前に data/stop_requested.flag が存在すると起動しません。

- Monitoring（ポーリング監視）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを保存します。

- .env ウィザード（再実行・更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポートの生成
  ```bash
  # デフォルト DB (data/paper_trading.db)
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パスを直接指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- OpenAI を使った機能（プログラム的に呼び出す例）
  - ニューススコアリング:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,12), api_key="sk-xxx")
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,12), api_key="sk-xxx")
    ```

## 主要な環境変数（よく使うもの）

- KABUSYS_ENV: execution モード（development / paper_trading / live）. デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant, partial, never, reject。デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch のフラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするフラグ（0/1、デフォルト 0。本番では 0 推奨）

.env ウィザードを使うと主要項目を対話式に作成できます。

## 停止・Kill フロー

- 実行中の ExecutionEngine / Monitoring の停止はプロジェクト内に配置される stop/kill フラグファイルで制御します。
  - run_execution/run_monitoring はそれぞれ data/stop_requested.flag（あるいはプロジェクトルートの data 以下）を監視して安全シャットダウンします。
  - KillSwitch は条件を満たした際に KILL_FLAG_PATH（デフォルト data/kill.flag）に理由を書き込み、ExecutionEngine に停止を促します。

## 注意事項 / 運用メモ

- Monitoring は常に（KABUSYS_ENV に関わらず）本番 sqlite_path を使用して監視ログを残します。
- Paper Trading は本番 DB と分離して動作するため、KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用します。
- OpenAI を利用する機能は API 呼び出しで失敗した場合にフォールバック（例: スコア 0 やスキップ）するよう設計されていますが、API キー管理には十分注意してください。
- process priority / CPU affinity 設定は psutil を使用します。権限不足時は警告が出てスキップされます。
- データベースマイグレーション（monitoring_db のカラム追加等）はアプリ起動時に簡易的な ALTER を行いますが、複雑なマイグレーションが必要な場合は手動で対応してください。

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル構成は以下の通りです。

```
src/
  kabusys/
    __init__.py
    config.py                   # 環境変数読み込み・Settings
    config_setup.py             # .env 対話ウィザード
    validate_config.py          # 設定検証 CLI
    run_execution.py            # ExecutionEngine 起動スクリプト
    run_monitoring.py           # Monitoring 起動スクリプト

    execution/                  # 発注エンジン関連（OrderManager 等）
      ...
    monitoring/                 # 監視関連
      monitoring_db.py
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      ...
    portfolio/                  # ポートフォリオ構築（選定・重み・サイズ計算）
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/                   # ファクター計算・リサーチ
      factor_research.py
      feature_exploration.py
    ai/                         # LLM 関連（ニュース NLP、レジーム判定）
      news_nlp.py
      regime_detector.py
    tools/
      paper_verification_report.py
    utils/
      process_priority.py
    data/                       # 実行時に使用する DB 等（デフォルト: data/*.db）
```

（実際のサブディレクトリ内に更に多くのモジュールがあります。上記は主要ファイルの抜粋です。）

## 開発 / デバッグのヒント

- 設定の自動読み込み:
  - プロジェクトルートにある `.env`/.env.local は自動でロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効）。
  - config_setup.py で .env を生成した後、validate_config で検証するのが推奨フローです。
- Logging:
  - 各スクリプトは logging.basicConfig(level=INFO) をベースにしているため、環境変数 LOG_LEVEL=DEBUG 等で詳細ログを得られます。
- テストやユニットテストを書く際は、環境変数や .env の操作、DB パスを分離して実行してください（PAPER_TRADING_SQLITE_PATH を使うと本番 DB を汚しません）。

---

README は開発者の最小限のガイドです。詳細な設計やアルゴリズム仕様（ポートフォリオ構築、戦略モデル、Execution の内部等）はリポジトリ内の doc/ または各モジュールの docstring を参照してください。質問や追加のドキュメント化が必要であれば教えてください。