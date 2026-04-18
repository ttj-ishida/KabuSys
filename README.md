# KabuSys

日本株自動売買システムのリポジトリ（ドキュメント的なコードベース抜粋）。  
この README はローカル実行や設定、主要スクリプトの使い方をまとめた参照ドキュメントです。

> ※ 本 README はリポジトリ内の Python モジュール群（src/kabusys 以下）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買および関連する研究・監視機能を提供する Python ベースのシステムです。  
主な役割は以下の通りです。

- 注文実行（ExecutionEngine）・注文管理・リスク管理
- 監視（System / Trade / Risk）と Kill Switch による自動停止
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 研究モジュール（ファクター計算、特徴量分析）
- AI を用いたニュースセンチメント解析・市場レジーム判定（OpenAI）
- Paper Trading 用の分離された DB／モックブローカー対応
- ログ管理（コンソール + 日次ローテーション）

---

## 機能一覧（抜粋）

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し `data/paper_trading.db` を使う。
  - 起動時にプロセス優先度を "high" に設定し、PID ファイルを書き込む。
  - 停止は `data/stop_requested.flag` や `data/kill.flag` を通じて行う仕組み。

- run_monitoring.py
  - SystemMonitor をポーリングして system_status / trade_logs / risk_logs / dashboard に記録。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用。

- monitoring モジュール
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine / MonitoringDB
  - kill.flag の書き込み（KillSwitch）で ExecutionEngine を停止可能

- portfolio モジュール
  - 候補選定（select_candidates）、重み計算（等金額 / スコア加重）、ポジションサイズ計算、セクター上限・レジーム乗数処理

- research モジュール
  - ファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリー

- ai モジュール
  - news_nlp.score_news: OpenAI を使ってニュースを銘柄ごとにセンチメント化し ai_scores に書込む
  - regime_detector.score_regime: 1321（ETF）の MA200 乖離 と マクロニュースの LLM センチメントを合成してレジーム判定

- ユーティリティ
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定検証 CLI
  - tools/paper_verification_report.py: Paper Trading の検証レポート出力

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。
2. 必要なパッケージをインストールします（プロジェクトに requirements.txt があればそれを使用）。
   - 主要依存例:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config ファイル検証のため）
   - 例:
     - pip install duckdb psutil openai PyYAML
3. .env を作成します（対話式推奨）。
   - python -m kabusys.config_setup
   - もしくはリポジトリ直下に `.env` を手動で作る
4. .env に必須値を設定
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - その他: KABUSYS_ENV（development/paper_trading/live）, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（paper_trading 用）, OPENAI_API_KEY（AI を使う場合）など
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も厳密に扱いたい場合は --strict を付与
6. データディレクトリ・ログディレクトリの確認
   - デフォルト DB/ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID/flags: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/<app>.log（logs ディレクトリが作成されます）

注意: .env は秘密情報を含むため絶対に Git にコミットしないでください。

---

## 環境変数（主なもの）

（完全な一覧は `src/kabusys/config.py` を参照）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し paper 用 DB（PAPER_TRADING_SQLITE_PATH）に分離
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY: OpenAI 利用時に必要
- MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアする (0/1)

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告を失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 動作: PID ファイルを書き込み、ExecutionEngine をスレッドで実行。`data/stop_requested.flag` の存在で停止。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は本番 sqlite_path（SQLITE_PATH）を使用（KABUSYS_ENV に依存しない）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（プログラムから呼ぶ API）
  - ニューススコアリング（ai.news_nlp）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn は duckdb connection（duckdb.connect(...)）を渡す
    - api_key を None にすると環境変数 OPENAI_API_KEY を参照
  - レジーム判定（ai.regime_detector）:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意点:
- Execution 起動時、paper_trading モードは paper 用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。
- kill.flag を存在させると ExecutionEngine に停止命令を出す仕組みです。kill.flag の作成・削除は KillSwitch を利用してください（config の KILL_FLAG_CLEAR_ON_START に依存）。

---

## ログ・プロセス優先度

- すべてのメインスクリプトは共通の logging 設定ユーティリティを使用します:
  - kabusys.utils.logging_setup.setup_logging(app_name="...")

- ログ:
  - コンソール（stdout）出力と logs/<app_name>.log へ日次ローテーション（30日保持）
  - LOG_DIR 環境変数でログディレクトリを変更可能

- プロセス優先度:
  - 起動時に set_process_priority("high") を呼び出しています（psutil を使用）
  - 権限不足等で設定できない場合は警告を出してスキップします

---

## ディレクトリ構成（主要ファイル・モジュール）

リポジトリの `src/kabusys` 以下（抜粋）:

- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py (存在が参照されるが省略）
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py (参照あり)

- execution/
  - execution_engine.py (参照あり)
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- monitoring tools / util:
  - utils/logging_setup.py
  - utils/process_priority.py
  - utils/__init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

- data/ (runtime)
  - monitoring.db (デフォルト SQLite)
  - paper_trading.db (paper_trading 用)
  - kabusys.duckdb (DuckDB)
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## よくある運用注意

- .env に秘密情報を含むため、絶対にバージョン管理に含めないでください。
- 本番（KABUSYS_ENV=live）での起動は慎重に。validate_config.py による検証を必ず通してください。
- Paper Trading モードは本番 DB から分離されますが、各種ファイル（logs、flag）は共有ディレクトリを使うことがあるため運用ルールを決めてください。
- OpenAI API 呼び出しは課金が発生します。API キーと呼出し量に注意してください。
- DuckDB / SQLite のファイルパスは環境変数で変更できます。バックアップ・アクセス権限に注意してください。

---

## 開発者向け情報

- ユニットテストや CI は本 README で扱っていませんが、各モジュールは純粋関数（副作用なし）で書かれている箇所が多く、単体テストが書きやすい設計になっています（例: portfolio/*.py, research/*.py）。
- OpenAI 呼び出し部分は外部依存が強いためテスト時にはモック化（unittest.mock.patch）することを想定しています（実装内で明記あり）。
- DuckDB を使う研究系関数は DB 接続を引数で受け取り、ローカル環境でテスト可能です。

---

## 最後に

この README はコードベースに含まれるモジュールから要点を抽出した概要ドキュメントです。実運用前には必ず `python -m kabusys.validate_config` による設定検証と、開発環境での動作確認を行ってください。

質問や追加で README に載せたい具体的なコマンド例があれば教えてください。README を拡張してコマンド別の詳細手順やトラブルシュートを追記できます。