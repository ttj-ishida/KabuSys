# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買 / 研究支援ライブラリ群と実行用スクリプト群を含むプロジェクトです。  
本 README はプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: 実行スクリプトは本番市場への発注を行う可能性があるため、本番運用前に設定（.env や config/*.yaml）を十分に確認してください。

---

## プロジェクト概要

KabuSys は以下の目的を持ったモジュール群を提供します。

- データ取り込み・集計（DuckDB を想定）
- ファクター計算・リサーチ（momentum / volatility / value 等）
- ポートフォリオ構築（候補選定、重み付け、株数計算、リスク調整）
- 実行エンジン（ExecutionEngine、ブローカークライアント抽象）
- 監視・アラート（SystemMonitor / TradeMonitor / RiskMonitor、Kill Switch）
- AI 活用（ニュースセンチメント、レジーム検出 via OpenAI）
- 開発運用ユーティリティ（.env ウィザード・設定検証・レポート生成）

設計上、研究コードは実取引ロジックと分離されており、Paper Trading（モックブローカー）動作もサポートします。

---

## 主な機能一覧

- 実行制御
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により paper_trading / live / development）
  - run_monitoring: SystemMonitor ポーリングループを起動（監視ログを SQLite に永続化）
- 監視
  - SystemMonitor: CPU / メモリ / ディスク、実行プロセス監視、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 注文遅延・約定異常・ドローダウン・ポジション数監視
  - KillSwitch: しきい値超過で data/kill.flag を書き込み ExecutionEngine の停止を誘発
  - MonitoringDB: SQLite への監視テーブル作成・読み書きユーティリティ
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスクに基づく株数決定、セクター制限、レジーム乗数
- 研究・ファクター計算
  - calc_momentum, calc_volatility, calc_value（DuckDB 接続を受けて計算）
  - 特徴量解析: 将来リターン、IC、統計要約
- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を LLM でセンチメント付与し ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロセンチメントを組み合わせて market_regime を判定
- 開発運用ユーティリティ
  - config_setup: .env を対話式に生成 / 更新
  - validate_config: 環境変数・config/*.yaml の検証 CLI
  - tools.paper_verification_report: ペーパートレード結果の検証レポート生成

---

## 必要条件（依存関係）

- Python 3.10 以上（| 型注記の使用のため）
- 必要パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
- 任意:
  - PyYAML（config/*.yaml 検証を行う場合）
- SQLite は標準ライブラリで利用

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai
# optional
pip install pyyaml
```

---

## 環境変数とデフォルト

主要な環境変数（.env 参照）:

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / デフォルトあり:
  - KABUSYS_ENV: development | paper_trading | live  (default: development)
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - LOG_DIR: logs/
  - OPENAI_API_KEY: OpenAI を使用する場合
  - PAPER_FILL_MODE: instant | partial | never | reject (paper_trading 用、default: instant)
  - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring で上書き可能、default: 60）

注意: Settings クラスは自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨 .env の骨子（例）:

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成:

```bash
git clone <repo_url>
cd <repo_root>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # もし用意されていれば
# または必要パッケージを個別にインストール:
pip install duckdb psutil openai pyyaml
```

2. .env を作成:
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成し、上記の必須変数を設定してください。

3. 設定を検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

4. 必要なディレクトリを作成（data, logs 等は自動作成される場合あり）:
   ```bash
   mkdir -p data logs
   ```

5. DuckDB / SQLite データベースはスクリプト実行時に自動で初期化されます（monitoring 用テーブルなどは init_monitoring_db が作成）。

---

## 使い方（主要コマンド）

- 監視プロセス起動（ポーリング）:
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒で指定可能（例: 30 秒）
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 実行中は data/stop_requested.flag の存在を検知してループを終了します（stop フラグ）。

- 実行エンジン起動（ExecutionEngine）:
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、モックブローカーを使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行エンジンは data/execution.pid に PID を書き出します。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI スコア / レジーム判定（プログラムから利用）:
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、必要に応じて OPENAI_API_KEY を環境変数または引数で与えます。

- kill.flag の操作:
  - KillSwitch は data/kill.flag を書き込み ExecutionEngine 停止を促します。
  - 手動でクリアする場合:
    ```bash
    rm -f data/kill.flag
    ```

---

## 動作上の注意点 / 動作差分

- run_monitoring は KABUSYS_ENV に依らず settings.sqlite_path（本番監視 DB）を使用します。監視ログは本番 DB に保存されます。
- run_execution は KABUSYS_ENV が `paper_trading` の場合、paper_sqlite_path を使用して完全に分離された DB に記録されます（本番 DB とは分離）。
- Paper Trading の fill 動作は PAPER_FILL_MODE により挙動を変更できます。
- OpenAI 連携機能は API 呼び出しで課金が発生します。テスト時はモック化を推奨します（各モジュール内で API 呼び出しを差し替え可能）。
- ログ設定: logs/<app_name>.log に日次ローテートで出力されます（30 日保持）。ログレベルは LOG_LEVEL で制御可能。

---

## ディレクトリ構成

リポジトリのルート配下に `src/kabusys` 配下で主要モジュールが配置されています。主要ファイル・ディレクトリを抜粋します:

```
src/kabusys/
├─ __init__.py
├─ config.py                 # 環境変数・設定読み込み
├─ config_setup.py           # .env 対話式ウィザード
├─ validate_config.py        # 設定検証 CLI
├─ run_execution.py          # ExecutionEngine 起動スクリプト
├─ run_monitoring.py         # SystemMonitor ポーリング起動スクリプト
├─ utils/
│  ├─ __init__.py
│  ├─ logging_setup.py       # ログ設定ユーティリティ
│  └─ process_priority.py    # プロセス優先度 / CPU affinity 設定
├─ monitoring/
│  ├─ monitoring_db.py       # DB 初期化 / 永続化
│  ├─ system_monitor.py
│  ├─ trade_monitor.py       # （コードベースに含まれる想定の監視）
│  ├─ risk_monitor.py
│  ├─ monitoring_engine.py
│  ├─ kill_switch.py
│  └─ alert_manager.py       # アラート送信（LINE などの実装想定）
├─ execution/
│  ├─ execution_engine.py    # ExecutionEngine（注文実行のコア）
│  ├─ broker_factory.py      # Broker クライアント生成（Mock/実ブローカー分岐）
│  ├─ order_manager.py
│  ├─ order_repository.py
│  ├─ reconciler.py
│  └─ risk_manager.py
├─ portfolio/
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ ai/
│  ├─ news_nlp.py            # ニュースセンチメント
│  └─ regime_detector.py     # レジーム判定
├─ monitoring/                # （上で列挙済）
└─ tools/
   ├─ __init__.py
   └─ paper_verification_report.py
```

（注）上記はコードベースから抽出した主要ファイル群の概観です。実際のリポジトリにはさらにモジュールや補助スクリプトが含まれる可能性があります。

---

## 開発 / テストに関するヒント

- 設定検証（validate_config）は起動前チェックに便利です。--strict モードで警告も失敗扱い可能。
- OpenAI を使う機能は単体テストでモック化してください。モジュールは _call_openai_api を内部で分離しているため差し替えが容易です。
- DB 初期化は init_monitoring_db が行います。テスト用に一時 DB（:memory: や data/test.db）を利用することを推奨します。
- ログはデフォルト logs/ に出力されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

## よくある質問

Q: 監視ループの間隔を変えたい  
A: 環境変数 MONITOR_POLL_INTERVAL に秒数を整数で設定できます（例: 30）。不正な値はデフォルト 60 秒にフォールバックします。

Q: 実行を強制停止させる方法は？  
A: data/kill.flag を作成すると KillSwitch により ExecutionEngine の停止が誘発されます（KillSwitch は条件評価で書き込みますが、手動で作成することも可能です）。逆に停止フラグによって run_execution の起動自体を抑止する箇所もあります。data/stop_requested.flag は run_* スクリプトの循環ループ停止に使われます。

Q: Paper Trading と Live の差分は何？  
A: KABUSYS_ENV=paper_trading のときはモックブローカーを使い、paper_trading 専用 SQLite DB（PAPER_TRADING_SQLITE_PATH）へ記録します。live では実ブローカー（kabuステーション）へ発注されます。

---

もし README に追記してほしい具体的な項目（例: config/*.yaml の詳細、API の呼び出しサンプル、CI 手順等）があれば教えてください。必要に応じて追記・拡張します。