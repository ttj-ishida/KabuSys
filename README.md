# KabuSys

日本株向け自動売買システムの参照実装ライブラリ / 実行スクリプト群です。  
本リポジトリはトレードエンジン（ExecutionEngine）、監視（Monitoring）、リサーチ／ポートフォリオ構築、AI（ニュース NLP / レジーム判定）などのコンポーネントを含みます。

README の目的:
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 実行例（使い方）
- 主なファイル／ディレクトリ構成

---

## プロジェクト概要

KabuSys は複数の責務に分かれた自動売買システムの構成要素を提供します。主な構成は以下です。

- ExecutionEngine（発注エンジン）: ブローカークライアント経由で発注を実行。paper_trading モードでは MockBrokerClient を使用して本番 DB と分離した専用 DB に記録します。
- Monitoring（監視）: システム状態、注文ログ、リスク（ドローダウン・ポジション数）を定期的にチェックし、kill flag やアラートを発行します。
- Portfolio / Strategy / Research: 銘柄選定、重み付け、ポジションサイジング、ファクター計算、特徴量探索などの純粋関数群。
- AI モジュール: ニュースを LLM（OpenAI）でスコアリングして ai_scores に保存、マクロセンチメントを使った市場レジーム判定。
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード、設定検証 CLI 等。

設計方針として、フェイルセーフ（API 失敗時はフォールバックして継続）、ルックアヘッドバイアス回避（datetime.today() を直接参照しない）、および本番 / ペーパートレードのデータ分離が組み込まれています。

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution）:
  - KABUSYS_ENV に応じて本番/ペーパートレードを切替え
  - 発注・オーダー管理・リスク管理・再照合（reconciler）を統合
- 監視ループ起動スクリプト（run_monitoring）:
  - システム状態、データ鮮度、注文状況、リスクを定期ポーリング
  - MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）
  - 監視は環境に関係なく本番 sqlite_path を使用（監視ログの永続化）
- 設定ウィザード（config_setup）:
  - .env を対話式で生成・更新
