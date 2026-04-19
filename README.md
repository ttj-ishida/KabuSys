# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ群・起動スクリプト・ツール）。  
この README はコードベースの主要コンポーネントと使用方法、セットアップ手順を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を念頭に設計されたモジュール化されたシステムです。主な機能は以下の通りです。

- 発注実行エンジン（ExecutionEngine）とブローカークライアントの抽象化
- 実行状態の監視（System / Trade / Risk モニタ）と Kill Switch（危険時の強制停止）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算、セクター制限）
- 研究用モジュール（ファクター計算、将来リターン、ICなど）
- AI を使ったニュースセンチメント（OpenAI）によるスコアリング / レジーム判定
- ペーパートレード検証用のレポート生成ツール
- .env ベースの設定ウィザード / 設定検証 CLI
- ログ設定・プロセス優先度など運用ユーティリティ

設計方針の一部：
- DuckDB を用いた分析・研究ワークフロー。
- SQLite を監視・トレードログ用に使用（本番/ペーパーで分離可能）。
- 外部 API 呼び出し（OpenAI など）は明示的なキー指定 / 環境変数を必要とし、フェイルセーフに配慮。

---

## 機能一覧（主なモジュール）

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV による paper_trading 対応）
  - run_monitoring.py — SystemMonitor のポーリングループを起動

- 設定関連
  - config.py — 環境変数読み込み・Settings クラス
  - config_setup.py — .env の対話式ウィザード
  - validate_config.py — 設定検証 CLI

- モニタリング（monitoring）
  - monitoring_db.py — 監視用 SQLite テーブル定義 / ラッパー
  - system_monitor.py / trade_monitor.py / risk_monitor.py — 各種監視ロジック
  - monitoring_engine.py — 各 Monitor を束ねる実行ループ
  - kill_switch.py — フラグファイルによる ExecutionEngine 停止

- 実行（execution）
  - ブローカーファクトリ / ExecutionEngine / OrderManager / Reconciler / RiskManager（実装は別ファイル群）

- ポートフォリオ（portfolio）
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算・資金配分・単元丸め
  - risk_adjustment.py — セクター上限・レジーム乗数

- 研究（research）
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - feature_exploration.py — 将来リターン、IC、統計サマリー

- AI（ai）
  - news_nlp.py — OpenAI を使ったニュースセンチメント集約・スコア保存
  - regime_detector.py — MA とマクロニュースセンチメントの合成によるレジーム判定

- ツール（tools）
  - paper_verification_report.py — ペーパートレードの Pass/Fail 検証レポート生成

- ユーティリティ（utils）
  - logging_setup.py — 統一ログ設定（コンソール + 日次ローテート）
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

---

## 前提・依存関係

- Python 3.10 以上（typing の | 演算子などが使われています）
- 必須パッケージ（一部例）
  - duckdb
  - psutil
  - openai
