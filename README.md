# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群。  
本リポジトリは戦略・ポートフォリオ構築、監視、実行エンジン、AI を用いたニュース処理・レジーム判定などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日次〜リアルタイムの売買実行を想定した日本株自動売買プラットフォームの基盤部分です。  
主要機能は以下を含みます。

- 監視（System / Trade / Risk モニタ）：プロセス状態、データ鮮度、ドローダウン監視、Kill Switch。
- 実行エンジン（ExecutionEngine）と注文管理（OrderManager / OrderRepository）。
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制約）。
- リサーチ機能（ファクター計算、将来リターン、IC 等）。
- AI 補助（ニュースのセンチメントスコアリング、マクロニュースを用いた市場レジーム判定）。
- Paper Trading 用の分離DBと検証レポート生成スクリプト。

---

## 主な機能一覧

- run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- run_execution.py: 実行エンジン起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用し DB を分離）
- config_setup.py: .env を対話式に作成・更新するウィザード
- validate_config.py: .env と config/*.yaml を起動前に検証する CLI
- monitoring/*: MonitoringDB、SystemMonitor、RiskMonitor、KillSwitch、MonitoringEngine 等
- execution/*: ブローカー抽象、注文管理、リスク管理、実行エンジン（エントリポイントは run_execution.py）
- portfolio/*: 候補選定、重み付け、サイズ決定、セクター制約、レジーム乗数
- research/*: ファクター計算（Momentum/Value/Volatility）、特徴量探索、IC、統計サマリ
- ai/*: ニュース NLP スコアリング、レジーム判定（OpenAI API を使用）
- tools/paper_verification_report.py: Paper Trading 検証レポート生成

---

## 要件（推奨）

- Python 3.10+
- 必要な Python パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証で使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実際の requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

---

## セットアップ手順

1. リポジトリをチェックアウトしてプロジェクトルートへ移動。

2. Python 仮想環境を作成し依存パッケージをインストール（上記参照）。

3. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 自動読み込み:
     - 起動時、プロジェクトルートに `.env` と `.env.local`（オプション）があれば自動読み込みされます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます）。
     - ロード優先度: OS 環境変数 > .env.local > .env

4. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   # --strict を付けると warning も失敗扱い (exit 1)
   python -m kabusys.validate_config --strict
   ```

5. 必要ディレクトリ（data, logs 等）は起動時に自動作成されますが、権限等に注意してください。

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）（デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番では 0 推奨）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

---

## 起動・使い方

各モジュールはモジュール実行可能（python -m）として提供されています。

- 監視ループの起動（SystemMonitor を常時実行）:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（例: 30秒）。
  - 監視プロセスはプロジェクトルート直下の `data/stop_requested.flag` を検知すると終了します。

- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（data/paper_trading.db 等）へ記録します（本番 DB とは完全分離）。
  - 実行中に `data/stop_requested.flag` を作成するとエンジン停止を試みます。
  - 実行時に PID ファイル（デフォルト data/execution.pid）を出力します。

- .env の対話式作成:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 系機能（ニューススコア・レジーム判定）は OpenAI API キーが必要です。環境変数 `OPENAI_API_KEY` を設定してください。
  - ニューススコア: kabusys.ai.score_news を呼び出して DuckDB 接続と日付を渡して実行する設計です（スクリプトから直接実行するエントリポイントはユーティリティとして提供されています）。

---

## ログ・データ

- ログ:
  - デフォルト出力先: logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション、30日保持）
  - コンソール出力は stdout に出力されます（stderr ではありません）。

- DB:
  - DuckDB: 分析用（data/kabusys.duckdb）
  - SQLite (monitoring): 監視ログ（data/monitoring.db）
  - SQLite (paper trading): paper_trading 環境時は data/paper_trading.db（環境により上書き可能）

- Kill Switch / Stop フラグ:
  - Kill Switch は条件成立時に `data/kill.flag` を書き込み、ExecutionEngine に停止を促します（KillSwitch クラスが管理）。
  - 手動停止・外部要求用には `data/stop_requested.flag` を作成すると run_monitoring / run_execution のループが検知して安全停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると Execution 起動時に kill.flag を自動でクリアします（本番環境では通常 0 推奨）。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル・ディレクトリの構成イメージです（src/kabusys をルートとした表示）。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - tools/
    - __init__.py
    - paper_verification_report.py

（実際のファイル数・詳細はリポジトリの src/kabusys 配下を参照してください）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では設定とシークレット管理を厳重に行ってください。validate_config は本番向けのチェック（LINE 通知設定など）を行います。
- .env は絶対にコミットしないでください（config_setup.py のヘッダにも同様の注意書きがあります）。
- OpenAI API を使用する機能は API 利用料が発生します。キーの管理・使用ポリシーに注意してください。
- run_execution/run_monitoring はプロセス優先度を「high」に設定しようとします。権限がない場合は警告が出ますが動作は継続します。
- Paper Trading は本番 DB と分離されますが、DB パス設定は .env で明示的に行ってください。

---

## 開発・拡張のヒント

- DuckDB 接続を渡すことでリサーチ関数（research/*.py）は DB を参照して計算する設計です。テスト時は in-memory の DuckDB を構築してユニットテストを作成できます。
- AI 呼び出しは retry/backoff、レスポンス検証を行うよう設計されています。テストでは各モジュールの API 呼び出し関数（_call_openai_api 等）をモックしてください。
- 設定読み込みロジックは project root を .git / pyproject.toml で検出するため、インストール配布後もカレントワーキングディレクトリに依存しないよう配慮されています。

---

必要であれば、README にコマンド例や運用チェックリスト、よくあるトラブルシュート（ログの場所、権限エラー、DB 作成エラー等）を追加します。どの情報を優先して追記しますか？