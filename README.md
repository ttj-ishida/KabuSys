# KabuSys — 日本株自動売買システム

簡潔な説明: KabuSys は日本株の自動売買（発注エンジン）と運用監視・研究ツール群を含むパッケージです。発注ロジック、ポートフォリオ構築、資金管理、監視・アラート、AI ベースのニュース NLP／レジーム判定、検証レポート生成などの機能を備えています。

---

目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 使い方（コマンド例）
- 重要な環境変数
- 停止・Kill スイッチの使い方
- ログ
- ディレクトリ構成（概要）

---

プロジェクト概要
- 自動売買 Engine（ExecutionEngine）とそれを監視する Monitoring コンポーネントを中心に、研究・ポートフォリオ構築、AI ベースのニューススコアリング等を提供するモジュール群。
- SQLite / DuckDB をローカル DB として使用し、Paper Trading（ペーパー取引）モードと本番モードを分離して運用可能。
- OpenAI を利用したニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）を実装している（APIキー必須）。

---

主な機能
- Execution:
  - 実際の発注を行う ExecutionEngine（kabuステーション等のブローカークライアントを利用）
  - Paper Trading モード（MockBrokerClient）で本番 DB と完全分離された data/paper_trading.db に記録
  - Order 管理、リスクマネジメント（RiskManager）、Reconciler 等を含む
- Monitoring:
  - SystemMonitor（CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック）
  - TradeMonitor、RiskMonitor（ドローダウンやポジション上限監視）
  - KillSwitch（条件に応じて停止フラグを作成）
  - MonitoringEngine（複数の Monitor をまとめてポーリング）
  - 永続化層 MonitoringDB（SQLite）
- 研究/解析:
  - research モジュール: ファクター算出（momentum/value/volatility）、将来リターン・IC 計算、統計要約
  - portfolio モジュール: 候補選定、等金額/スコア加重、セクターキャップ、ポジションサイジング
- AI（OpenAI）:
  - news_nlp: ニュースを集約して LLM で銘柄ごとのセンチメントを算出し ai_scores に格納
  - regime_detector: ETF (1321) の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール:
  - paper_verification_report: Paper Trading DB のパフォーマンス／稼働性レポート生成
- 設定管理:
  - .env ウィザード（config_setup.py）で対話的に .env を生成
  - validate_config.py で起動前検証（必須環境変数・ファイルの存在チェックなど）

---

必要条件
- Python 3.10 以上（型注釈で PEP 604 の Union 型表記などを使用）
- 主な Python ライブラリ（実行する機能によって必要なライブラリが変わります）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML （config 検証で YAML の解析を行う場合）
- ネットワーク接続（本番ブローカーや OpenAI を利用する場合）
- ディスク領域（logs/ や data/ に書き込み可能であること）

依存パッケージの例インストール:
```bash
python -m pip install duckdb psutil openai pyyaml
```

---

セットアップ手順（簡易）
1. リポジトリをクローン／配置してプロジェクトルートに移動
2. Python 仮想環境を作成してアクティベート
3. 必要なパッケージをインストール（上記参照）
4. .env の準備（対話ウィザード推奨）
   - 対話的に作成:
     ```bash
     python -m kabusys.config_setup
     ```
   - 作成後、設定を検証:
     ```bash
     python -m kabusys.validate_config
     # --strict を付けると警告も FAIL 扱いになる
     python -m kabusys.validate_config --strict
     ```
5. data/ と logs/ ディレクトリが自動作成されるが、権限問題などがあれば手動で作成してください。

デフォルトファイルパス（.env で上書き可能）
- DuckDB: data/kabusys.duckdb
- SQLite (monitoring): data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- PID ファイル（Execution）: data/execution.pid
- Kill フラグ（KillSwitch）: data/kill.flag
- Stop フラグ（手動停止検知）: data/stop_requested.flag
- ログディレクトリ: logs/（日次ローテート、30日保持）

---

使い方（起動例 / CLI）
- Execution（エンジン）を起動:
  - 通常モード（KABUSYS_ENV を .env で設定）
    ```bash
    python -m kabusys.run_execution
    ```
  - Paper Trading:
    - .env の KABUSYS_ENV を paper_trading にするか、環境変数で指定:
      ```bash
      export KABUSYS_ENV=paper_trading
      python -m kabusys.run_execution
      ```
    - Paper Trading 用 DB のパスを変更する場合:
      ```bash
      export PAPER_TRADING_SQLITE_PATH=/path/to/data/paper_trading.db
      ```
