# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群です。  
このリポジトリは、取引実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、AI 補助（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計されたモジュール群です。

- 自動売買の ExecutionEngine（発注・オーダー管理・リスク管理）の実装（run_execution.py）
- システム稼働監視 / リスク監視 / トレード監視のポーリング (run_monitoring.py, monitoring/*)
- ポートフォリオ構成（候補選定・重み計算・株数算出・セクター制約等） (portfolio/*)
- リサーチ用モジュール（ファクター計算・特徴量探索） (research/*)
- AI を用いたニュースセンチメント / 市場レジーム判定（OpenAI） (ai/*)
- ユーティリティ（設定読み込み、ログ設定、プロセス優先度など） (utils/*)
- ツール類（ペーパートレード検証レポート等） (tools/*)
- 設定ウィザード / 設定検証 CLI（config_setup.py / validate_config.py）

設計方針の一部：
- 環境依存設定は .env（または環境変数）で行う。config.Settings を経由して取得。
- Paper Trading（KABUSYS_ENV=paper_trading）時は実口座とデータを分離。
- 可能な限り副作用を抑え、冪等性・フェイルセーフを重視。

---

## 主な機能一覧

- Execution
  - ブローカークライアント抽象化（BrokerClientFactory）
  - ExecutionEngine（発注セッションの起動 / 停止）
  - OrderManager / OrderRepository / Reconciler / RiskManager
  - Paper Trading 用モッククライアントと専用 DB 分離

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、実行プロセス監視
  - TradeMonitor: 発注ログの監視（滞留注文、約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限検出
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine 停止
  - MonitoringEngine: 各モニタを統合して周期的に監視・アラート発行
  - 永続化: SQLite に監視ログを格納（monitoring_db.py）

- Portfolio / Position sizing
  - 候補選定（スコア降順、上位 N）
  - 重み算出（等金額・スコア加重）
  - セクター上限適用
  - ポジションサイズ計算（リスクベース / 等分配 / スコアベース、単元株丸め、aggregate cap）

- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー 等）
  - 将来リターン・IC 計算・統計サマリー（外部依存を極力排した実装）
  - DuckDB を利用した分析向け処理

- AI（OpenAI）
  - ニュースを LLM でスコアリングして ai_scores に書き込む（news_nlp.score_news）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - 再試行・バリデーション・部分書き込みで安全性を確保

- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - 設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）

---

## セットアップ手順

前提:
- Python 3.9+（型注釈や一部ライブラリの互換性に依存）
- SQLite（標準ライブラリ）
- システム上での DB ファイル格納用に repository ルートに `data/` ディレクトリを作ると便利

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 必須: duckdb, psutil, openai
   - 任意（YAML 検証用）: PyYAML
   例:
   ```
   pip install duckdb psutil openai
   pip install pyyaml   # オプション（validate_config で YAML パースを有効にする場合）
   ```

   ※ requirements.txt は本リポジトリに含まれていないため、上記を参考に環境へ追加してください。

3. プロジェクトルートに .env を用意
   - 対話式で作る場合:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作る場合は .env.example（ない場合は README を参照）を参考に最低限以下を設定してください:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV (development / paper_trading / live)
     - (OpenAI を使う場合) OPENAI_API_KEY

   注意: .env は決して Git にコミットしないでください。

4. 設定チェック
   ```
   python -m kabusys.validate_config
   # 警告を厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. データ / ログ用ディレクトリを作成（必要なら）
   ```
   mkdir -p data logs
   ```

---

## 使い方

主要な実行スクリプト・モジュールの例です。

- ExecutionEngine（発注実行）を起動
  - 通常起動:
    ```
    python -m kabusys.run_execution
    ```
  - 動作概要:
    - KABUSYS_ENV によって本番 / ペーパートレードを切り替え
    - Paper Trading の場合は専用 DB（data/paper_trading.db がデフォルト）を使用
    - 起動時に pid ファイルを作成し、data/stop_requested.flag により停止可能

- Monitoring（監視）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 動作概要:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定（デフォルト 60）
    - 常に本番の sqlite_path（監視 DB）を使用して記録
    - stop_requested.flag を検知するとループを終了

- 設定ウィザード（.env の生成）
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
  # 期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュールの呼び出し（ライブラリ的利用）
  - ニューススコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    # target_date は date 型（例: datetime.date(2026,4,1)）
    score_news(conn, target_date, api_key="sk-...")
    ```
  - レジームスコア:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

- ログ設定
  - ログは kabusys.utils.logging_setup.setup_logging を通して統一的に出力されます。
  - 環境変数:
    - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
    - LOG_DIR: ログディレクトリ（デフォルト: logs/）
  - run_* スクリプトは自動で setup_logging を呼び出します。

- プロセス優先度
  - run_* スクリプトは起動時に set_process_priority("high") を呼び出します（権限がない場合は警告を出してスキップ）。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- SQLITE_PATH — 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（default: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイル（default: data/kabusys.duckdb）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL — 監視ポーリング秒（run_monitoring で使用）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など

validate_config.py で必須項目のチェックが可能です。

---

## 停止・Kill スイッチの挙動

- Monitoring と Execution はフラグファイルによる外部制御を行います。
  - 監視ループ停止フラグ: data/stop_requested.flag（run_monitoring / run_execution が参照）
  - Kill スイッチ: data/kill.flag — KillSwitch が書き込むと ExecutionEngine の停止を促す
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除します（本番では推奨されません）。

---

## ディレクトリ構成

主要なファイル・ディレクトリ構造（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py        # （存在は示唆されているが詳細実装はここでは除外）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        # （アラート送信ロジックがある想定）
  - execution/
    - execution_engine.py    # ExecutionEngine 実装（参照）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                    — 実行時に利用するファイル群（logs/、DB ファイル等はプロジェクトルートに作成）
  - logs/                    — デフォルトのログ出力先

（上記は本コードベースに含まれるモジュール群を抜粋したものです。実装ファイルの完全な一覧はリポジトリを参照してください。）

---

## 開発・運用上の注意事項

- .env（認証情報・シークレット）は決して Git に含めないこと。
- KABUSYS_ENV が `live` の場合は特に注意して設定を確認する（validate_config の警告を参照）。
- OpenAI を用いる機能は API コストとレート制限に注意。API 失敗時はフェイルセーフでスコアをスキップまたはデフォールト値にフォールバックする実装になっていますが、使用方針は慎重に。
- ペーパートレードモード（paper_trading）は本番 DB と分離され、data/paper_trading.db を使用します。検証・テスト時は必ずこちらで動作確認してください。
- ログディレクトリの作成失敗時はファイルハンドラが無効になり、コンソールのみで出力されます。

---

## 参考コマンド一覧

- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate

- 依存パッケージインストール
  - pip install duckdb psutil openai
  - pip install pyyaml  # 任意

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動
  - python -m kabusys.run_execution

- Monitoring 起動
  - python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば、インストール手順の例（requirements.txt 作成）、各モジュールの API 使用例、monitoring/trade_monitor の詳細、ExecutionEngine の実行フロー図などを追加できます。どの部分を詳しく書き起こしますか？