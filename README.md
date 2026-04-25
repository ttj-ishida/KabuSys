# KabuSys

日本株向け自動売買システムのコアライブラリ群および起動スクリプト集です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、AI を用いたニュースセンチメントなどの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を想定しています。

- データベース（DuckDB / SQLite）を用いた市場データの保持と分析
- 戦略に基づく銘柄選定・配分・株数決定（ポートフォリオ構築）
- 発注エンジン（実取引 / ペーパートレード切替）
- 発注・約定・リスク監視の永続化（SQLite）
- システム監視（CPU/メモリ/Disk、プロセス生存確認、データ鮮度）
- Kill Switch による安全停止、アラート送信フック
- OpenAI を利用したニュース NLP（センチメント付与）、レジーム判定
- ペーパートレード検証レポート生成、設定ウィザード・検証 CLI

主要スクリプトはモジュールとしても呼び出せるほか、ライブラリ関数（ポートフォリオ構築やリサーチ関数）としても利用できます。

---

## 機能一覧（抜粋）

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading/ live 切替）
  - run_monitoring: SystemMonitor のポーリングループを起動（監視専用）
- 設定関連
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 環境・設定ファイルの事前検証 CLI
- モニタリング
  - monitoring_db: SQLite スキーマ/永続化ロジック
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine
  - kill_switch: 条件に応じた停止フラグ書き込み
- ポートフォリオ構築（純粋関数）
  - portfolio_builder: 候補選定、等配分・スコア配分
  - position_sizing: 株数計算、ロット丸め、aggregate cap 調整
  - risk_adjustment: セクター上限、レジーム乗数
- リサーチ
  - factor_research: Momentum/Value/Volatility 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC、統計要約
- AI（OpenAI）
  - news_nlp: raw_news を OpenAI へ送って銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ETF の MA 乖離 + マクロニュースで市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成

---

## 必要な依存パッケージ（代表）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証で YAML をパースする場合）
- その他標準ライブラリ（sqlite3 等）

例（pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローンしワークディレクトリへ移動
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env の作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 一般的なデフォルト:
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - KABUSYS_ENV=development （development / paper_trading / live）
     - KILL_FLAG_CLEAR_ON_START=0
4. 設定検証（任意／推奨）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告を FAIL 扱いにする
   ```
5. ログディレクトリ（デフォルト: logs/）は自動作成されますが、パーミッションを確認してください。

注意事項:
- ペーパートレード（KABUSYS_ENV=paper_trading）は発注系をモック化し、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。
- Monitoring 用スクリプトは環境に関わらず settings.sqlite_path（= monitoring.db）を使用します。

---

## 使い方

コマンドラインから実行する主な入口:

- ExecutionEngine 起動
  - デーモンや手動で実行:
    ```
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中は data/execution.pid を書きます（デフォルト）。
    - プロセス優先度は起動時に "high" に設定されます（psutil を使用）。

- Monitoring 起動
  - ポーリングループを開始:
    ```
    python -m kabusys.run_monitoring
    ```
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト: 60）。1 未満や不正値は無視されデフォルトにフォールバック。
  - 監視は SQLite（settings.sqlite_path）と DuckDB（settings.duckdb_path）に接続します。
  - 停止は data/stop_requested.flag の作成で行えます（run_monitoring はこのフラグを検出して優雅に終了します）。

- .env の操作
  - 対話式作成:
    ```
    python -m kabusys.config_setup
    ```
  - 検証:
    ```
    python -m kabusys.validate_config
    ```

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も使用可。

- AI 関連（ニュース NLP / レジーム判定）
  - 実行前に OpenAI API キーを設定:
    ```
    export OPENAI_API_KEY="sk-..."
    ```
  - モジュール関数をコード上から呼び出す:
    - kabusys.ai.news_nlp.score_news(duckdb_conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=None)

注意: OpenAI への API 呼び出しは失敗耐性がありますが、API キーは必須です。失敗時は安全側の値（0.0 等）でフォールバックします。

---

## 重要なファイル・フラグ

- data/stop_requested.flag: run_execution/run_monitoring が存在を検知して停止します（管理者が作成することで優雅に停止）。
- data/kill.flag: KillSwitch が判定した場合に作成され、ExecutionEngine に停止シグナルを送る目的で使用します（Settings.kill_flag_clear_on_start により起動時に自動クリアするかを制御）。
- data/execution.pid: ExecutionEngine が書き込む PID ファイルのデフォルト場所。

設定値は環境変数で上書き可能。Settings クラスが読み取りロジックを提供します（kabusys.config.Settings）。

---

## ディレクトリ構成

（主要なファイル群を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込みロジック
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ & DB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信の抽象化、実装による）
  - execution/                — 発注関連（BrokerFactory, ExecutionEngine, OrderManager 等）
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
  - data/                     — デフォルト DB / フラグ / pid 等（.gitignore で除外推奨）

---

## 開発時のヒント

- .env は絶対にリポジトリにコミットしない（config_setup のヘッダにも注意書きがあります）。
- validate_config は起動前に必ず実行し、必須環境変数が設定されていることを確認してください。
- run_execution/run_monitoring の停止は stop_requested.flag の作成で行うのが安全です。kill.flag はシステム側からの「停止要求（Kill Switch）」であり自動的に書き込まれます。
- DuckDB は分析用途、SQLite は監視/トランザクションログ（軽量永続化）用途に使い分けています。
- OpenAI を使う機能は API の料金が発生します。テストではモック化して呼び出しを抑えてください（news_nlp._call_openai_api 等を patch 可能）。

---

## ライセンス / 貢献

この README はコードベースの説明に基づく概要です。実際のライセンスやコントリビューションガイドはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

README に記載した情報はコードの該当箇所（kabusys/config.py, run_execution.py, run_monitoring.py, monitoring/*, ai/*, portfolio/* など）を参照して要点を抜粋しています。必要ならば各モジュールのより詳しい使い方・API ドキュメント（関数シグネチャや返り値）を追加で生成します。どの部分を詳しくドキュメント化しましょうか？