- Monitoring（監視ループ）を起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き（秒単位。1 秒以上）:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視は本番 DB を前提）。
- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- Paper Trading 検証レポート:
  ```bash
  # デフォルト DB (data/paper_trading.db) を使用
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

---

重要な環境変数（抜粋）
- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境:
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- データベース:
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE — Paper Trading の約定動作（instant|partial|never|reject、デフォルト: instant）
- ロギング:
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログ保存先（デフォルト: logs/）
- AI:
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で必須）
- 監視／Kill:
  - PID_FILE_PATH — Execution の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — KillSwitch のフラグパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- その他:
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

詳細は kabusys/config.py を参照してください。

---

停止方法 / Kill スイッチ
- 手動停止（両スクリプトで共通）:
  - 監視・実行ループはプロジェクトルート/data/stop_requested.flag の存在を監視しています。ファイルを作成すると次回ループ時に安全に停止します。
    ```bash
    touch data/stop_requested.flag
    ```
  - 監視側から Execution 停止要求を出す（KillSwitch）と data/kill.flag が書き込まれます。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると起動時に自動でクリアしますが、本番では 0 推奨です。
- Ctrl+C（KeyboardInterrupt）でも安全に停止します。

---

ログ
- ログ設定は kabusys.utils.logging_setup.setup_logging により統一的に管理されます。
- デフォルトはコンソール（stdout） + 日次ローテートのファイル出力（logs/<app_name>.log）で、30 日分保持。
- 起動スクリプト（monitoring / execution）はそれぞれ app_name="monitoring" / "execution" でログを出力します。

---

ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・Settings クラス
  - config_setup.py          # .env 対話ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  # Paper Trading レポート生成
  - execution/               # Execution に関する実装群（OrderManager 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py       # SQLite schema & MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
  - portfolio/               # ポートフォリオ構築ロジック（純関数群）
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/                # 研究用ファクター・解析モジュール
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            # OpenAI を使ったニュースセンチメント
    - regime_detector.py     # レジーム判定
    - __init__.py
  - data/ (実行時に生成される)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading モード)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/ (実行時に生成される) 
    - monitoring.log
    - execution.log

---

開発メモ / 注意点
- Settings は起動時にプロジェクトルートの .env / .env.local を自動読み込みします（OS 環境変数が優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効にできます。
- Monitoring は監視目的のため、本番 sqlite_path（SQLITE_PATH）を参照する設計です。監視が本番 DB を対象にすることを意図しています。
- Execution の Paper Trading は本番 DB と分離された paper_sqlite_path を使用します（settings.is_paper 判定）。
- OpenAI API を使う機能（news_nlp / regime_detector）は API キーと料金・利用ポリシーに注意してください。API 呼び出し部分はリトライ・バックオフやレスポンスバリデーションを実装していますが、運用時のエラーハンドリング設計は重要です。
- duckdb / sqlite のファイルパスはデフォルトで data/ 以下に置かれます。運用環境のパスや権限に注意してください。

---

トラブルシューティング（よくある問題）
- .env が正しく読み込まれない → .env がプロジェクトルートに存在しているか、KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。
- ログファイルが作成できない → LOG_DIR / logs/ に書き込み権限があるか確認。ディレクトリ作成に失敗した場合はコンソール出力のみになります。
- OpenAI 呼び出しで失敗 → OPENAI_API_KEY の設定、ネットワーク接続、API レート制限や料金上限を確認。news_nlp は複数のリトライロジックを持ちますが、根本的な API 利用設定が必要です。
- データ鮮度・DuckDB クエリエラー → DuckDB に期待するテーブル (prices_daily / raw_financials / raw_news など) があるか確認。

---

ライセンス・貢献
- 本 README はコードベースの解説を目的としています。実運用で用いる場合は適切なテスト・レビュー・リスク評価を行ってください。

---

追加のドキュメントが必要な場合（例: ExecutionEngine の設定パラメータ、OrderManager の契約仕様、DB スキーマ詳細、デプロイ手順、systemd / cron 用の起動スクリプト例など）は要望を教えてください。必要に応じて具体的なコマンド例や systemd ユニットファイルのテンプレート等を作成します。