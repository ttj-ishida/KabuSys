# KabuSys

日本株向け自動売買システム（ライブラリ / 起動スクリプト群）

本リポジトリは、戦略研究（DuckDB）、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、AI 補助（ニュース NLP / レジーム判定）などを含む自動売買基盤の一部です。本 README はコードベース（src/kabusys 配下）の利用開始手順、主要機能、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は次の主要コンポーネントを提供します。

- ExecutionEngine 起動スクリプト（run_execution.py）  
  実際のブローカークライアントまたはペーパートレード用の MockBrokerClient を使って注文処理を行います。KABUSYS_ENV によって paper_trading / live / development を切り替え可能。ペーパートレード時は専用 SQLite（data/paper_trading.db）に出力して本番 DB と分離します。

- Monitoring（run_monitoring.py / monitoring パッケージ）  
  システム稼働状態、データ鮮度、注文/約定ログ、リスク指標を定期的にチェックし、kill.flag の作成やアラート送信のトリガーを行います。監視データは SQLite（デフォルト: data/monitoring.db）に永続化されます。

- ポートフォリオ構築（portfolio パッケージ）  
  候補選定、重み計算、セクター制約、ポジションサイズ計算（単元丸め・リスクベース等）を純粋関数として提供します。

- 研究モジュール（research パッケージ）  
  DuckDB 上でファクター（モメンタム / ボラティリティ / バリュー）や特徴量探索、将来リターン、IC 計算、サマリー等を計算する関数群。

- AI モジュール（ai パッケージ）  
  OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメントスコアリング（news_nlp）や市場レジーム判定（regime_detector）。API 呼び出しのリトライ、バリデーション、部分書き込みの安全性に配慮しています。

- ユーティリティ（utils）  
  ロギング初期化（ログの日次ローテーションなど）、プロセス優先度設定、環境変数の自動ロード補助など。

- ツール（tools）  
  ペーパートレードの検証レポート生成ツール（paper_verification_report.py）など。

---

## 機能一覧（抜粋）

