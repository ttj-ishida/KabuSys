# KabuSys

日本株向け自動売買システム（ライブラリ/実行スクリプト群）

このリポジトリは、戦略から発注、監視、ペーパートレード検証、研究用ユーティリティまでを含む自動売買基盤の一部実装です。モジュールは可能な限り副作用を避けた設計（純粋関数／明示的な DB 接続受け渡し）になっています。

---

## 概要

主なコンポーネント:

- ExecutionEngine：ブローカークライアントを用いた発注エンジン（本番／ペーパートレード対応）
- Monitoring：システム状態、注文状況、リスク（ドローダウン・ポジション上限）を定期チェック。Kill Switch によりエンジン停止指示を出せる
- Portfolio：銘柄選定・重み付け・株数計算などのポートフォリオ構築ロジック
- Research：DuckDB を用いたファクター計算・将来リターン計算・IC 解析など
- AI モジュール：ニュースを LLM（OpenAI）で解析し銘柄・マクロセンチメントを算出
- ユーティリティ：ログ設定、プロセス優先度設定、環境設定ウィザード／検証など
- ツール：Paper Trading の検証レポート生成スクリプト等

設計方針の一部:
- 環境依存値は .env / 環境変数で設定
- Paper Trading は本番 DB と分離（専用 SQLite）
- ルックアヘッドバイアスを避ける実装（target_date を明示して処理）
- フェイルセーフ（API 失敗時にフォールバックして継続）

---

## 機能一覧

- 環境設定ウィザード（.env の対話的生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の検査）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）: python -m kabusys.run_execution
  - Paper Trading 時は MockBrokerClient を使用し専用 DB に記録
- Monitoring 起動スクリプト（SystemMonitor のポーリング）: python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で変更可能
- Monitoring Engine（System / Trade / Risk 監視の統合）
- Kill Switch：kill.flag による ExecutionEngine 停止指示
- RiskMonitor：ドローダウン・ポジション数監視とリスクログ記録
- Portfolio モジュール：候補選定／重み計算／ポジションサイズ計算／セクター制限／レジーム乗数
- Research：モメンタム・ボラティリティ・バリュー等のファクター計算、IC 計測
- AI：
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector: マクロ + ma200 による市場レジーム判定
- Tools：
  - paper_verification_report: Paper Trading の実績を解析して PASS/FAIL レポートを出力

---

## 前提（Prerequisites）

- Python 3.10+
- 推奨パッケージ（主な依存）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/ YAML 検証・解析に必要、任意）
- OS: Linux / macOS / Windows（process priority は一部 OS で制限あり）

インストール例（仮に requirements.txt がない場合）:
```
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成・有効化し依存パッケージをインストール
   （上の「前提」を参照）

3. 環境変数設定（.env）
   - 対話式ウィザードで .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J‑Quants API）
     - KABU_API_PASSWORD（kabuステーション）
   - 重要な設定例（デフォルトは repo 内で参照可）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（DEBUG, WARNING, ERROR, CRITICAL）
     - OPENAI_API_KEY: OpenAI を使う場合必須（AI モジュール）

4. 設定検証:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告もエラー扱い
   ```

5. データディレクトリを作成（必要時）
   ```
   mkdir -p data logs
   ```

---

## 使い方（実行例）

- ExecutionEngine（本番 / ペーパートレード）起動
  - 通常（KABUSYS_ENV に応じて本番 or paper_trading）
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレードを明示的に実行する場合:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 注意:
    - paper_trading のときは settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB とは分離されます。

- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔の上書き:
    ```
    export MONITOR_POLL_INTERVAL=30   # 秒
    ```
    デフォルトは 60 秒。0 以下の値は無視されデフォルトにフォールバックします。

- 設定ウィザード
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
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI（ニューススコア・レジーム判定）
  - OpenAI API キーを環境変数に設定:
    ```
    export OPENAI_API_KEY=sk-...
    ```
  - モジュールをプログラムから呼び出す:
    ```py
    from kabusys.ai.news_nlp import score_news
    # conn: duckdb connection, target_date: datetime.date
    count = score_news(conn, target_date, api_key=None)  # api_key が None の場合 env を参照
    ```

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: INFO（DEBUG等も指定可）
- LOG_DIR: ログ保存先（デフォルト: logs）
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効、デフォルト 0）

---

## 停止・フラグ管理

- stop_requested.flag:
  - run_monitoring.py および run_execution.py は data/stop_requested.flag をチェックし、存在すると安全に停止します（外部から停止要求する場合に利用）。
- kill.flag:
  - KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送る（data/kill.flag、Settings.kill_flag_path でパスを変更可）。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動でクリアされる（本番環境では推奨されない設定）。

---

## ロギング

- ログ構成は kabusys.utils.logging_setup.setup_logging で集中管理されます。
- デフォルトではコンソール出力（stdout）と日次ローテーションのファイルハンドラを logs/<app_name>.log に出力。
- LOG_DIR 環境変数でログディレクトリを変更可能。ログディレクトリが作れない場合はコンソール出力のみで継続します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込みと Settings
  - config_setup.py          — 対話式 .env ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/               — 発注エンジン周り（broker_factory 等）
  - monitoring/
    - monitoring_db.py       — SQLite 監視ログ永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                    — データファイル（例: monitoring.db, kabusys.duckdb, paper_trading.db）
  - logs/                    — デフォルトログ保存先

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## 注意事項 / 運用上のヒント

- 本番運用時は KABUSYS_ENV=live を慎重に設定してください。validate_config は live 設定に対して追加警告を出します。
- Paper Trading は本番 DB と分離されますが、設定ミスで上書きしないよう .env を管理してください。
- OpenAI を使う機能は API 呼び出し回数・コストが発生します。API キーの管理と利用制限設定を検討してください。
- process priority / cpu affinity は OS 権限に依存します。権限不足時は設定がスキップされます（ログに警告）。
- DuckDB / SQLite のパスの親ディレクトリがない場合は警告が出ますが、起動時に自動作成されることがあります。必要に応じて事前に作成してください。

---

## 開発・拡張ポイント（参考）

- Portfolio の単元株（lot_size）は現状全銘柄共通。将来的に銘柄別 lot_map に拡張可能。
- position_sizing の価格欠損時のフォールバック（前日終値等）を強化すると安全になります。
- AI モジュールのレスポンス検証は堅牢化済み。必要に応じて別 LLM への対応やバッチサイズ調整を行ってください。
- monitoring のアラート配送（LINE 等）は AlertManager を拡張して複数チャネルに対応できます。

---

README に書かれている使い方で問題が生じた場合や追加のドキュメント（ER 図、API 仕様、運用手順書）が必要であれば教えてください。必要に応じてセッション起動手順や systemd / Supervisor 用のサンプルユニットも作成できます。