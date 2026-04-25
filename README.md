# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買／リサーチ／監視を目的としたモジュール群です。  
主要コンポーネントは実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI）などで構成されています。

---

## 概要（Project Overview）

- 自動売買の実行・発注ロジックとリスク管理を分離して実装
- 監視コンポーネントでシステム稼働状況・注文状態・リスク指標を定期チェック
- DuckDB（分析データ）と SQLite（監視・トレードログ）をデータストアとして併用
- Paper Trading モードをサポートし、本番 DB と完全に分離可能
- ニュースセンチメントやレジーム判定に OpenAI を利用する拡張機能あり（API キー必須）
- 設定ウィザード・検証 CLI を備え、.env / config/*.yaml の検証が可能

---

## 機能一覧（Features）

- Execution
  - 実際のブローカー／モックブローカーを抽象化して ExecutionEngine を起動
  - Paper Trading 時は mock クライアントと専用 SQLite（data/paper_trading.db）を使用
  - PID ファイル（data/execution.pid）管理、停止フラグ検知（data/stop_requested.flag）
- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、Execution プロセス状態、データ鮮度の監視
  - TradeMonitor：注文滞留や約定異常チェック（trade_logs を参照）
  - RiskMonitor：ドローダウン、ポジション上限の監視とリスクログ記録
  - KillSwitch：条件に応じて data/kill.flag を書き込み、Execution を停止させる
  - MonitoringEngine：各 Monitor の束ねとアラート送信（AlertManager 経由）
- Portfolio / Position sizing
  - 候補銘柄選定、等金額／スコア加重、リスクベース配分、単元株処理、セクターキャップ等
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）
  - news_nlp.score_news：ニュース記事を LLM でセンチメント評価して ai_scores に格納
  - regime_detector.score_regime：ETF MA とマクロニュースを合成して市場レジーム判定
- ツール
  - 設定ウィザード（python -m kabusys.config_setup）で .env を対話的に作成
  - 設定検証（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 必要環境・依存パッケージ（Dependencies）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - psutil
  - openai
- 任意（検証機能）
  - PyYAML（config/*.yaml の検証に使用）
- これらは適宜 requirements.txt を作成して管理してください。

例：
```
pip install duckdb psutil openai PyYAML
```

---

## 初期セットアップ手順（Setup）

1. リポジトリをクローンして Python 仮想環境を準備
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt  # または上記パッケージを個別にインストール
   ```

2. 対話式ウィザードで .env を作成（推奨）
   ```
   python -m kabusys.config_setup
   ```
   - J-Quants トークン、kabu API パスワード、データベースパス等を設定できます。
   - .env は絶対に Git にコミットしないでください。

3. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリ（デフォルト）
   - DuckDB: data/kabusys.duckdb
   - Monitoring(SQLite): data/monitoring.db
   - Paper trading DB: data/paper_trading.db
   - ログ: logs/
   - PID/フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag

必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_DIR を変更してください。

---

## 使い方（Usage）

- 実行エンジン（ExecutionEngine）を起動
  - 本番 / 開発 / ペーパーは KABUSYS_ENV によって切替
  - Paper Trading の場合、設定された PAPER_TRADING_SQLITE_PATH に書き込まれる
  ```
  # 環境例: .env で KABUSYS_ENV を設定しておく
  python -m kabusys.run_execution
  ```
  - 起動中に data/stop_requested.flag を作成すると安全に停止します（監視スクリプトや外部オペレータが使用）
  - paper_trading モードでは MockBrokerClient が使われ、本番 DB と分離されます

- 監視プロセス（Monitoring）を起動
  ```
  # ポーリング間隔を秒で上書き（デフォルト 60 秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 監視は常に（KABUSYS_ENV に関わらず）Settings.sqlite_path（デフォルト data/monitoring.db）を使用します
  - stop フラグファイル（data/stop_requested.flag）でループを終了します

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # またはデフォルト DB を上書き:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
  - 例（Python から呼ぶ）:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, date(2026, 4, 11), api_key="sk-...")
    ```

- 設定自動読み込みの無効化（テスト用）
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 重要な環境変数（主要なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR（ログ保存先、デフォルト: logs/）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（本番での Kill フラグ自動クリア制御）

（config_setup.py に .env 作成用の全項目が定義されています）

---

## 停止・Kill Switch / フラグの挙動

- data/stop_requested.flag
  - run_monitoring および run_execution はこのファイルの存在を見て安全に停止します（外部からの停止指示用）
- data/kill.flag
  - KillSwitch（監視）を通じて書き込まれ、ExecutionEngine に対する強制停止指示として利用されます
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされる（本番は 0 推奨）

---

## ディレクトリ構成（Directory Structure）

以下は主要なファイル／パッケージの概要です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数・設定読み込みロジック
  - config_setup.py             — 対話式 .env ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading レポート生成ツール
  - execution/                  — 発注エンジン・OrderManager 等（主要ロジック）
  - monitoring/
    - monitoring_db.py          — SQLite 永続化ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                       — 実行時生成の DB / フラグ / PID（デフォルト）
  - logs/                       — ログファイル出力先（デフォルト）

---

## 開発上の注意点・運用メモ

- データベース（DuckDB / SQLite）はファイルベースなのでバックアップや権限に注意してください。
- 本番環境（KABUSYS_ENV=live）での設定は慎重に行ってください（validate_config は live 時に警告を出します）。
- OpenAI を使う処理は API コストとレート制限に注意し、API キー管理は厳重に行ってください。
- logging_setup はデフォルトで stdout と日次ローテートファイル logging を設定します。LOG_DIR を適切に設定してください。
- process_priority で優先度設定を行いますが、OS により失敗する場合があります（権限不足など）。

---

この README は現状のコードベース（src/kabusys）をもとにした概略です。実際の運用前に config/*.yaml や .env を生成/確認し、validate_config によるチェックを推奨します。必要であれば README を拡張して個別モジュールの API 使用例や設計ドキュメントへの参照を追加できます。