# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）。

本 README は与えられたコードベースを元に、プロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・研究基盤の実装です。  
主な構成要素は以下の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を行うエンジン（本番 / ペーパートレード対応）
- Monitoring：システム監視・稼働状態・リスク監視・Kill Switch（異常時に ExecutionEngine を停止する仕組み）
- Research：DuckDB を使ったファクター計算・特徴量分析（オフライン分析 / 研究用途）
- AI モジュール：OpenAI を用いたニュースセンチメント評価（news_nlp）、市場レジーム判定（regime_detector）
- Tools：ペーパートレーディングの検証レポート生成などのユーティリティ
- Utilities：ログ設定、プロセス優先度設定、設定管理等の共通ユーティリティ

設計上の特徴：
- 設定は環境変数 / .env による管理（`.env` と `.env.local` の自動読み込み対応）
- 本番 DB とペーパートレード DB を分離（環境 `KABUSYS_ENV=paper_trading` 時は専用 DB に記録）
- DuckDB を分析用 DB として利用、SQLite を監視 / 発注履歴用に利用
- OpenAI API 統合：ニュースセンチメント・マクロセンチメントにより市場判定を行える（API キー必須）
- Kill Switch により重大なリスク検出時に ExecutionEngine を停止可能（フラグファイル方式）

---

## 機能一覧

- Execution
  - 実際のブローカー / モックブローカー（ペーパートレード）選択（`KABUSYS_ENV` に依存）
  - OrderManager / RiskManager / Reconciler による発注・約定管理
  - PID ファイル / stop フラグによる起動・停止制御
- Monitoring
  - system_status/trade_logs/positions/risk_logs/dashboard の永続化
  - SystemMonitor: CPU/メモリ/Disk/プロセス稼働、データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常などの監視（コード内に実装）
  - RiskMonitor: ドローダウン検出・ポジション数監視
  - KillSwitch：ドローダウンやポジション上限超過で `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送る
  - MonitoringEngine: 各監視をまとめて定期実行（ポーリング）
- Research
  - ファクター計算 (momentum, volatility, value)
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI 連携）
  - news_nlp: LLM による銘柄ごとのニュースセンチメント生成・ai_scores への書き込み
  - regime_detector: ETF 等のMA偏差とマクロニュースを用いた市場レジーム判定
- Tools
  - paper_verification_report: ペーパートレード DB から検証レポートを生成
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定検証 CLI

---

## 依存関係（主なもの）

（実際にはプロジェクトの requirements.txt を参照してください。ここではコードから明らかな主要パッケージを示します）

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（config の検証を行う場合に推奨）
- sqlite3（標準ライブラリ）

インストール例（最低限）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. Python 仮想環境の作成（任意）
```
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

3. 依存パッケージのインストール
```
pip install duckdb psutil openai PyYAML
```

4. `.env` ファイルの作成（対話式ウィザード推奨）
```
python -m kabusys.config_setup
```
このウィザードはプロジェクトルートの `.env` を生成／更新します。生成後は `python -m kabusys.validate_config` で検証してください。

主な環境変数（例）:
- JQUANTS_REFRESH_TOKEN=your_token
- KABU_API_PASSWORD=your_password
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO
- OPENAI_API_KEY=sk-xxxx (AI 機能を使う場合)

自動読み込み:
- `/path/to/project/.env` と `.env.local` がプロジェクトルートにあれば、起動時に自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

5. 必要に応じて `data/` ディレクトリや `logs/` ディレクトリを作成（起動時に自動作成されることもありますが、アクセス権等に注意）。

---

## 使い方

以下は主要なスクリプトとその使い方の概要です。各スクリプトはパッケージとして実行できます（モジュールとして実行）。

- ExecutionEngine を起動（発注エンジン）
```
python -m kabusys.run_execution
```
振る舞い：
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、`data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` で上書き可）に結果を記録します。
  - 起動前に `data/stop_requested.flag` が存在すると起動を中止します。
  - 実行中に `data/stop_requested.flag` が作成されるとエンジンを停止します。
  - PID を `data/execution.pid` に書きます。

- Monitoring を起動（監視ループ）
```
python -m kabusys.run_monitoring
```
振る舞い：
  - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - 監視は本番 sqlite_path を使用（`Settings.sqlite_path`）
  - 停止は `data/stop_requested.flag` の検知で行います

- 設定検証（起動前チェック）
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict  # 警告も失敗扱い
```

- ペーパートレード検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を直接指定:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI / ニューススコア（プログラム内から呼ぶ）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を利用

- Kill Switch（監視から呼ばれる）
  - `data/kill.flag` ファイルが書かれると、ExecutionEngine 側で停止信号として扱われます。
  - `KILL_FLAG_CLEAR_ON_START=1` を有効にすると起動時に自動クリアしますが、本番では `0` を推奨しています。

- ログ
  - ログは console (stdout) と日次ローテートファイル（デフォルト `logs/<app_name>.log`）に出力されます。
  - `LOG_DIR` を環境変数で上書き可能。ログレベルは `LOG_LEVEL` で指定します。

---

## 主要な設定項目（Settings クラスで参照）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用
- KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API 用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（ペーパー時に使用）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant, partial, never, reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- LOG_LEVEL, LOG_DIR

Settings は `kabusys.config.Settings` でラップされています。`.env` の自動読み込みはプロジェクトルートが特定できる場合に行われます。

---

## ディレクトリ構成（主要ファイル）

以下はコードベース内の主要モジュールとファイルのツリー（簡略）です。実際のリポジトリでは他のファイルやサブパッケージが存在する可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数 / .env の読み込み・Settings
    - config_setup.py               # 対話式 .env ウィザード
    - validate_config.py            # 設定検証 CLI
    - run_execution.py              # ExecutionEngine 起動スクリプト
    - run_monitoring.py             # SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py            # ログ設定ユーティリティ
      - process_priority.py         # プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py            # SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py            # （該当実装あり）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py            # （アラート管理、LINE 等、コード内で参照）
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
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
    - monitoring/                    # 上記
    - tools/
      - paper_verification_report.py
    - data/ (runtime)                # data/kill.flag, data/stop_requested.flag, data/*.db
    - logs/ (runtime)                # ログ保存先（デフォルト）

---

## 運用上の注意 / 推奨

- 本番運用前に `python -m kabusys.validate_config` で設定を検証してください。
- `KABUSYS_ENV=live` の場合は LINE 通知や kill flag の設定を特に確認してください（警告や注意が出ます）。
- Kill Switch は致命的なリスク時に ExecutionEngine を止めるための重要な仕組みです。`KILL_FLAG_CLEAR_ON_START` を本番で `1` にするのは危険です（自動クリアされるため）。
- OpenAI を使用する機能は API コストとレイテンシを考慮して運用してください（リトライ・フォールバックあり）。
- ログディレクトリのパーミッションとディスク空き容量に注意してください（ログが回転しつつ増える可能性があります）。

---

以上がこのコードベースの README です。必要であれば次の内容についてさらに詳細なドキュメント（API 使用例、設定ファイルサンプル、systemd / service ユニット例、テスト手順など）を追加できます。どのトピックを優先して深掘りしますか？