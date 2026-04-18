# KabuSys

日本株向け自動売買システムのコアライブラリ（README）。  
このドキュメントはリポジトリ内のスクリプト／モジュール群に基づいて、導入・起動方法や機能を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件（Dependencies）
- セットアップ手順
- 使い方（起動コマンド / ツール）
- 環境変数（主要項目とデフォルト）
- ファイル・ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買およびリサーチ用モジュール群をまとめたプロジェクトです。  
主に以下の責務を持つコンポーネントを含みます。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム状態 / 注文・リスク監視）
- Portfolio construction（銘柄選定・配分・ポジションサイズ計算）
- Research（ファクター計算・特徴量探索）
- AI コンポーネント（ニュース NLP によるセンチメント、レジーム判定）
- CLI ユーティリティ（.env ウィザード、設定検証、検証レポート等）

設計上の留意点：
- Paper Trading 環境は本番 DB と分離（paper_trading 用 SQLite を使用）。
- LLM（OpenAI）を利用する機能は API キーを必要とし、失敗時はフェイルセーフで継続する実装になっています。
- ロギングは統一的に設定され、日次ローテーション（logs/*.log）されます。

---

## 機能一覧

- 実行（Execution）
  - Broker クライアントの抽象化（本番 / モック切替）
  - OrderManager / RiskManager / Reconciler 統合
  - ExecutionEngine によるセッション実行と PID 管理
- 監視（Monitoring）
  - システム状態（CPU/MEM/DISK/プロセス）監視
  - 注文ログ / リスクログの永続化（SQLite）
  - Kill Switch（dradown・ポジション上限で停止フラグを書き込む）
  - MonitoringEngine：各 Monitor を束ねて定期実行
- ポートフォリオ構築
  - 候補選定、等金額・スコア加重の重み計算
  - セクター上限適用、レジーム乗数
  - 株数決定（risk_based / equal / score）、単元株丸め、合計キャップ調整
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）の算出、統計サマリー
- AI（OpenAI）
  - ニューステキストの銘柄別センチメント付与（ai_scores へ書き込み）
  - マクロニュースを用いた市場レジーム判定（market_regime テーブルへ書込）
  - API 呼び出しはリトライ・バックオフ・レスポンス検証を行う
- ツール
  - .env 対話式作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 用検証レポート生成（tools/paper_verification_report）

---

## 必要条件（Dependencies）

必須（少なくとも以下が必要です）:
- Python 3.9+
- pip install で以下をインストールすることを推奨:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合に必要）
（その他、標準ライブラリのみで動作する部分も多いです）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

注意: SQLite は Python 標準の sqlite3 モジュールを使用します（システムに特別な準備は不要）。

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートに移動
2. 仮想環境作成（推奨）
3. 依存パッケージをインストール（上記参照）
4. .env を作成
   - 自動で .env をロードする仕組みが組み込まれています（プロジェクトルートに .env または .env.local を置く）。
   - 対話式ウィザードで作成する:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定検証:
     ```
     python -m kabusys.validate_config
     # 警告もエラー扱いにする場合:
     python -m kabusys.validate_config --strict
     ```
5. データディレクトリの準備（通常は自動作成されます）
   - デフォルトでは data/ 以下に SQLite / PID / flag ファイル等を保持します。
6. 必要に応じて OpenAI API キー 等を .env に設定（ai 機能を使う場合）

---

## 環境変数（主要項目）

多くは .env に設定します。主要なものとデフォルト値（設定がない場合）は下記の通りです。

- KABUSYS_ENV
  - 有効値: development / paper_trading / live
  - デフォルト: development
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
- LOG_LEVEL
  - デフォルト: INFO
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH
  - Paper Trading 時の専用 DB（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE
  - Paper Trading のモック約定挙動: instant / partial / never / reject（デフォルト: instant）
- PID_FILE_PATH
  - デフォルト: data/execution.pid
- KILL_FLAG_PATH
  - デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START
  - 0/1（デフォルト: 0） — Execution 起動時に kill.flag を自動クリアするか
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視用閾値）
- OPENAI_API_KEY
  - AI 機能（news_nlp / regime_detector）で利用

特記事項:
- 自動 .env ロードはデフォルトで有効。無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL
  - 監視ループのポーリング間隔（秒）。run_monitoring で参照。デフォルトは 60 秒。環境変数で上書き可能。
  - 例: export MONITOR_POLL_INTERVAL=30

---

## 使い方

プロジェクトルート（.env があるディレクトリ）で実行することを想定しています。

### 1) .env の生成（対話式）
```
python -m kabusys.config_setup
```
終了後、.env が作成されます。

### 2) 設定検証
```
python -m kabusys.validate_config
# --strict を付けると警告も失敗扱いになります
python -m kabusys.validate_config --strict
```

### 3) ExecutionEngine を起動
ExecutionEngine は発注・注文管理を担当します。

- 通常起動:
```
python -m kabusys.run_execution
```

- 注意点:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に書き込みます（本番 SQLite と完全分離）。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中に stop フラグを立てるには data/stop_requested.flag を作成するとエンジンは停止要求を検知します。
  - PID ファイル: デフォルト data/execution.pid

### 4) Monitoring を起動
システム状態／注文／リスクを定期監視します。

```
python -m kabusys.run_monitoring
```

- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可。デフォルト 60 秒。
- 監視は Settings.sqlite_path（production 相当）を用いて DB に永続化します（モニタは環境に依らず本番 sqlite_path を参照する仕様）。
- stop フラグ: data/stop_requested.flag を配置すると監視ループが終了します。

### 5) Paper Trading 検証レポート（ツール）
Paper Trading の SQLite を解析してレポートを生成します。

```
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB 指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

### 6) AI 機能（ニュース NLP / レジーム判定）
OpenAI API キーが必要です（OPENAI_API_KEY または関数呼び出し時の api_key 引数）。

- ニューススコア付与: kabusys.ai.score_news（DuckDB 接続・target_date を渡して呼び出す）
- レジーム判定: kabusys.ai.regime_detector.score_regime（同様）

AI 呼び出しはリトライ・バックオフ・レスポンス検証を実装しています。API キーが未設定だと例外が発生しますので .env に設定してください。

---

## 追加の運用上注意点

- ロギング
  - 共通の logging 設定関数が用意されています: kabusys.utils.logging_setup.setup_logging(app_name="...")  
  - ログは stdout と logs/<app_name>.log（日次ローテーション、30 日保持）へ出力します。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出し、可能ならば優先度を上げます（プラットフォーム依存）。
- Kill Switch
  - RiskMonitor / KillSwitch により重大リスクが検出されると data/kill.flag が書き込まれ、ExecutionEngine 側で停止シグナルとして扱われます。
  - 本番（KABUSYS_ENV=live）で KILL_FLAG_CLEAR_ON_START=1 は危険なので推奨されません。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成を行い、既存 DB に対する軽微なマイグレーション（カラム追加）も行います。

---

## ディレクトリ構成（主なファイル・フォルダ）

リポジトリの主要部分（src/kabusys 以下）を抜粋しています。

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / Settings
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — SystemMonitor 起動スクリプト
    - ai/
      - news_nlp.py              — ニュース NLP（OpenAI 依存）
      - regime_detector.py       — 市場レジーム判定（OpenAI 依存）
    - monitoring/
      - monitoring_db.py         — SQLite 永続化層
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
      - risk_manager.py
      - broker_factory.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - data/
      - pipeline.py               — データ取得・DuckDB 周り（prices_daily 等）
      - stats.py                  — 正規化ユーティリティ等
    - utils/
      - logging_setup.py
      - process_priority.py
    - tools/
      - paper_verification_report.py

プロジェクトルートには通常以下のディレクトリ/ファイルが想定されます:
- .env, .env.local (環境変数)
- config/ (system_config.yaml など: validate_config が参照)
- data/ (monitoring DB, paper_trading DB, PID/flag files)
- logs/ (ログファイル)
- pyproject.toml / setup.py 等（配布用）

---

## よくあるコマンド集（例）

- .env ウィザード：
  ```
  python -m kabusys.config_setup
  ```
- 設定検証：
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- Execution（本番または paper_trading）：
  ```
  python -m kabusys.run_execution
  ```
- Monitoring（常駐）：
  ```
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート：
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

以上が本リポジトリの README 相当の概要と起動手順です。細かい内部仕様（関数引数や戻り値、SQL スキーマなど）は各ソースコードの docstring を参照してください。必要ならばこの README を元に INSTALL.md や OPERATION.md といった個別ドキュメントの作成も支援します。