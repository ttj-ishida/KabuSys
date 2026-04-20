# KabuSys

日本株向け自動売買フレームワークのサブセット実装。システム監視、ペーパートレード用の検証ツール、ファクター計算、ポートフォリオ構築、LLM を使ったニュースセンチメント評価などのユーティリティ群を含みます。

---

## プロジェクト概要

KabuSys は以下の役割を持つモジュール群で構成されています。

- ExecutionEngine（発注エンジン）とその周辺（order_repository / order_manager / reconciler / risk_manager 等）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine）
- 研究用モジュール（ファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出・セクター制限）
- AI モジュール（OpenAI を用いたニュース NLP と市場レジーム判定）
- CLI ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

設計方針の例：
- データ永続化に SQLite（監視用）/ DuckDB（分析用）を併用
- Paper Trading は本番 DB と完全分離（data/paper_trading.db を使用）
- LLM 呼び出しはフェイルセーフでリトライ／スキップする実装

---

## 主な機能一覧

- 設定ウィザード（.env の対話作成）: python -m kabusys.config_setup
- 設定検証 CLI（環境変数・config/*.yaml の簡易チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker を使用）: python -m kabusys.run_execution
  - Paper トレード時の DB: data/paper_trading.db（環境変数で上書き可能）
- Monitoring のポーリング起動スクリプト: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）
  - Monitoring は環境にかかわらず本番 sqlite_path を使用
- Kill Switch 実装（data/kill.flag）による ExecutionEngine の停止通知
- RiskMonitor によるドローダウン・ポジション上限の監視とログ記録
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report
- 研究用ファクター計算（momentum / volatility / value）および特徴量解析（IC 等）
- ニュース NLP（OpenAI を使用した銘柄別センチメント算出）と市場レジーム判定

---

## 必要要件（推奨）

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証時に使用。任意）
- SQLite は標準ライブラリで利用可能

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成と依存ライブラリのインストール（上記参照）

3. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   必須の環境変数（最低限設定するもの）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   主要な環境変数（既定値あり）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - LOG_LEVEL: INFO など
   - OPENAI_API_KEY: OpenAI を使う場合必須

4. データディレクトリの準備（自動で作られることもありますが手動で作る場合）
   ```
   mkdir -p data logs
   ```

5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も失敗扱い
   ```

---

## 使い方

- 実行（ExecutionEngine）
  - 本番／Paper の挙動切替は KABUSYS_ENV により制御
  - Paper Trading の場合、専用 DB に記録され、本番 DB と分離されます
  ```
  python -m kabusys.run_execution
  ```
  停止制御:
  - 停止を即時伝えたい場合はプロジェクトルートの `data/stop_requested.flag` を作成してください（run_execution/run_monitoring はこれを検知して正常終了します）。
  - ExecutionEngine の外部停止（注文停止の Kill Switch）は `data/kill.flag` で行います（Monitoring 側が判定して書き込む）。

- 監視ループ（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を設定できます（例: export MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 関連
  - ニューススコアリングやレジーム判定は OpenAI API キー（OPENAI_API_KEY）が必要です。
  - モジュール API を直接呼ぶ場合、DuckDB 接続オブジェクトを渡して利用します（ユーティリティ関数: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。

- ログ
  - ログはデフォルトで stdout と `logs/<app_name>.log`（日次ローテーション）へ出力されます。LOG_DIR で出力先を変更できます。
  - ログレベルは LOG_LEVEL 環境変数または .env で設定します。

---

## 重要な挙動・ファイル

- data/kill.flag — Kill Switch（存在すると ExecutionEngine は停止対象と判定される）
- data/stop_requested.flag — 手動停止フラグ（run_* スクリプトが検知して終了）
- data/execution.pid — 実際に ExecutionEngine が PID を書き込むファイル（run_execution のデフォルト）
- data/monitoring.db — 監視ログ（SQLite。Settings.sqlite_path による）
- data/paper_trading.db — Paper Trading 用監視 DB（KABUSYS_ENV=paper_trading 時）
- data/kabusys.duckdb （または DUCKDB_PATH で指定）— 分析用 DuckDB

---

## ディレクトリ構成

（抜粋: 主要モジュールを中心に示します）
```
src/
  kabusys/
    __init__.py                # パッケージ定義、バージョン
    config.py                  # 環境変数 / Settings 管理（自動 .env ロード機能含む）
    config_setup.py            # .env 対話ウィザード
    validate_config.py         # 設定検証 CLI

    run_execution.py           # ExecutionEngine 起動スクリプト
    run_monitoring.py          # Monitoring ポーリング起動スクリプト

    utils/
      logging_setup.py         # ログ設定ユーティリティ
      process_priority.py      # プロセス優先度 / CPU affinity ユーティリティ

    monitoring/
      monitoring_db.py         # SQLite テーブル初期化 + DB 操作ラッパ
      system_monitor.py        # システム / データ鮮度監視
      trade_monitor.py         # （注文監視ロジック）
      risk_monitor.py          # ドローダウン・ポジション監視
      kill_switch.py           # Kill Switch 実装
      monitoring_engine.py     # 各 Monitor を束ねる

    execution/                  # ExecutionEngine 関連（発注ロジック等）
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
      ...

    portfolio/
      portfolio_builder.py      # 候補選定・重み計算
      position_sizing.py       # 株数算出・資金制限・丸め処理
      risk_adjustment.py       # セクター上限・レジーム乗数

    research/
      factor_research.py       # Momentum/Value/Volatility 等のファクター計算
      feature_exploration.py   # IC 等の解析ユーティリティ
      ...

    ai/
      news_nlp.py              # ニュースの LLM センチメント評価
      regime_detector.py       # 市場レジーム判定（MA + LLM 合成）
      ...

    tools/
      paper_verification_report.py  # Paper Trading 検証レポート生成
```

---

## 開発・運用上の注意

- KABUSYS_ENV によって挙動が変わります。`live` は本番扱いのため十分な注意（LINE 通知設定、Kill Switch 設定等）が必要です。
- .env はバイナリやパスワードを含むため Git にコミットしないでください（config_setup でも明記しています）。
- OpenAI 呼び出しはネットワーク障害や API 制限に対してリトライ実装がありますが、APIキーやコスト面に注意してください。
- DuckDB / SQLite のファイルパスは環境変数で変更できます。運用時はバックアップや運用ポリシーを検討してください。
- ログディレクトリ作成に失敗するとファイル出力は無効化され stdout のみになります。LOG_DIR の権限設定に注意してください。

---

## 参考コマンド一覧

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- Execution 起動
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README の内容や CLI の使い方について追加説明が必要でしたら、どの箇所を詳しく書くか教えてください（例: 実運用での systemd/cron 設定例、データベースの初期投入手順、OpenAI API の利用上限対策など）。