- 設定検証 CLI（validate_config）:
  - .env と config/*.yaml の検証（--strict で警告を FAIL 扱い）
- Paper Trading 検証レポート（tools/paper_verification_report）:
  - ペーパートレード DB から稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL を判定
- ポートフォリオ構築ライブラリ:
  - 銘柄選定、等金額/スコア加重配分、セクター上限、レジーム乗数、ポジションサイズ計算（lot 丸め・aggregate cap）
- リサーチ:
  - モメンタム、ボラティリティ、バリュー等のファクター計算、将来リターン、IC（情報係数）計算
- AI:
  - ニュース集約 → OpenAI（gpt-4o-mini）でセンチメント評価 → ai_scores へ書込
  - マクロニュース + ETF MA200 による market_regime 判定

---

## セットアップ手順（ローカル開発想定）

前提: Python 3.10+ を想定（型注釈の union 型や typing 機能に依存）。必要なパッケージは以下を参照してください。

1. リポジトリをクローン / 取得
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（最低限の候補）
   - pip install duckdb psutil openai PyYAML
   - （必要に応じて他の依存を追加してください）
   - または requirements.txt があれば: pip install -r requirements.txt
4. 環境変数 / .env の準備
   - 対話式に作る: python -m kabusys.config_setup
   - もしくは .env を手動で作成（例は下記参照）
   - 自動ロード: パッケージ起動時に .env / .env.local が自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合: python -m kabusys.validate_config --strict
6. データディレクトリの作成（必要に応じて）
   - デフォルトでは data/ 以下に DB や pid/flag ファイルを作成します。実行前に権限を確認してください。
7. ログディレクトリは自動作成されます（デフォルト: logs/）。失敗した場合はコンソール出力のみになります。

必須の環境変数（最小）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）

AI モジュールを使う場合:
- OPENAI_API_KEY（score_news / score_regime を実行するため）

データベースのデフォルトパス:
- DuckDB: data/kabusys.duckdb
- SQLite（監視）: data/monitoring.db
- Paper trading SQLite（paper_trading 時）: data/paper_trading.db

ログ設定:
- logs/<app_name>.log に日次ローテーションで出力（30日保持）

---

## 使い方（実行例）

ここでは一般的なコマンド・動作を示します。モジュールはパッケージモードで実行できます（python -m kabusys.〜）。

1. 設定ウィザード（.env の生成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード（警告を FAIL にする）: python -m kabusys.validate_config --strict

3. ExecutionEngine（発注エンジン）起動
   - 本番・開発・ペーパートレードは KABUSYS_ENV で切替:
     - export KABUSYS_ENV=development|paper_trading|live
   - 起動:
     - python -m kabusys.run_execution
   - 備考:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と分離）。
     - エンジンは data/stop_requested.flag を検知すると安全に停止します。
     - PID ファイル: data/execution.pid（設定により変更可能）

4. Monitoring（監視ループ）起動
   - ポーリング間隔を上書きする場合:
     - export MONITOR_POLL_INTERVAL=30  （秒）
   - 起動:
     - python -m kabusys.run_monitoring
   - 備考:
     - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用してログを記録します。
     - 停止は data/stop_requested.flag を作成することで行います（監視ループはフラグを検知して終了）。

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を指定する場合:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

6. AI 関連（プログラム API として使用）
   - ニュース NLP スコア: kabusys.ai.score_news(conn, target_date, api_key=None)
     - conn は duckdb.connect(...) で得た接続オブジェクト
     - api_key が None の場合は環境変数 OPENAI_API_KEY を使用
   - レジームスコア: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 両関数は LLM 呼び出し時に例外を吸収する箇所がありますが、APIキーが未設定の場合は ValueError を投げます。

7. 一時停止 / 強制停止フラグ
   - ExecutionEngine の停止シグナル: data/kill.flag を KillSwitch が作成する（監視コンポーネントが条件を満たした際）
   - 管理者による強制停止（監視 / エンジンを止めたい場合）:
     - data/stop_requested.flag を作成すると run_execution / run_monitoring が検知して終了します。
   - kill.flag 自動クリア設定:
     - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に kill.flag を自動クリアします（本番では 0 推奨）。

---

## よく使う環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- SQLITE_PATH: 監視 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- LOG_LEVEL: LOG レベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用。デフォルト 60）

---

## ディレクトリ構成（主要ファイル）

以下はソースツリーの要約（src/kabusys をルートとした主要ファイル／モジュール）です。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py
  - config_setup.py        # .env 対話ウィザード
  - validate_config.py     # 設定検証 CLI
  - run_execution.py       # ExecutionEngine 起動スクリプト
  - run_monitoring.py      # Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py     # ログ設定ユーティリティ
    - process_priority.py  # プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py      # （実装参照 — ログ監視等）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py      # （アラート実装）
  - execution/
    - broker_factory.py
    - execution_engine.py
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
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/                  # 実行時に使用する data/ 配下ファイル（DB, pid, flag 等）
  - logs/                  # ログ出力先（デフォルト）

（注）上記ツリーは主要ファイルにフォーカスしています。実際のリポジトリにはさらに補助モジュールやテスト、スクリプトが存在する場合があります。

---

## 注意事項 / 運用メモ

- 監視（run_monitoring）は KABUSYS_ENV にかかわらず本番の sqlite_path を使用します。監視ログは本番 DB を想定した記録です。
- ExecutionEngine は paper_trading モード時に別 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離します。これによりペーパートレードの履歴が本番データに影響しません。
- Kill Switch（kill.flag）はリスクトリガー（ドローダウン超過等）で作成され、ExecutionEngine はそれを検知して安全に停止します。KILL_FLAG_CLEAR_ON_START を誤って 1 にしてしまうと本番で kill.flag が自動クリアされるため注意してください。
- LLM（OpenAI）呼び出しには API キーが必要です。キーは環境変数 OPENAI_API_KEY に設定してください。API 呼び出しはリトライロジックやレスポンス検証を備えていますが、コスト・レイテンシ・利用規約には注意してください。
- ログディレクトリの作成に失敗した場合はファイル出力が無効化され、コンソールのみの出力になります（setup_logging がその旨を警告します）。
- DuckDB / SQLite / psutil 等のネイティブ拡張や OS 権限に依存する処理があるため、実行ホストの環境（ユーザー権限, ファイルパス, ネットワーク）に注意してください。

---

必要であれば、README に含めるサンプル .env テンプレート、起動スクリプトのデーモン化手順（systemd ユニット例）、あるいは各モジュール（ExecutionEngine, MonitoringEngine, AI スコアリング）の設計仕様の詳細も追加できます。どの情報を優先して追記しましょうか？