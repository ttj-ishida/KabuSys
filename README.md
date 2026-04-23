# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ + 起動スクリプト群）

この README は提供されたコードベースに基づく概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買、モニタリング、リサーチ、ポートフォリオ構築、AI を使ったニュースセンチメント評価等を組み合わせたシステムです。  
主要コンポーネントは次のとおりです。

- ExecutionEngine: 発注・注文管理・リスク管理・再整合（reconciler）などを担う実行エンジン
- Monitoring: システム稼働状況・注文状況・リスク指標のポーリング監視とアラート／Kill Switch の生成
- Research: DuckDB を使ったファクター計算・特徴量探索
- Portfolio: 候補選定、重み付け、ポジションサイズ決定、セクター制約・レジーム補正
- AI モジュール: ニュース NLP による銘柄センチメント評価、マクロニュースからのレジーム判定
- CLI ツール: .env 作成ウィザード、設定検証、Paper Trading 検証レポート生成 等

設計上の注目点:
- 環境変数（.env/.env.local）で挙動を制御
- paper_trading モードでは本番 DB と完全分離（MockBroker を利用）
- DuckDB を分析用に利用、SQLite を監視・発注ログ用に利用
- OpenAI（gpt-4o-mini）を利用した NLP 機能を含む（API キー必須）

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証（python -m kabusys.validate_config）
- ExecutionEngine の起動／停止監視（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading 専用 DB に記録
- Monitoring の起動（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト 60秒）
  - システム稼働率、データ鮮度、滞留注文、リスク指標など監視
- Kill Switch（条件により data/kill.flag を書き込み、Execution を停止）
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- DuckDB を用いたファクター計算（momentum / volatility / value 等）
- ニュース NLP（OpenAI）による銘柄スコアリング（ai.score_news）
- 市場レジーム判定（ai.regime_detector）

---

## セットアップ手順

1. リポジトリ（またはパッケージ）を配置
   - この README 想定では `src/` 配下に `kabusys` パッケージがある構成です。

2. Python 環境の用意
   - Python 3.9+ を想定（実行環境に合わせて調整）
   - 仮想環境を作成・有効化（例: venv / conda）

3. 依存パッケージをインストール
   - 必要なパッケージ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検査する場合）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - 実際の requirements.txt がある場合はそれを使用してください。

4. .env の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - これによりプロジェクトルートに `.env` が生成されます（.env は絶対に Git にコミットしないでください）。

   - 自動読み込みについて:
     - デフォルトで `.env`（および `.env.local`）を自動読み込みします。
     - 自動ロードを無効にする場合:
       ```
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
       ```

5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - OPENAI_API_KEY が AI 機能を使う場合に必要
   - その他は .env ウィザードを参照

6. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告も失敗扱いになります。

7. データ／ログディレクトリ
   - デフォルトで次のパスが使われます（.env で上書き可）
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   - 起動時に自動作成されますが、パーミッション等は事前に確認してください。

---

## 使い方（主要コマンド）

基本的にモジュールは -m で実行します。

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を行いません。
  - 実行中は data/execution.pid（デフォルト）に PID を書きます。

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（monitoring DB）を使用します（環境にかかわらず本番の sqlite_path を使う設計）。
  - 停止は data/stop_requested.flag を作成すると次のポーリングで終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。

- AI 関連（ライブラリ関数として）
  - ニュースセンチメントスコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止制御に関する注意:
- Kill Switch: 条件に該当すると monitoring 側が `.env` の kill_flag_path（デフォルト data/kill.flag）に文字列を書き、ExecutionEngine の起動中に検出すればエンジンを停止させます（冪等書き込み）。
- 手動でエンジンを止めたい場合: data/stop_requested.flag を作成すると run_monitoring/run_execution が次のループで検知して終了します。

ログ:
- 共通 logging 設定は kabusys.utils.logging_setup.setup_logging を通して設定されます。デフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。LOG_DIR、LOG_LEVEL により調整可。

---

## 環境変数（主なもの）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のマッチングモード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_PATH: kill.flag の出力先（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロード無効化（1 を設定）

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールのツリー（src/kabusys 配下）。実際のファイルはこの README の元となるコードベースに準じます。

```
src/kabusys/
├─ __init__.py
├─ config.py                 # 環境変数読み込み・Settings
├─ config_setup.py           # .env 対話ウィザード
├─ validate_config.py        # 設定検証 CLI
├─ run_execution.py         # ExecutionEngine 起動スクリプト
├─ run_monitoring.py        # Monitoring 起動スクリプト
├─ utils/
│  ├─ __init__.py
│  ├─ logging_setup.py      # ログ設定ユーティリティ
│  └─ process_priority.py   # プロセス優先度 / CPU affinity
├─ monitoring/
│  ├─ monitoring_db.py      # SQLite 永続化層
│  ├─ system_monitor.py
│  ├─ trade_monitor.py      # （存在は示唆、コードベース内にあることを期待）
│  ├─ risk_monitor.py
│  ├─ kill_switch.py
│  ├─ alert_manager.py      # （存在は示唆）
│  └─ monitoring_engine.py
├─ execution/
│  ├─ execution_engine.py   # エンジン本体（起動ロジック）
│  ├─ broker_factory.py     # BrokerClientFactory（Mock/実ブローカー切替）
│  ├─ order_manager.py
│  ├─ order_repository.py
│  ├─ reconciler.py
│  └─ risk_manager.py
├─ portfolio/
│  ├─ __init__.py
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py           # ニュース NLP（OpenAI）
│  └─ regime_detector.py    # レジーム判定（OpenAI + MA）
├─ monitoring/               # 再掲: 監視関連
└─ tools/
   ├─ __init__.py
   └─ paper_verification_report.py
```

（注）上記は主要モジュールを抜粋したもので、実際にはさらに細分化された実装ファイルが含まれる可能性があります。

---

## 運用上の注意点

- 本番運用（KABUSYS_ENV=live）を行う場合は validate_config での警告・エラーを必ず解消してください。特に LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定は重要です。
- paper_trading モードでは本番 DB を汚染しない設計になっていますが、環境変数の指定ミスに注意してください（PAPER_TRADING_SQLITE_PATH を明示する等）。
- OpenAI を利用する機能は API 呼び出しの失敗に備えたフォールバックロジックがありますが、API キー漏洩やコスト上限には十分注意してください。
- ログや DB の保存先（data/, logs/）は監視とバックアップを行ってください。

---

この README はコードベースの主要点をカバーしています。必要であれば、各モジュール（ExecutionEngine、TradeMonitor、AlertManager 等）の使い方や拡張ガイドを別途作成できます。何を追加したいか教えてください。