- 任意（機能による）
  - PyYAML（config/*.yaml の内容を検証する場合）
- SQLite は標準ライブラリで提供されます。

pip でのインストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai PyYAML
```

※ requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を用意する。

2. 依存パッケージをインストール（上記参照）。

3. .env の作成
   - 対話式で作成する:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードに従って J-Quants トークン、kabu API パスワードなどを設定します。
   - 自動ロード挙動:
     - プロジェクトルートにある `.env` と `.env.local` は自動で読み込まれます（OS 環境 > .env.local > .env の順）。
     - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 設定の検証
   ```
   python -m kabusys.validate_config
   ```
   必須環境変数やファイルパスの基本チェックが行われます。`--strict` を付けると警告も失敗扱いになります。

5. データディレクトリ確認
   - デフォルトファイルパス（.env で上書き可）
     - DuckDB: data/kabusys.duckdb
     - Monitoring (SQLite): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / Kill flag: data/execution.pid / data/kill.flag

6. ログディレクトリ
   - デフォルトは `logs/`。権限により作成できなければコンソール出力のみになります。

---

## 使い方（起動・ツール）

基本的にモジュールはパッケージ単位で実行できます。

- ExecutionEngine（実行エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、ペーパートレード用 DB（デフォルト: data/paper_trading.db）に分離して記録します。
  - 起動時に `data/stop_requested.flag` が存在するとエンジンは起動せず終了します。
  - 実行中は `data/execution.pid` に PID を書きます。

- Monitoring（監視）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書きできます。
  - Monitoring は本番用の sqlite_path を常に使用して監視ログを記録します。
  - 停止は `data/stop_requested.flag` の作成で行います。

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db path/to/paper_trading.db
  ```
  - デフォルト DB: data/paper_trading.db（環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可）
  - 出力は標準出力のテキストレポート。稼働率・注文成功率・P95 レイテンシ等を評価して PASS/FAIL を出します。

- .env の作成 / 編集
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- AI モジュールをプログラムから利用する例（簡易）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  written = score_news(conn, target_date=date(2026, 4, 11), api_key='sk-...')
  print(f"ai_scores に書き込んだ銘柄数: {written}")
  ```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
- OPENAI_API_KEY（AI 機能で使用）
- PAPER_FILL_MODE（paper_trading 時の約定モード: instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（本番での自動 kill フラグクリア設定 0/1）

注意: Settings クラスで未設定の必須変数は ValueError を投げます。`.env.example` を参考に `.env` を作成してください。

---

## 運用メモ

- Kill Switch:
  - risk_monitor の判定で kill.flag（デフォルト: data/kill.flag）を書き込むと ExecutionEngine に停止シグナルを送れます。KillSwitch class にて作成・検出・削除が可能です。
  - 本番では KILL_FLAG_CLEAR_ON_START は 0（自動クリアしない）を推奨します。

- 停止フラグ:
  - run_execution/run_monitoring はプロジェクトルートの `data/stop_requested.flag` を監視して安全にループを終了します。

- ログ:
  - 各アプリ（monitoring / execution 等）は logging_setup により `logs/<app_name>.log` に日次ローテーションで出力します。
  - ログディレクトリに書けない場合はコンソール出力のみになります。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB にカラムが無い場合は ALTER TABLE による簡易マイグレーションを行います。

---

## ディレクトリ構成（抜粋）

（リポジトリの src/kabusys 配下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照されるがここでは抜粋のみ)
  - execution/
    - execution_engine.py (実行エンジン)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成される)
    - monitoring.db (default)
    - kabusys.duckdb (default)
    - paper_trading.db (paper_trading 用)

（プロジェクトルート）
- .env, .env.local（環境変数）
- config/*.yaml（設定テンプレート）
- logs/（ログ出力）
- data/（db, pid, flag 等）

---

## 開発・テストに関する補足

- DuckDB を使った研究モジュールは、prices_daily / raw_financials / raw_news 等のテーブルを前提とします。実データ投入が必要です。
- AI 機能は OpenAI API に依存します。テスト時は API 呼び出し部分をモックすること（モジュール内に `_call_openai_api` が分離されており、ユニットテストで差し替え可能）。
- config_setup と validate_config を組み合わせて初期セットアップと自動チェックを行ってください。

---

## よくある質問（FAQ）

- Q: paper_trading と live を同一 DB にしてよいですか？  
  A: 推奨されません。run_execution は paper_trading の場合に専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。

- Q: Monitoring はどの DB を使いますか？  
  A: Monitoring は環境にかかわらず本番の sqlite_path（Settings.sqlite_path）を使用します。

- Q: .env をコミットしてよいですか？  
  A: 絶対にコミットしないでください。.env は機密情報を含みます。

---

必要であれば、README に以下を追記できます:
- requirements.txt の推奨内容
- systemd / Supervisor / docker-compose の例（運用用）
- 詳細な API 使用例（AI モジュールや ExecutionEngine のプログラム的利用）
- config/*.yaml のサンプルと generate_config.py の説明

追加してほしい項目があれば教えてください。