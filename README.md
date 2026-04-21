# KabuSys

日本株自動売買システムの軽量コアライブラリ群。バックテスト・リサーチ・ポートフォリオ構築・実行/監視/リスク管理・AI を利用したニュース解析などの機能を含む。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコアとなる Python モジュール群です。主な目的は以下：

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制約）
- ExecutionEngine による発注管理（本番 / ペーパートレードの分離）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- OpenAI を使ったニュース NLP によるセンチメント評価
- 構成ウィザード・検証ツール・検証レポート生成ツール

設計方針としては、モジュール間の結合を低く保ち、DB（DuckDB / SQLite）を明確に分離している点が特徴です。

---

## 主な機能一覧

- 環境変数 / .env の読み込みと Settings 管理（`kabusys.config`）
- 対話式 .env 作成ウィザード（`kabusys.config_setup`）
- 起動前設定検証 CLI（`kabusys.validate_config`）
- 実行エンジン起動スクリプト（`run_execution.py`）
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、ペーパートレード用 DB に記録
- 監視（System / Trade / Risk）とポーリングループ起動スクリプト（`run_monitoring.py`）
  - `MONITOR_POLL_INTERVAL` でポーリング間隔をオーバーライド可能（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を参照（環境に依存せず）
- 監視用永続化（SQLite）ラッパー（`kabusys.monitoring.monitoring_db`）
- Kill Switch（`data/kill.flag`）による ExecutionEngine 停止
- ポートフォリオ構築ユーティリティ（選定、等配分・スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数）
- リサーチ：ファクター計算、将来リターン、IC 計算、統計サマリー（DuckDB を使用）
- AI モジュール：
  - ニュース NLP（OpenAI）で銘柄別センチメントを計算し `ai_scores` に書き込み
  - レジーム判定（ETF MA + マクロニュースの LLM センチメントを合成）
- ツール：
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## 必要条件（依存パッケージ）

主に以下を想定しています（プロジェクトに requirements.txt がある場合はそれを参照してください）:

- Python 3.9+
- duckdb
- psutil
- openai
- (任意) PyYAML — `validate_config` の YAML 検証に使用

インストール例:

```bash
python -m pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを取得

2. Python 環境を準備し、必要パッケージをインストール

3. .env の作成
   - 対話式ウィザードを推奨:

     ```bash
     python -m kabusys.config_setup
     ```

   - 作成後、`python -m kabusys.validate_config` で検証（`--strict` で警告も失敗扱い）:

     ```bash
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict
     ```

4. DB ファイルとディレクトリ
   - デフォルト:
     - DuckDB: `data/kabusys.duckdb`
     - SQLite(監視): `data/monitoring.db`
     - Paper trading SQLite: `data/paper_trading.db`
   - 必要に応じて `.env` の `DUCKDB_PATH` / `SQLITE_PATH` / `PAPER_TRADING_SQLITE_PATH` を編集

5. OpenAI を使用する場合は `OPENAI_API_KEY` を設定

6. 実行前に（本番時）`KABUSYS_ENV` を `live` に設定することで本番モードになります（注意して扱ってください）

---

## 使い方

重要なスクリプトの実行例を示します。

- 実行エンジン（ExecutionEngine）を起動

  - 本番/開発/ペーパートレードは KABUSYS_ENV による（例: `paper_trading`）

  ```bash
  # 例: ペーパートレードで起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

  - ペーパートレード時は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に完全分離して記録されます。

  - 停止はプロセスに対する通常のシグナル（Ctrl+C）や、監視側が `data/kill.flag` を書き込むことで行えます。`run_execution` は `data/stop_requested.flag` の存在も監視して終了します。

- 監視ループを起動

  ```bash
  # MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60 秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  - 監視は本番 sqlite_path（`.env` の `SQLITE_PATH`）を常に使用します。
  - 停止フラグ: `data/stop_requested.flag` が存在するとループを終了します。

- .env の対話式作成

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート生成

  ```bash
  # デフォルトの paper db を使う
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB 指定
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュールの呼び出し（ライブラリ API）
  - ニュース NLP を使って得点を生成する例（ライブラリ関数）:

    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 20), api_key="YOUR_OPENAI_API_KEY")
    ```

  - OpenAI API キーは引数で与えるか環境変数 `OPENAI_API_KEY` を使用します。

---

## 主要構成ファイル・設定項目（抜粋）

- 必須環境変数
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 重要な環境変数（デフォルトを持つもの）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（デフォルト: INFO）
  - OPENAI_API_KEY（AI 機能利用時に必須）
  - MONITOR_POLL_INTERVAL（監視スクリプトのポーリング間隔）

- ログ
  - ログはデフォルトで `logs/` に出力（TimedRotatingFileHandler、日次ローテーション、30日保持）
  - `kabusys.utils.logging_setup.setup_logging(app_name="...")` を各スクリプトで呼ぶことで統一的に設定される

---

## 停止 / Kill Switch の挙動

- Kill Switch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります（`KillSwitch.evaluate` が監視イベントから条件を判断して作成）。
- 監視ループと実行エンジンは `data/stop_requested.flag` を見て自発的に終了します。
- `KILL_FLAG_CLEAR_ON_START` を `1` にすると起動時に `kill.flag` を自動クリアします（本番では `0` 推奨）。

---

## ディレクトリ構成

（このリポジトリの `src/kabusys` を想定した代表的な構成）

- kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数・Settings 管理、自動 .env ロード
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（テーブル初期化・CRUD）
    - system_monitor.py — システム監視（CPU/MEM/DISK、データ鮮度、プロセス生存）
    - trade_monitor.py — 発注関連監視（滞留注文、約定異常など）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書き込み / クリア
    - monitoring_engine.py — 各 Monitor の統合とアラート起動ループ
    - alert_manager.py — （アラート送信ラッパー: LINE 等）（実装がある想定）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（発注セッション管理）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 実行系コンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・資金割当
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC 計算・統計サマリー
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py — レジーム判定（ETF MA + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ — 実行時に使われる DB / フラグ / pid ファイルを格納する想定ディレクトリ（例: monitoring.db, paper_trading.db, kill.flag, execution.pid）

---

## 注意点 / 運用上のヒント

- KABUSYS_ENV を `live` にした場合は本番での発注が行われます。パラメータ・鍵類の管理・LINE 通知設定を事前に十分確認してください。
- .env は絶対にバージョン管理にコミットしないでください（`config_setup.py` も README に警告の注記あり）。
- OpenAI の呼び出しは API の失敗に対してリトライ・フェイルセーフを実装していますが、API キーやクオータ管理は運用者側で注意してください。
- 監視は監視 DB（SQLite）にログを残します。監視系は本番 sqlite_path を参照するため、テスト時はパスを分けるか注意してください。
- `psutil` を用いた優先度設定は OS に依存します。権限不足等で設定に失敗した場合はログに警告が出ますが処理は継続します。

---

## 開発者向け情報

- 単純関数群（portfolio / research / utils）は DB に副作用を持たない設計になっているため、ユニットテストが容易です。
- AI 関連関数は API 呼び出し部分を分離しており、テスト時は該当関数をモックできます（コメントにテスト方針あり）。
- DuckDB を用いる関数は SQL 内で集約処理を行うため、大量データ処理に適しています。

---

以上がこのコードベースの README.md 相当の概要と基本的な使い方です。必要であれば、セットアップ手順（シェルスクリプト化）、環境変数の .env.example、または運用ガイド（デプロイ / systemd / Supervisor 用定義）のテンプレートも作成します。どの情報を優先して追加しますか？