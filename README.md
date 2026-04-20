# KabuSys

日本株向けの自動売買システムのモジュール群です。本リポジトリは以下の主要機能を提供します：マーケットリサーチ（ファクター計算）、ポートフォリオ構築、ポジションサイズ計算、発注エンジン（ExecutionEngine）・監視（Monitoring）・リスク管理、ニュースNLP を用いた AI スコアリング、ペーパートレード検証レポート生成など。

この README ではプロジェクト概要、機能一覧、セットアップ手順、使い方（主要コマンド例）、ディレクトリ構成を日本語でまとめています。

注意: 実行スクリプトは Python モジュールとして起動する想定です（例: python -m kabusys.run_execution）。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成する複数コンポーネントを含むライブラリ兼実行環境です。設計方針の一部は次の通りです。

- 各モジュールは可能な限り純粋関数／副作用の少ない実装（research / portfolio 等）を志向。
- 発注系（Execution）は実行環境（KABUSYS_ENV）によりペーパートレードと本番を分離。
- 監視（Monitoring）はプロセス／データ鮮度／注文状況／リスクを定期チェックし、Kill Switch（flag ファイル）で安全停止できる。
- ニュース NLP（OpenAI）を用いたセンチメント算出と市場レジーム判定をサポート。
- ログは標準出力（stdout）と日次ローテートファイル（logs/<app>.log）へ出力。

---

## 主な機能一覧

- Execution（発注エンジン）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - MockBroker を使ったペーパートレード（データは data/paper_trading.db に保存）
  - RiskManager / OrderManager / Reconciler による発注管理

- Monitoring（監視）
  - SystemMonitor: CPU/MEM/DISK、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新、risk_logs 記録
  - KillSwitch: 条件（ドローダウン等）で data/kill.flag を書き込み、ExecutionEngine を停止

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額 / スコア加重配分、リスクベース配分、単元丸め、セクターキャップ適用、レジーム乗数

- Research（リサーチ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマン）などの統計解析ユーティリティ

- AI（ニュース NLP / レジーム判定）
  - OpenAI を用いたニュースセンチメント（ai_scores への保存）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（market_regime 書き込み）

- ユーティリティ
  - .env 対話式生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

---

## 必要な依存パッケージ（例）

最低限必要な主要パッケージ（バージョンは適宜）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証を行う場合）
- その他: 標準ライブラリ

pip でのインストール例（requirements.txt がない場合は個別インストール）:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

---

## 環境変数（主要）

重要な環境変数（一部）:

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用トークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。既定は development
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

