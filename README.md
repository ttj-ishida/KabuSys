# KabuSys

日本株自動売買システムの軽量コアライブラリ群と起動スクリプト群です。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）等の主要コンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件
- セットアップ手順
- 使い方（実行例）
- 重要な環境変数
- 停止・Kill スイッチ
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。  
主な役割は以下の通りです。

- ExecutionEngine: 発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）。
- Monitoring: システム稼働状況・注文ログ・リスク監視を行う監視サブシステム。Kill Switch による外部停止機能を備える。
- Portfolio モジュール: 候補選定、重み計算、ポジションサイズ決定、セクター上限などの純関数群。
- Research モジュール: ファクター計算・特徴量探索用ユーティリティ（DuckDB 経由で履歴データを参照）。
- AI モジュール: ニュースセンチメント（OpenAI）を用いたスコアリング、レジーム判定。
- ユーティリティ: ロギング設定、プロセス優先度設定、設定読み込みウィザード、設定検証ツールなど。

---

## 主な機能一覧

- 設定管理（.env の自動読み込み / Settings クラス）
- 対話式 .env 作成ウィザード（kabusys.config_setup）
- 起動前の設定検証 CLI（kabusys.validate_config）
- 実行エンジン起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading で MockBrokerClient を利用し、本番 DB と分離して data/paper_trading.db を使用
  - プロセス優先度を High に設定
  - pid ファイルの出力（data/execution.pid）
- 監視ループ起動スクリプト（kabusys.run_monitoring）
  - ポーリング間隔のカスタマイズ（MONITOR_POLL_INTERVAL）
  - Monitoring は環境に関わらず production sqlite_path を使用して監視ログを記録
- 監視サブシステム
  - SystemMonitor（CPU / メモリ / ディスク / データ鮮度 / 実行プロセス検出）
  - TradeMonitor（注文滞留・異常約定の検出 等）
  - RiskMonitor（ドローダウン検出・ポジション上限監視 等）
  - KillSwitch（条件発生時に data/kill.flag を書き込み、ExecutionEngine を停止）
  - AlertManager（LINE などの通知プラグイン用のフック）
- Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- DuckDB を使ったリサーチ処理（ファクター計算・前方リターン・IC 等）
- OpenAI を利用したニュース NLP（スコアリング、レジーム判定） — API キー必須

---

## 前提条件

- Python 3.9+
- 必要パッケージ（用途に応じて）
  - duckdb
  - psutil
  - openai （AI 機能を利用する場合）
  - PyYAML（設定ファイルの検証に必要。無くても動作するが警告を出す）
- ディレクトリ権限: データ・ログ用のディレクトリ（デフォルト `data/`, `logs/`）へ書き込み可能であること

パッケージのインストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（OpenAI を使わない場合は openai のインストールは不要です）

---

## セットアップ手順

1. リポジトリをクローンしてソースルートへ移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化し依存をインストール（上記参照）。

3. .env ファイルの作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を参考に手動作成（リポジトリに例ファイルがあれば参照してください）。

4. 設定検証（起動前に推奨）
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いになります
   python -m kabusys.validate_config --strict
   ```

5. 必要なデータディレクトリを準備（通常は自動作成されますが、手動で確認できます）
   - data/ （デフォルト DB やフラグファイルを格納）
   - logs/ （ログ出力先）

---

## 使い方

主要なエントリポイント（パッケージモジュールを -m で実行）:

- ExecutionEngine を起動（本番 / ペーパートレードに応じて KABUSYS_ENV を設定）
  ```bash
  # 本番（注意して使用）
  export KABUSYS_ENV=live
  python -m kabusys.run_execution

  # ペーパートレード
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  実行時の挙動:
  - プロセス優先度を High に設定（可能な環境で）
  - paper_trading の場合は MockBrokerClient を利用し `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ記録
  - 起動前に `data/stop_requested.flag` が存在すると起動せず終了

- Monitoring を起動
  ```bash
  # デフォルトポーリング間隔 60 秒
  python -m kabusys.run_monitoring

  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  特記事項:
  - Monitoring は KABUSYS_ENV に関わらず production の sqlite_path（Settings.sqlite_path）を使用して監視ログを書き込みます
  - 停止はプロセスに対する KeyboardInterrupt か、リポジトリルート下 `data/stop_requested.flag` を作成すると監視ループが終了します

