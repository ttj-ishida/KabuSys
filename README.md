# KabuSys (README)

以下はこのコードベース（KabuSys：日本株自動売買システム）の README です。導入・起動方法、主要機能、ディレクトリ構成などを日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買および研究/モニタリングを目的としたモジュール群です。  
設計方針として以下を重視しています：

- 実行（ExecutionEngine）と監視（Monitoring）を分離して安全に運用可能
- ペーパートレード（完全分離された DB）をサポート
- DuckDB を使った分析 / リサーチ機能（ファクター計算等）
- LLM（OpenAI）を利用したニュースセンチメント評価・レジーム判定（任意）
- .env による設定管理 + 対話式ウィザード / 検証ツールを提供

バージョン: 0.1.0（パッケージ __init__ より）

---

## 主な機能一覧

- Execution
  - 実際の発注処理を担当する ExecutionEngine（run_execution.py）
  - Paper Trading モード（モックブローカー、別 DB に記録）
  - リスク管理（RiskManager）、注文管理（OrderManager）、リコンサイル（Reconciler）

- Monitoring
  - システム資源・プロセス・データ鮮度の定期監視（run_monitoring.py）
  - 監視ログの永続化（SQLite）
  - Kill Switch（閾値を超えた場合に停止フラグを書き込む仕組み）
  - アラート発行（AlertManager 経由。LINE 連携等の仕組みあり）

- Portfolio Construction（純粋関数群）
  - 候補選定、等金額/スコア加重配分、ポジションサイズ計算、セクターキャップ、レジーム乗数

- Research
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等

- AI（任意）
  - ニュース記事に対する LLM ベースのセンチメントスコアリング（news_nlp）
  - ETF 指標＋マクロニュースを用いた市場レジーム判定（regime_detector）

- ユーティリティ
  - .env 初期作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポートジェネレータ（tools/paper_verification_report.py）
  - ログ設定・プロセス優先度設定ユーティリティ

---

## 前提 / 必要環境

- Python 3.10+ を推奨（typing / modern libs を考慮）
- 必須パッケージ（想定）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定ファイルの検証を行う場合）
- 標準ライブラリ: sqlite3, logging, threading, datetime など

（プロジェクトに requirements.txt がなければ、上記を仮想環境にインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリを取得し、Python 仮想環境を作成する
2. 依存パッケージをインストールする（上記参照）
3. .env を作成（対話式ウィザード推奨）
   - 実行:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```
     python -m kabusys.validate_config
     ```
     --strict オプションで警告もエラー扱いにできます
4. 必要であればデータディレクトリを作成:
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
5. OpenAI を利用する場合は API キーを設定:
   - 環境変数: OPENAI_API_KEY

---

## 主な環境変数（要・推奨設定）

必須（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用 / 推奨:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBroker を使い data/paper_trading.db に記録します
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存先（デフォルト logs/）
- OPENAI_API_KEY — OpenAI を使う場合に必須
- PAPER_FILL_MODE — ペーパートレード時の約定モデル（instant|partial|never|reject、デフォルト "instant"）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"1"=有効）

設定は .env/.env.local から自動ロードされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

---

## 使い方（起動・実行）

- 設定の作成・検証
  - 対話式ウィザード:
    ```
    python -m kabusys.config_setup
    ```
  - 検証:
    ```
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict
    ```

- 監視ループ起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒指定（デフォルト 60）
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```

  - 特記事項:
    - run_monitoring は監視用 DB に常に本番 sqlite_path を使います（KABUSYS_ENV に依存せず）。
    - 停止はプロジェクトルート/data/stop_requested.flag の作成で行う（存在を検知してループ終了）。

- 実行エンジン起動（ExecutionEngine）
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動をしません。
    - 実行中は data/execution.pid を使用してプロセス管理します。
    - 停止は run_execution が定期的に data/stop_requested.flag を監視し、検知で engine.stop() を呼び出します。

- Paper Trading 検証レポート
  - 例:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB 指定オプション:
    --db でパスを指定するか、PAPER_TRADING_SQLITE_PATH 環境変数を使用

- AI 機能
  - ニューススコアリングやレジーム判定は OpenAI API を利用（OPENAI_API_KEY 必須）
  - 各モジュールの関数はプログラム内から呼び出す想定（例: kabusys.ai.score_news）

---

## 停止・Kill Switch

- Graceful stop:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution はその存在を検知して安全に停止します。
- Kill Switch:
  - 監視ロジックにより重大イベント（例: ドローダウン閾値超過等）が発生すると monitoring 側の KillSwitch が data/kill.flag を書き込みます。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（ただし本番では 0 を推奨）。
- PID:
  - 実行中の Execution は data/execution.pid を利用します。

---

## ロギング

- ログは以下の通り出力されます：
  - コンソール（stdout）: 常に出力
  - ファイル: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30日分保持）
- ログ設定機能は kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます。
- LOG_DIR 環境変数でログディレクトリを指定可能

---

## ディレクトリ構成（主要ファイル）

プロジェクトルート（抜粋）:

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, ...（テンプレ/生成スクリプトあり）
- data/
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード用)
  - kill.flag, stop_requested.flag, execution.pid など
- logs/
  - execution.log, monitoring.log, ...（日次ローテート）
- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数ロード / Settings
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py
      - process_priority.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
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
    - data/ (モジュール化されたデータパイプライン等)

（実際のフルツリーはリポジトリを参照してください。ここでは主要ポイントのみ列挙しています。）

---

## 開発・テストのヒント

- 設定検証や .env の作成は開発の初動で必ず行ってください。
- Paper Trading を利用すると本番 DB と分離して安全に動作確認できます（KABUSYS_ENV=paper_trading）。
- AI 周り（OpenAI）をテストする場合は API 呼び出しをモック化する設計が用意されています（内部関数を patch してテスト可能）。
- DuckDB を使ったリサーチ関数は DB 接続を引数に取る純粋な関数群なので、テスト用 DB を用意してユニットテストを書けます。

---

## 参考コマンドまとめ

- ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 監視開始:
  ```
  python -m kabusys.run_monitoring
  ```
- 実行エンジン開始:
  ```
  python -m kabusys.run_execution
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に記載してほしい追加情報（依存パッケージの正確なバージョン、起動時の systemd/cron のサンプル、CI 設定、より詳細なディレクトリツリー等）があれば教えてください。必要に応じて追記します。