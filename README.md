# KabuSys

日本株向け自動売買システムのコードベース。シグナル生成、ポートフォリオ構築、発注実行、監視、研究用ユーティリティ、AI ベースのニュース解析などを含むモジュール群を提供します。

以下はリポジトリの概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は以下の責務を持つ Python パッケージ群です。

- リサーチ：ファクター計算、将来リターン、IC 計算など（DuckDB を利用）
- ポートフォリオ構築：候補選定、重み付け、セクター制約、ポジションサイズ算出（純粋関数）
- Execution（発注系）：Broker クライアントを介した発注（本番 / ペーパートレード分離）
- Monitoring（監視系）：システム稼働状況・注文ログ・リスク監視、Kill Switch の発動
- AI：ニュースのセンチメント（OpenAI）を使ったスコアリング、レジーム判定
- ツール：ペーパートレード検証レポート生成、設定ウィザード、設定検証 CLI
- 共通ユーティリティ：ロギング設定、プロセス優先度制御、設定読み込み

設計上の特徴：
- データ永続化には DuckDB（分析）と SQLite（監視・発注履歴）を使用
- ペーパートレードは本番 DB と分離（デフォルト: data/paper_trading.db）
- .env ベースの設定管理と対話式ウィザード / 検証ツールを提供
- 外部 API（OpenAI など）はキーを環境変数で渡す（フェイルセーフ実装あり）

---

## 主な機能一覧

- 設定管理
  - .env 自動ロード（.env / .env.local、OS 環境変数優先）
  - 対話式ウィザード: `kabusys.config_setup`
  - 起動前検証 CLI: `kabusys.validate_config`（--strict オプションあり）

- 実行・監視スクリプト
  - ExecutionEngine 起動: `src/kabusys/run_execution.py`（KABUSYS_ENV に応じてペーパー/本番を切り替え）
  - Monitoring ポーリング起動: `src/kabusys/run_monitoring.py`（MONITOR_POLL_INTERVAL で間隔変更可能）

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存 / データ鮮度監視
  - TradeMonitor: 発注ログのチェック（滞留注文、異常約定等）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: しきい値超過で data/kill.flag を書き込み Execution を停止

- 発注（Execution）
  - Broker クライアント抽象化（本番 / Mock）
  - OrderRepository / OrderManager / RiskManager / ExecutionEngine 等

- ポートフォリオ構築（純粋関数）
  - 候補選定（select_candidates）
  - 重み付け（等金額 / スコア加重）
  - セクター上限適用（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）

- 研究（Research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC、統計サマリー

- AI
  - ニュース NLP（OpenAI）で銘柄別センチメントを ai_scores に書き込む
  - レジーム判定（MA + マクロニュースセンチメント合成）

- ツール
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

- 共通ユーティリティ
  - ロギング設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（クロスプラットフォーム）

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化（例: pyenv/venv）
   - 推奨 Python バージョン: 3.10+（コードは型ヒント等で新しい機能を想定）

   例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（最低限の依存）
   - 必須: duckdb, psutil, openai
   - 開発時に便利: PyYAML（config 検証で使うが必須ではない）

   例:
   ```
   pip install duckdb psutil openai
   pip install PyYAML  # 任意（validate_config の YAML 検証用）
   ```

   （requirements.txt がある場合はそれを使用）

3. .env の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動でプロジェクトルートに `.env` を作り、必要変数を設定する。
     最低必須環境変数:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD

   - 主要な環境変数（デフォルト値はコメント）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - OPENAI_API_KEY — OpenAI を使う場合必須
     - PAPER_FILL_MODE — ペーパートレードの Fill モード (instant|partial|never|reject)

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要であれば）
   ```
   mkdir -p data logs
   ```

---

## 使い方（実行例）

- ExecutionEngine を起動（デーモン化は OS 側のサービス管理で行う）
  ```
  python -m kabusys.run_execution
  ```
  動作のポイント:
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_sqlite_path（デフォルト: data/paper_trading.db）へ記録。production DB と分離。
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動しない。
  - Execution は data/execution.pid（デフォルト）に PID ファイルを書きます。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  動作のポイント:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視テーブルを初期化します。
  - 停止は data/stop_requested.flag を作成するか、Ctrl+C（KeyboardInterrupt）。

- ペーパートレード検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```

- AI ベースのニューススコアリング（プログラム内呼び出し）
  - OpenAI API キーを環境変数にセット（または関数に渡す）
  - 例（スクリプト内）:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,20), api_key="sk-...")
    ```

- 設定ウィザード / 検証
  - 対話式 .env 作成:
    ```
    python -m kabusys.config_setup
    ```
  - 検証:
    ```
    python -m kabusys.validate_config
    ```

- ログ
  - デフォルトで stdout に出力され、logs/<app_name>.log に日次ローテートで保存されます（logs/ ディレクトリを指定しない場合は自動作成を試みます）。

- Kill / Stop
  - Execution を安全に停止させたい場合:
    - Kill Switch（監視からの自動写）: monitoring が検知して data/kill.flag を作成する
    - 手動で停止フラグを立てる: data/stop_requested.flag を作成すると run_* スクリプトが検知して停止
  - run_execution は実行中に stop flag を検知するとエンジンに stop() を要求します。

---

## 重要な環境変数（要点）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API 用

- 運用上重要
  - KABUSYS_ENV — development | paper_trading | live
    - paper_trading: Mock ブローカーを使用し DB を完全分離
    - live: 実際に発注を行う
  - OPENAI_API_KEY — AI モジュール使用時に必要
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - LOG_LEVEL — ログ出力レベル
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動ロード / Settings クラス
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py — 統一ロギング設定（stdout + 日次ファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・制約・丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュースセンチメント取得（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・読み書き層
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （trade モニタ実装ファイル）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の生成 / 管理
    - monitoring_engine.py — モニタ群の統合ループ
  - execution/（発注関連モジュール群）
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

- data/（実行時に使用するディレクトリ; デフォルト）
  - monitoring.db（SQLITE_PATH）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - kabusys.duckdb（DUCKDB_PATH）
  - execution.pid, stop_requested.flag, kill.flag など

- logs/
  - <app_name>.log（TimedRotatingFileHandler により日次ローテート）

---

## 開発時の注意点 / 実運用メモ

- DB の初期化
  - Monitoring は起動時に監視テーブルを冪等に作成します（init_monitoring_db）。
  - DuckDB のスキーマ（prices_daily/raw_financials 等）は別途データパイプラインで投入してください。

- ペーパートレードと本番 DB は分離されています。環境変数 `KABUSYS_ENV` の設定に注意してください。

- AI モジュール（news_nlp, regime_detector）は OpenAI API を呼びます。API のエラーはリトライやフォールバック（0.0）で安全に扱われますが、API キーは必須です。

- ロギング
  - アプリケーション全体で `setup_logging(app_name="...")` を使い統一的にログ出力しています。ログディレクトリの作成に失敗した場合はコンソールのみの出力になります。

- 停止方法
  - 手動停止: data/stop_requested.flag を作成またはスクリプト実行時に Ctrl+C
  - Kill Switch: 監視が自動的に data/kill.flag を作成して Execution を停止することがあります（しきい値超過時）

---

## よく使うコマンドまとめ

- 仮想環境作成・有効化
  - python -m venv .venv && source .venv/bin/activate

- 依存インストール
  - pip install duckdb psutil openai PyYAML

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行 / 監視プロセス起動
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要があれば README のサンプル .env や systemd / Docker 用の起動例、CI テスト例、より詳細なモジュール説明（各 API のパラメータや戻り値のドキュメント）を追加できます。どの部分を詳細化したいか教えてください。