- .env 作成ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB (env か --db で指定)、期間指定可能
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI モジュールを使った処理（ライブラリ呼び出し）
  - ニューススコアリング（例: Python から）
    ```python
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    ```
  - レジーム判定
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,11), api_key="sk-...")
    ```

---

## 重要な環境変数（抜粋）

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると ExecutionEngine 起動時に kill.flag を自動クリア（本番では 0 推奨）

- データベース / ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の pid ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）

- ログ関連
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: ログファイル保存先（デフォルト logs/）

- Monitoring
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）

- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY または各関数の api_key 引数

- Paper Trading の動作モード
  - PAPER_FILL_MODE: instant / partial / never / reject（デフォルト "instant"）

---

## 停止方法 / Kill スイッチ

- 停止フラグ（run_execution / run_monitoring が参照）
  - data/stop_requested.flag を作成すると実行中のループが検出して安全終了します。

- Kill Switch（リスクトリガーにより ExecutionEngine を停止）
  - KillSwitch は条件に応じて data/kill.flag（Settings.kill_flag_path）を書き込みます。
  - ExecutionEngine はこの kill.flag の存在を検出して停止する設計です。
  - 起動時に kill.flag を自動で削除するには KILL_FLAG_CLEAR_ON_START=1 を設定します（本番での自動クリアは危険なので慎重に）。

---

## ロギング

- 共通のロギング設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - コンソール(stdout) と日次ローテートされるファイル出力（logs/<app_name>.log）を設定します
  - ログディレクトリは自動作成を試みますが失敗するとファイル出力は無効化され、コンソールのみ出力されます

---

## ディレクトリ構成（主要ファイル）

```
src/kabusys/
├── __init__.py
├── config.py                     # Settings / .env 自動ロード
├── config_setup.py               # .env 対話ウィザード
├── validate_config.py            # 起動前の検証ツール
├── run_execution.py              # ExecutionEngine 起動スクリプト
├── run_monitoring.py             # Monitoring 起動スクリプト
├── utils/
│   ├── __init__.py
│   ├── logging_setup.py          # ログ設定ユーティリティ
│   └── process_priority.py       # プロセス優先度 / affinity
├── execution/                     # 発注・実行関連（ブローカー、エンジン、リスク等）
│   ├── ... (OrderManager, ExecutionEngine, Reconciler, RiskManager など)
├── monitoring/
│   ├── monitoring_db.py          # SQLite テーブル定義・DB ラッパー
│   ├── system_monitor.py
│   ├── trade_monitor.py
│   ├── risk_monitor.py
│   ├── monitoring_engine.py
│   ├── kill_switch.py
│   └── alert_manager.py
├── portfolio/
│   ├── portfolio_builder.py
│   ├── position_sizing.py
│   └── risk_adjustment.py
├── research/
│   ├── factor_research.py
│   └── feature_exploration.py
├── ai/
│   ├── news_nlp.py               # ニュース NLP スコアリング
│   └── regime_detector.py        # レジーム判定
├── data/                         # （実行時に利用されるデフォルトパス）
│   ├── monitoring.db             # デフォルト監視 DB（自動作成）
│   └── paper_trading.db          # ペーパートレード DB（環境により使用）
└── tools/
    └── paper_verification_report.py
```

各サブディレクトリ内に多数の補助モジュールがあり、上記は主要ファイルの抜粋です。

---

## 補足 / 注意事項

- Monitoring は明示的に「監視用」DB（Settings.sqlite_path）へ記録します。run_monitoring は KABUSYS_ENV に依存せず本番の sqlite_path を使用する点に注意してください（監視データは一元的に管理するため）。
- ExecutionEngine は paper_trading モード時に DB を分離します（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を利用する機能は API 呼び出しを含むため、利用はコストとレイテンシの観点で注意してください。API キーは環境変数や引数で安全に渡してください。
- 本 README はコードベースの主要挙動をまとめたものであり、個別モジュールの詳細な API は該当ソースコメントを参照してください。

---

必要があれば、特定コンポーネント（ExecutionEngine の起動フロー、Monitoring のアラート連携、AI モジュールのテスト方法など）に関する詳しいドキュメントを追加で作成します。どの部分を深掘りしますか？