.env の自動読み込み:
- プロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` が自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

サンプル（最低限）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル）

1. リポジトリをクローンしてワークディレクトリへ移動

2. Python 仮想環境作成と依存インストール

```
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt   # ある場合
# または最低限:
pip install duckdb psutil openai pyyaml
```

3. .env を作成（対話式推奨）

```
python -m kabusys.config_setup
```

対話で入力するか、テンプレ .env を手動で作成してください。

4. 設定検証

```
python -m kabusys.validate_config
# 警告をエラー扱いにする場合:
python -m kabusys.validate_config --strict
```

5. データディレクトリ等の作成（必要に応じて）

```
mkdir -p data logs
```

---

## 実行・使い方

主要な実行スクリプトと説明:

- Execution（発注エンジン）起動

  ペーパートレードで起動（KABUSYS_ENV=paper_trading）:

  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  本番（live）で起動する場合は KABUSYS_ENV=live とし、設定・トークン類を必ず確認してください。

  実行挙動:
  - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へデータを記録します。
  - 起動時に data/stop_requested.flag が存在すれば起動をしない仕様。
  - 実行中は data/execution.pid に PID が書き込まれます（設定による）。

- Monitoring（監視）起動

  ```
  python -m kabusys.run_monitoring
  ```

  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視プロセスは KABUSYS_ENV にかかわらず「本番の sqlite_path」（SQLITE_PATH）を使用して監視 DB に接続します。

  停止方法:
  - プロセス停止（Ctrl+C）またはプロジェクトルートの data/stop_requested.flag を作成するとループを抜けます。

- .env 作成ウィザード

  ```
  python -m kabusys.config_setup
  ```

- 設定検証

  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成

  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（スクリプト起動は提供されていないが、関数を呼び出して利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  いずれも OpenAI API キー（OPENAI_API_KEY）を環境変数か引数で与える必要があります。

ログ:
- setup_logging により stdout と logs/<app>.log（日次ローテート）へ出力されます。ログディレクトリは環境変数 LOG_DIR またはデフォルト `logs/`。

Kill Switch（安全停止）:
- KillSwitch は監視結果に基づき `data/kill.flag` を作成します。ExecutionEngine 起動時や定期チェックで存在検査を行い、安全に停止します（KILL_FLAG_CLEAR_ON_START=1 により起動時自動クリアも可、ただし本番では注意）。

---

## ディレクトリ構成（主要ファイル／モジュール）

以下は src/kabusys 以下の主要なモジュールとその役割です。

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数の集中管理・自動 .env ロード
  - config_setup.py
    - 対話式 .env 生成ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py: ログ設定ユーティリティ（stdout + 日次ファイル）
    - process_priority.py: プロセス優先度 / CPU affinity 設定
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - position_sizing.py: 発注株数計算（リスクベース等）
    - risk_adjustment.py: セクター上限・レジーム乗数
  - research/
    - factor_research.py: ファクター計算（momentum, volatility, value）
    - feature_exploration.py: 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py: ニュースを OpenAI で評価し ai_scores を書き込む
    - regime_detector.py: MA200 + マクロセンチメントで市場レジーム判定
  - monitoring/
    - monitoring_db.py: SQLite モデル層（テーブル作成・永続化 API）
    - system_monitor.py: システム状態 / データ鮮度監視
    - trade_monitor.py: （滞留注文等の監視）※主要ロジックあり
    - risk_monitor.py: ドローダウン・ポジション上限検出
    - kill_switch.py: kill.flag 管理
    - monitoring_engine.py: 各 Monitor を束ねる実行エンジン
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
      - 発注フロー / ブローカークライアント抽象化 / リスク制御など（主要実装ファイル）
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト

- data/
  - 実行時に使用される SQLite / flag / pid ファイルが置かれる想定ディレクトリ（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid, data/stop_requested.flag）

- logs/
  - ログファイル出力先（logs/<app>.log）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では .env の内容、LINE 通知設定、Kill Switch の設定などを慎重に確認してください。validate_config が本番向けの警告を出します。
- Monitoring は KABUSYS_ENV にかかわらず（run_monitoring）本番の SQLITE_PATH を参照します。開発環境で監視 DB を分離したい場合は SQLITE_PATH の値を切り替えてください。
- ExecutionEngine の停止には data/kill.flag（Kill Switch）または data/stop_requested.flag（run_execution の停止フラグ）を使います。flag ファイルを直接編集する運用は確実な手順を定めてください。
- OpenAI 等の外部 API を使う機能は API キー漏洩に注意して管理してください。テスト時はモック化が可能な設計になっています。

---

## 開発・テストのヒント

- 設定検証（validate_config）と対話式 .env 作成（config_setup）を活用して初期設定を整えてください。
- DuckDB 接続は research / ai モジュールで頻用します。分析用データを DuckDB にロードしてから各種ファクター計算を実行してください。
- AI 呼び出しはリトライやバックオフ、レスポンスバリデーションを実装していますが、テスト時は外部呼び出しを patch / mock してください（モジュール内でテスト用の差替えしやすい設計になっています）。

---

必要に応じて README を拡張します。特に以下があれば追記できます：

- requirements.txt / pyproject.toml をもとにしたインストール手順
- ExecutionEngine の詳細な設定例（risk config / engine config）
- CI / デプロイ手順（systemd / docker / supervisor 等での運用例）
- API（関数）リファレンスの自動生成や簡易サンプルコード

ご要望があれば特定セクションを詳述します。