- 環境設定ウィザード（kabusys.config_setup.run_wizard）と .env 生成
- 設定検証 CLI（kabusys.validate_config）: .env / config/*.yaml の整合性チェック
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（バックグラウンドスレッド）
  - run_monitoring.py — SystemMonitor ポーリングループ起動
- 監視関連
  - MonitoringDB（SQLite）に system_status / trade_logs / risk_logs / positions / dashboard を定義・操作
  - RiskMonitor、TradeMonitor、SystemMonitor、MonitoringEngine、KillSwitch、AlertManager（アラート送信は LINE や他の実装に依存）
- ポートフォリオ構築ライブラリ（候補選別、重み算出、ポジションサイズ算出、セクターキャップ、レジーム乗数）
- 研究用関数（DuckDB 接続を受ける）
- AI: ニュースの LLM ベースセンチメント評価（batch、JSON mode、リトライ、検証）、レジーム判定
- ツール: Paper Trading の検証レポート出力（JSON/ターミナル）

---

## 前提 / 必要要件

- Python 3.9+（ソースは型ヒントに対応）
- 必須ライブラリ（main 機能利用時）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - sqlite3（標準ライブラリ）
- 任意（構成検証で YAML を検証する場合）
  - PyYAML

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンしてソースルートに移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して依存をインストール（上記参照）

3. .env の作成
   - 対話式ウィザードを使う（推奨）
     ```
     python -m kabusys.config_setup
     ```
     これにより .env が生成されます（.env は Git に絶対コミットしないでください）。

   - または手動で .env を作成（最低限必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - 例（.env の要点）
       ```
       JQUANTS_REFRESH_TOKEN=your_token_here
       KABU_API_PASSWORD=your_password_here
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO
       ```

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリの準備（data, logs 等は自動作成されることが多いですが手動で用意しておくと安全）
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要コマンド例）

- ExecutionEngine を起動（デフォルトは settings に従う）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）にトレードログを出力します。
  - 実行中の停止は data/stop_requested.flag の作成で通知できます（run_execution はこのフラグを検出して正常停止します）。

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（デフォルト: data/monitoring.db）へ書き込みます（環境に関係なく本番 sqlite_path を使用）。

- .env の作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート（SQLite DB 指定可）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- ライブラリ関数を直接利用（例: 研究用）
  Python REPL やスクリプト内で DuckDB 接続を渡して呼び出す:
  ```py
  import duckdb
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 4, 1))
  ```

- AI 機能（ニューススコアリング / レジーム判定）
  - OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時に api_key を渡します。
  - 例:
    ```py
    from kabusys.ai.news_nlp import score_news
    # conn は duckdb connection, target_date は datetime.date
    count = score_news(conn, target_date, api_key="sk-...")
    ```

---

## 主要環境変数（要点）

- 必須（本番・研究で使用）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live

- DB / ファイルパス
  - DUCKDB_PATH: DuckDB データベース（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: エンジンの PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）

- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログファイル出力先（デフォルト: logs/）

- Monitoring 特有
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）

- Paper Trading / Mock Broker
  - PAPER_FILL_MODE: instant | partial | never | reject

- OpenAI
  - OPENAI_API_KEY: LLM 呼び出しに必要

- その他
  - KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" で有効。注意: 本番では推奨されない）

---

## 停止・Kill Switch の仕組み

- run_execution / run_monitoring はプロセス内で data/stop_requested.flag の存在を監視しています。管理者がこのファイルを作成すると次回ループで安全停止します。
- KillSwitch（監視側）は条件（ドローダウン閾値超過・ポジション数上限など）を満たすと data/kill.flag を書き込みます。ExecutionEngine は起動時/稼働中に kill.flag を検出すると停止します。
- kill.flag の自動クリアを有効にする環境変数 KILL_FLAG_CLEAR_ON_START=1 がありますが、本番環境では OFF（0）を推奨します。

---

## ログ / ファイル出力

- デフォルトのログ出力先: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）。日次ローテーション・30 日保持。
- 監視 DB: data/monitoring.db（SQLite）
- ペーパートレード DB: data/paper_trading.db（paper_trading 環境時）
- PID / フラグファイル: data/execution.pid, data/stop_requested.flag, data/kill.flag

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動ロードロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ロギング初期化（console + timed file handler）
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ / CRUD ラッパー
    - system_monitor.py
    - trade_monitor.py       — （trade_monitor 実装あり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信の抽象）
  - execution/                — ExecutionEngine 周り（発注・OrderManager 等）
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

（上記はコードベースの主要ファイル一覧です。実際のリポジトリではさらに補助スクリプト・モジュールが存在する場合があります。）

---

## 開発メモ / 注意点

- .env はセキュアに管理し、VCS にコミットしないでください。
- KABUSYS_ENV=live の場合は特に注意が必要です。validate_config は本番向けの追加ガードを出します（LINE トークン等のチェック、kill flag の自動クリア警告など）。
- AI（OpenAI）呼び出しはネットワークやレート制限の影響を受けます。API キーは安全に保管してください。AI モジュールは部分失敗に備えたフェイルセーフを実装していますが、本番での運用前に十分な検証を行ってください。
- DuckDB は研究・分析用。prices_daily / raw_financials / raw_news 等のテーブル構成に依存するため、データ投入スクリプトや ETL パイプラインが別途必要です。
- プロセス優先度設定（set_process_priority）は OS に依存します（Windows / POSIX）。権限不足で変更できない場合は警告を出してスキップします。

---

## サポート / 追加情報

- 設定テンプレートや config/*.yaml の生成スクリプトがリポジトリに含まれている場合があります（scripts ディレクトリ等）。validate_config の警告に従って生成してください。
- さらに詳細なドキュメント（アルゴリズム解説、PortfolioConstruction.md, StrategyModel.md 等）が repo に含まれている想定です。研究・運用前にそちらも参照してください。

---

README に記載のない操作や詳細な API 仕様については、該当モジュールの docstring を参照してください。README の補足や改善点があればお知らせください。