# KabuSys

日本株向けの自動売買システム（モジュール群）。ポートフォリオ構築、ポジションサイジング、発注実行（実売買 / ペーパートレード）、監視・アラート、研究用ファクター計算、ニュースNLP を含むツール群で構成されています。

---

## 概要

KabuSys は次のような関心事を分離して実装した Python パッケージです。

- Execution: 発注エンジン（実口座 or ペーパートレード）
- Monitoring: システム稼働監視、トレード監視、リスク監視、Kill Switch
- Portfolio: 候補選定・配分・ポジションサイズ計算、セクター制約・レジーム乗数
- Research: ファクター計算・特徴量探索（DuckDB を用いた分析）
- AI: ニュースの LLM によるセンチメント評価 / レジーム判定（OpenAI の利用を想定）
- Tools: ペーパートレード検証レポート等のユーティリティスクリプト
- Utils / Config: ロギング設定、プロセス優先度、環境設定読み込み/ウィザード 等

設計方針の一部：
- 設定は .env（自動ロード）または環境変数で与える。`config_setup` による対話式生成あり。
- 本番データベースとペーパートレード用 DB を分離（KABUSYS_ENV に応じて切替）。
- 監視は独立プロセスでポーリングし、kill.flag による停止信号を ExecutionEngine に送れる。
- LLM を呼ぶ処理はリトライや入力トリムなどフェイルセーフ寄りに実装。

---

## 主な機能一覧

- 発注エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して `data/paper_trading.db` に記録
  - プロセス優先度設定、PID ファイル出力、停止フラグ監視
- 監視ループ起動スクリプト: run_monitoring.py
  - システム状態・データ鮮度・取引ログ・リスク監視をポーリング
  - MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60 秒）
- 監視 DB 層（SQLite）: monitoring_db.py
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル定義／マイグレーション
- Kill Switch（kill.flag）: 異常検知時に書き込み、ExecutionEngine を停止させる仕組み
- Portfolio モジュール:
  - 候補選定、等金額/スコア加重、セクター制約、レジーム乗数、ポジションサイズ計算（丸め・上限・スケーリング）
- Research モジュール:
  - モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB接続で SQL を実行）
  - 将来リターン計算、IC（スピアマン）などの解析関数
- AI モジュール:
  - news_nlp.py: raw_news を集約し OpenAI に投げて銘柄別センチメントを ai_scores に書き込む
  - regime_detector.py: ma200 とマクロニュースの LLM スコアを合成し市場レジーム判定
- CLI ユーティリティ:
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env / config/*.yaml の前提チェック
  - tools.paper_verification_report: ペーパートレード実行結果の検証レポート生成

---

## 前提（主な依存）

必須（利用する機能に応じて）：
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- sqlite3（組み込み）
- PyYAML（config の厳密検証を行う場合。インストール済みであれば config/*.yaml のパースチェックを実行）

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリをプロジェクトルートにする。

2. 仮想環境を作成して依存をインストール（上記参照）。

3. .env を作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成（例は以下の主要項目を参照）。

4. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL にしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. 必要なディレクトリ（data, logs など）はスクリプト実行時に自動作成されることが多いですが、権限等の問題がある場合は手動で作成してください。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker 使用、ペーパートレード専用 DB に記録
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（本番）デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定振る舞い（instant|partial|never|reject、デフォルト instant）
- OPENAI_API_KEY: AI 機能で必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログの出力先ディレクトリ（デフォルト logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（開発用。0/1）

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine の起動（実行）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker としてペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 起動時に `data/execution.pid`（PID ファイル）を生成します。
  - 停止は `data/stop_requested.flag` を作るか、監視側が `data/kill.flag` を書き込むことで停止できます。

- Monitoring の起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能。
  - 監視は常に本番の sqlite_path を使う（環境にかかわらず本番監視 DB を参照）。

- Paper Trading 検証レポート（ツール）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

---

## 停止 / Kill Switch

- kill.flag（デフォルト: data/kill.flag）
  - KillSwitch はリスク監視等で発動した場合に `kill.flag` を書き込み、ExecutionEngine の起動時／稼働中に停止をトリガーします。
  - ExecutionEngine は `data/stop_requested.flag` または kill.flag の存在で停止処理を行います。
- stop_requested.flag（デフォルト: data/stop_requested.flag）
  - ローカルで強制停止したい場合に作成しておくと、run_execution/run_monitoring が検知して安全に終了します。
- KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると起動時に kill.flag を自動クリアします（注意: 本番では推奨されません）。

---

## ログ・DB の場所（デフォルト）

- ログ: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite DB: data/monitoring.db
- ペーパートレード SQLite DB: data/paper_trading.db

ログは daily ローテーション（30 日保持）になります。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ...（発注関連モジュール群）
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
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
  - data/ (実行時に生成されることが想定)
    - *.db, *.flag, *.pid
  - logs/ (デフォルトログ出力先)

---

## 開発メモ / 注意事項

- 全体設計として「外部 API 呼び出し（発注・LLM等）」は失敗時にフェイルセーフで進める（例: API 失敗時はスキップ／デフォルト値）。
- DuckDB を解析に利用し、SQL と Python を併用した実装が多くあります。テーブル名（prices_daily / raw_financials / raw_news 等）を想定して処理します。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup でもその旨の注意を出しています）。
- OpenAI を利用する機能は API キーの管理とコストに注意してください。API 呼び出しはバッチ化・リトライ・クリップ等により安全性を高めていますが、実行は自己責任でお願いします。
- 本番（KABUSYS_ENV=live）での起動前には validate_config の実行と、LINE 通知設定等の十分な確認を推奨します。

---

もし README に追加したい具体的な実行例（環境変数のテンプレートや systemd / Supervisor 用のユニットファイル例など）があれば教えてください。必要に応じてサンプルも作成します。