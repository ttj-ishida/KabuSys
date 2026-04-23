# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）の一部実装です。戦略・ポートフォリオ構築、発注エンジン、監視、Research ツール、AI（ニュース NLP / レジーム判定）等を含みます。

---

## プロジェクト概要

KabuSys は以下の機能を備えたモジュール群で構成されています（主に pure-Python で DB は SQLite / DuckDB を使用）:

- 発注・実行エンジン（ExecutionEngine、BrokerClientFactory 等）
- モニタリング／アラート（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch）
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ決定）
- リサーチ（ファクター計算、IC 計算、特徴量解析）
- AI サービス（ニュースのセンチメントスコアリング、レジーム判定：OpenAI 呼び出し）
- ユーティリティ（ロギング設定、プロセス優先度設定、設定読み込みウィザード・検証）
- ツール（Paper Trading の検証レポート生成）

設計方針の例：
- DuckDB を分析用に利用、SQLite を監視/発注履歴用に利用
- 環境に依存しない設定読み込み（.env / .env.local を自動読み込み）
- 本番・ペーパートレードを分離（KABUSYS_ENV）

---

## 主な機能一覧

- 環境設定ウィザード（.env を対話式で作成）：kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml のチェック）：kabusys.validate_config
- ExecutionEngine 起動スクリプト：kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
- Monitoring（System/Trade/Risk のポーリング）：kabusys.run_monitoring および MonitoringEngine
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 異常検知時に Kill Switch を書き込み、ExecutionEngine を停止できる
- Paper Trading 検証レポート生成スクリプト：kabusys.tools.paper_verification_report
- AI モジュール：
  - ニュース NLP（OpenAI を使った銘柄ごとのセンチメント -> ai_scores）
  - レジーム判定（ETF + マクロニュースを統合して 'bull' / 'neutral' / 'bear'）
- Portfolio モジュール（候補選定、重み計算、リスク調整、株数決定） — 純粋関数群でユニットテストしやすい
- utils：ログ設定（ログ回転）、プロセス優先度 / CPU affinity 設定 など

---

## セットアップ手順（ローカル開発向け）

以下は一般的な手順です。プロジェクト内に requirements ファイルがある場合はそちらを優先してください。

1. Python 環境を用意（3.9+ 推奨）
2. 必要パッケージをインストール（例）

   ```
   python -m pip install duckdb psutil openai
   ```

   - OpenAI 呼び出しを利用する場合は `openai`（もしくは新 API クライアント）をインストールしてください。
   - DuckDB、psutil は本リポジトリ内で使用しています。その他の依存は利用する機能により追加してください（PyYAML は validate_config の YAML 検証に任意）。

3. プロジェクトルートに移動（.git または pyproject.toml があるディレクトリを基準に自動で .env を検索します）。

4. 環境変数を設定
   - 対話式で作る（推奨）:

     ```
     python -m kabusys.config_setup
     ```

   - もしくは .env を直接作成。主なキー（必須）は以下。

     - 必須
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - 推奨 / 任意（デフォルト値あり）
       - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (ペーパートレード時の DB、デフォルト: data/paper_trading.db)
       - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
       - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知）
       - OPENAI_API_KEY（AI 機能利用時）
       - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading 時の約定モード

5. 設定検証（起動前チェック）:

   ```
   python -m kabusys.validate_config
   # strict モード（警告もエラー扱い）
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリやログディレクトリの作成は基本的に自動で行われますが、必要に応じて `data/` や `logs/` を作っておくとよいです。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（発注実行）
  - 本番/開発/ペーパートレードは KABUSYS_ENV で制御します。

  ```
  # ローカル開発（デフォルト KABUSYS_ENV=development）
  python -m kabusys.run_execution

  # ペーパートレードで起動（環境変数で切り替え）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  # 実際の本番
  KABUSYS_ENV=live python -m kabusys.run_execution
  ```

  注意:
  - run_execution は起動時に data/stop_requested.flag の存在をチェックし、存在する場合は起動を中止します。
  - 実行中は data/execution.pid（デフォルト）に PID を書きます。停止は停止フラグや kill.flag を用います（下記参照）。

- Monitoring を起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```

  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視ループは data/stop_requested.flag の検出で終了します。

