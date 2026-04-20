# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群です。  
本リードミーはリポジトリ内の主要モジュールから機能を抜粋して、導入・実行手順やディレクトリ構成を分かりやすくまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（アルゴリズム取引エンジン）用の共通ライブラリと管理ツール群を提供します。主な目的は以下です。

- シグナル生成・ポートフォリオ構築（portfolio）
- 注文管理・発注エンジン（execution）
- システム監視・リスク監視・Kill Switch（monitoring）
- 研究用ファクター計算（research）
- ニュース NLP を用いた AI スコアリング（ai）
- ユーティリティ（ロギング、プロセス優先度設定、設定管理）

重要な特徴:
- 本番（live）とペーパートレード（paper_trading）を環境変数で明確に分離
- DuckDB / SQLite を用いたデータ管理（時系列価格や監視ログ）
- OpenAI を利用したニュースセンチメント評価（ai モジュール）
- 起動スクリプト（run_execution / run_monitoring）でプロセス優先度やログを統一設定

---

## 主な機能一覧

- 設定管理
  - .env ファイルの自動ロード（`kabusys.config.Settings`）
  - 対話式 .env 作成ウィザード（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）

- 実行エンジン（Execution）
  - 実注文用 BrokerClient と MockBroker を環境に応じて切替
  - OrderManager / RiskManager / ExecutionEngine による発注制御
  - Paper trading（KABUSYS_ENV=paper_trading）では `data/paper_trading.db` を使用し本番 DB と分離

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor: 注文滞留や約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限などの定期チェック
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み、ExecutionEngine を停止させる
  - MonitoringEngine: 上記モニタ群のポーリングとアラート連携

- ポートフォリオ構築（Portfolio）
  - シグナルの候補選定、等金額/スコア重み付け、セクター上限適用、単元株丸め、リスクベースの株数計算

- 研究用 / 分析
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - DuckDB を用いた高速集計処理

- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア取得（`kabusys.ai.news_nlp.score_news`）
  - マクロニュースと ETF 指標で市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
  - OpenAI API 呼び出しは冪等性・リトライ・レスポンス検証を考慮

- ツール
  - Paper Trading 検証レポート生成（`python -m kabusys.tools.paper_verification_report`）

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化（例: venv）
   - 推奨: Python 3.9+（コードはタイプヒントを使用しており recent なバージョンを想定）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要なパッケージをインストール
   - 主に以下パッケージが必要です:
     - duckdb
     - psutil
     - openai
     - PyYAML （validate_config の YAML 検証に任意で使用）
   - 例:

   ```
   pip install duckdb psutil openai PyYAML
   ```

   （requirements.txt がある場合は `pip install -r requirements.txt`）

3. .env の作成
   - 対話式ウィザードで初期設定を行います:

   ```
   python -m kabusys.config_setup
   ```

   - 必須環境変数
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env は絶対にリポジトリへコミットしないでください。

4. 設定検証（起動前チェック）

   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. DB ディレクトリ等の初期化
   - デフォルトでは `data/` に SQLite / DuckDB ファイルが置かれます。必要に応じて `DUCKDB_PATH` / `SQLITE_PATH` を .env で変更してください。
   - ログは `logs/` に出力されます（`kabusys.utils.logging_setup` が作成）。

---

## 環境変数（主要）

- KABUSYS_ENV: execution 環境（development | paper_trading | live）、デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai 機能を利用する場合に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等は Settings により制御

設定の多くは `kabusys.config.Settings` で参照され、デフォルト値が設定されています。詳細は `src/kabusys/config.py` を参照してください。

---

## 使い方（主要コマンド）

- .env 作成（対話）:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- モニタープロセス起動:
  - デフォルトのポーリング間隔 60 秒。環境変数で変更可。
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します。

- 実行エンジン起動:
  - 本番/ペーパートレードは KABUSYS_ENV に応じて切替。
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - Execution は `data/execution.pid` を使用し、`data/stop_requested.flag` があれば起動しません。停止要求は `data/stop_requested.flag` を作成することで行います。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を個別指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（プログラム内で呼ぶ）
  - ニューススコア生成:
    ```
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")
    ```

---

## ロギングと PID / フラグ

- ログ:
  - `kabusys.utils.logging_setup.setup_logging(app_name=...)` によって標準出力と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- 停止フラグ / Kill Switch:
  - `data/stop_requested.flag` : run_execution / run_monitoring などの起動スクリプトが監視する外部停止フラグ（存在すれば起動を中止／実行中なら停止）。
  - `data/kill.flag` : KillSwitch により書き込まれ、致命的なリスク条件で ExecutionEngine を停止させるために使用されます。
  - `data/execution.pid` : ExecutionEngine の PID ファイル（管理用）。

---

## ディレクトリ構成

リポジトリの主要部分（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py         — ロギング設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB レイヤ
    - monitoring_engine.py     — 各モニタを束ねるエンジン
    - system_monitor.py        — システム状態 / データ鮮度監視
    - trade_monitor.py         — (注文系) 監視（存在を想定）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 管理
    - alert_manager.py         — (アラート送信)（存在を想定）
  - execution/
    - execution_engine.py      — 実行エンジン（EngineConfig, run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 株数算出・スケーリング
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — momentum / volatility / value ファクター
    - feature_exploration.py   — forward returns / IC / stats
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI + ETF 指標）
  - tools/
    - paper_verification_report.py — Paper Trading レポート生成

（実際のリポジトリには上記以外にも data/、logs/、config/ 等のディレクトリや追加モジュールが含まれる可能性があります）

---

## 開発・運用上の注意点

- .env は機密情報を含むため Git 管理しないこと（config_setup のヘッダにも注意書きあり）。
- KABUSYS_ENV=live を使う際は十分に注意すること（validate_config は live 時に警告を表示します）。
- OpenAI API 呼び出しには課金が発生する場合があるため、キー管理と呼び出し回数に注意してください。
- モジュールは DuckDB と SQLite を併用しています。DuckDB は分析用データ、SQLite は監視・トランザクションログなど軽量永続化用に想定されています。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存です。権限不足で設定できない場合は警告が出てスキップされます。

---

## よく使うコマンドまとめ

- .env を作る（対話）:
  - python -m kabusys.config_setup

- 設定チェック:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- モニタ起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に書かれている以上の詳細（内部実装・パラメータの微調整など）は各モジュールの docstring / ソースコードに記載されています。特定のモジュールや機能についてさらに詳細な説明や例が必要であれば、どの部分を深掘りしたいかを教えてください。