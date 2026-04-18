# KabuSys

日本株自動売買システムの一部（ライブラリ + 起動スクリプト群）。  
このリポジトリには取引実行エンジン、監視・アラート、ポートフォリオ構築・サイズ計算、ファクター算出、AI を使ったニュース NLP／レジーム判定、ユーティリティ等が含まれます。

バージョン: 0.1.0

---

## 概要

- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動（paper_trading では MockBroker を使用し paper DB に記録）
  - run_monitoring.py: SystemMonitor をポーリングして監視ログを収集
- 設定管理
  - config_setup.py: .env の対話式作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証
  - config.py: 環境変数から Settings を提供（デフォルト値や検証ロジックを含む）
- 監視
  - monitoring/*: MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、AlertManager 等
- 戦略／ポートフォリオ
  - portfolio/*: 銘柄選定、重み計算、セクター制限、ポジションサイズ算出
- リサーチ
  - research/*: ファクター計算（momentum/value/volatility）、特徴量探索、IC 計算等
- AI
  - ai/news_nlp.py: OpenAI を使ったニュースのセンチメント付与（ai_scores テーブルへ書き込み）
  - ai/regime_detector.py: MA 乖離 + マクロニュースの LLM 評価で市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポートの生成
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定

---

## 主な機能一覧

- 実行エンジン起動（本番 / ペーパートレード分離）
  - KABUSYS_ENV による動作モード切替（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient を使用し DB を分離（data/paper_trading.db が既定）
- 監視（System / Trade / Risk）
  - system_status / trade_logs / risk_logs / positions / dashboard などを SQLite に永続化
  - Kill Switch（条件を満たしたら data/kill.flag を書き込みエンジン停止）
  - stop リクエスト（data/stop_requested.flag）によるグレースフル停止
- ポートフォリオ構築
  - シグナル選別、等金額・スコア加重、リスクベース配分、単元株丸め、集約キャップ処理
  - セクター集中制限、レジーム乗数適用
- リサーチ / ファクター計算
  - DuckDB からの価格・財務データ参照によるファクター算出（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（情報係数）や統計サマリ
- AI 統合
  - OpenAI (gpt-4o-mini) を利用したニュースセンチメントスコアリングとレジーム判定（API キー必須）
  - リトライ・バックオフ、レスポンスバリデーション、部分成功時の DB 保護（冪等性）
- 運用支援ツール
  - .env 対話ウィザード、設定検証、ペーパートレード検証レポート生成

---

## セットアップ（ローカル）

1. リポジトリをクローン／チェックアウトする。

2. Python 環境を作成・有効化（例: venv / pyenv / poetry）。
   - 必要な主な外部ライブラリ（プロジェクトによって追加要件あり）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合に推奨）
   - 例:
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
   - requirements.txt がない場合は上記パッケージを個別にインストールしてください。

3. .env を作成する
   - 対話式ウィザードで生成:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成（以下は最低限必要な環境変数の例）:

     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     # OpenAI を使う機能を使うなら:
     OPENAI_API_KEY=sk-...

   - 注意: .env は絶対にバージョン管理にコミットしないでください。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合:
     python -m kabusys.validate_config --strict

5. データディレクトリ作成（logs, data 等）
   - ログディレクトリや data は起動時に自動作成される場合がありますが、権限等で失敗することがあるため事前に作成しておくと安全です。
   - 例:
     mkdir -p data logs

---

## 使い方（起動・運用）

- ExecutionEngine を起動
  - 通常起動（設定に従う）:
    python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading: MockBrokerClient を使用。発注情報は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離される。
    - KABUSYS_ENV=live: 実際に発注を行います（本番注意）。
  - 停止方法:
    - run_execution は data/stop_requested.flag を監視します。停止したい場合は当該ファイルを作成してください。
    - Kill Switch（監視から書き込まれる data/kill.flag）を使うとエンジンに停止命令を出せます。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動でクリアしますが、本番では 0 を推奨します。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き可能:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ※ デフォルトは 60 秒。0 以下は無効でデフォルトにフォールバックします。
  - 監視は Settings.sqlite_path（monitoring DB）に書き込みます（monitoring は環境に関わらず本番 sqlite_path を使用する設計）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定や DB 指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー (OPENAI_API_KEY) が必要です。関数はプログラム内から呼び出すことを想定しています。
  - news_nlp.score_news、regime_detector.score_regime を利用して DuckDB のテーブルに書き込みます。

---

## 重要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ログ
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時のみ使用）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログ格納ディレクトリ（デフォルト logs/）
- ペーパートレード
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
- Kill/Stop
  - KILL_FLAG_PATH: data/kill.flag（デフォルト）
  - KILL_FLAG_CLEAR_ON_START: 0 | 1（デフォルト 0。本番では 0 推奨）
- モニター
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

---

## 注意点・運用メモ

- run_monitoring と run_execution は stop フラグファイル（data/stop_requested.flag）を見てグレースフルに終了します。スクリプトの停止はフラグ作成を使うと安全です。
- Monitoring は sqlite のスキーマを init_monitoring_db() で自動生成・マイグレーションします。
- ロギングは utils.logging_setup.setup_logging を使って統一されます。ログは stdout と logs/<app>.log（日次ローテート）へ出力されます。
- psutil によるプロセス優先度設定は環境に依存します。権限不足や未対応 OS の場合は警告を出してスキップします。
- OpenAI を利用する機能は API 呼び出しに対してリトライ・バックオフとレスポンスバリデーションを実装していますが、API キーの管理・利用料・利用制限等は運用者が管理してください。
- paper_trading モードは本番 DB と完全に分離する設計ですが、環境変数の設定ミスには注意してください（特に live モード時）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

src/kabusys/utils/
- __init__.py
- logging_setup.py
- process_priority.py

src/kabusys/monitoring/
- monitoring_db.py
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- monitoring_engine.py
- alert_manager.py (参照あり)

src/kabusys/execution/
- broker_factory.py
- execution_engine.py
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/ai/
- news_nlp.py
- regime_detector.py
- __init__.py

src/kabusys/tools/
- paper_verification_report.py
- __init__.py

（実際のリポジトリにはさらに細かい実装ファイルが存在します。上は主要なモジュールの抜粋です。）

---

## よく使うコマンドまとめ

- .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動:
  python -m kabusys.run_execution

- 監視起動:
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

もし README に加えたい具体的な例（.env の完全サンプル、systemd ユニットの例、データベース初期化スクリプトなど）があれば教えてください。必要に応じて追記します。