- Kill Switch / Stop フラグ
  - Kill Switch（自動停止トリガー）: monitoring モジュールが条件を満たすと `data/kill.flag` を作成します。ExecutionEngine はこのファイルを検出して安全停止します。
  - 手動停止フラグ: `data/stop_requested.flag` を作ると run_monitoring / run_execution のループを終了させます。
  - ExecutionEngine の PID ファイルは `data/execution.pid`（デフォルト）。監視プロセスはこの PID を参照してプロセス稼働判定等を行います。

- Paper Trading 検証レポート生成

  ```
  # デフォルト DB パスは data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI モジュール（プログラムから呼び出す）
  - ニュース NLP（銘柄別センチメントを ai_scores に書き込む）

    例（スクリプト内）:
    ```
    from kabusys.ai.news_nlp import score_news
    # conn: duckdb connection, target_date: datetime.date, api_key: Optional[str]
    count = score_news(conn, target_date, api_key="sk-...")
    ```

  - レジーム判定（market_regime テーブルへ書き込む）:

    例:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

  - OpenAI API キーは引数で渡せます。引数未指定時は環境変数 `OPENAI_API_KEY` を参照します。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV — 'development' | 'paper_trading' | 'live'（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant | partial | never | reject）

詳細は `kabusys.config.Settings` のプロパティ実装を参照してください。

---

## ログ / ファイル

- ログディレクトリ（デフォルト）: logs/
  - 起動スクリプトごとに <app_name>.log を日次ローテートで出力します（30日分保持）。
- データディレクトリ（デフォルト）: data/
  - monitoring.db（SQLITE_PATH のデフォルト）
  - kabusys.duckdb（DUCKDB_PATH のデフォルト）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH のデフォルト）
  - stop_requested.flag, kill.flag, execution.pid などの制御ファイル

---

## ディレクトリ構成

主要なモジュールとファイルのツリー（src/kabusys 配下の抜粋）:

- src/
  - kabusys/
    - __init__.py
    - run_monitoring.py            # SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py             # ExecutionEngine 起動スクリプト
    - config.py                    # 環境変数 / Settings
    - config_setup.py              # .env 対話式ウィザード
    - validate_config.py           # 設定検証 CLI
    - utils/
      - logging_setup.py           # ロギング設定ユーティリティ
      - process_priority.py        # プロセス優先度 / affinity 設定
    - monitoring/
      - monitoring_db.py           # SQLite テーブル定義・DB 操作
      - system_monitor.py
      - trade_monitor.py           # （抜粋に含まれます）
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py           # アラート送信（LINE 等）実装想定
    - execution/
      - execution_engine.py        # ExecutionEngine 本体（参照）
      - broker_factory.py          # ブローカークライアント生成
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py       # 候補選定・重み計算
      - position_sizing.py         # 株数計算・スケール調整
      - risk_adjustment.py         # セクター制約・レジーム乗数
    - research/
      - factor_research.py         # Momentum / Volatility / Value など
      - feature_exploration.py     # 解析ユーティリティ（IC 等）
    - ai/
      - news_nlp.py                # ニュース NLP（OpenAI）
      - regime_detector.py         # レジーム判定（ETF + マクロニュース）
    - tools/
      - paper_verification_report.py

---

## 開発時の注意・運用上のポイント

- .env は絶対にリポジトリにコミットしないでください（config_setup.py の出力ヘッダにも警告あり）。
- KABUSYS_ENV によって動作や DB パスが変わる箇所があるため、本番時は `KABUSYS_ENV=live` の設定を慎重に確認してください（validate_config によるチェック推奨）。
- Monitoring は本番の ExecutionEngine を監視し、条件によって kill.flag を書き込みます。kill.flag が書かれると ExecutionEngine 側で安全停止する設計になっています。
- OpenAI を利用する機能は API 利用料が発生します。API エラーやレート制限に対してはリトライやフェイルセーフ（スコア 0 を代替）を入れていますが、運用ポリシーに合わせて設定を調整してください。
- DuckDB / SQLite のパスは Settings で簡単に上書きできます。開発環境と本番環境で DB を分けることを強く推奨します（特に paper_trading）。

---

## 参考コマンドまとめ

- .env 作成（ウィザード）:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- ExecutionEngine 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README を拡張します（例: 実行時のログサンプル、詳細な config/*.yaml の説明、CI/デプロイ手順、ユニットテストの実行方法など）。どの項目を追加したいか指示してください。