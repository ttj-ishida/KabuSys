# KabuSys

日本株自動売買システムのコアライブラリ / スクリプト群です。  
このリポジトリには、戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、AI 支援（ニュース NLP / レジーム判定）などの実装が含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 環境変数（主要項目）
- 監視・停止・ファイルフラグ
- ディレクトリ構成

---

プロジェクト概要
- 日本株の自動売買システムのコアモジュール群。
- データ解析用に DuckDB を利用し、監視ログや発注履歴は SQLite に永続化します。
- 実行モードは開発 / ペーパートレード（分離 DB） / 本番を切り替え可能（KABUSYS_ENV）。
- OpenAI を使ったニュースセンチメントやレジーム判定機能を備え、戦略やリスク制御と連携します。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録して本番 DB と分離。
  - プロセス優先度設定・PID ファイル管理・停止フラグ監視を実装。
- Monitoring（run_monitoring.py / monitoring_engine）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングしてシステム健全性をチェック。
  - KillSwitch による停止フラグ（data/kill.flag）出力やアラート連携。
- 環境セットアップウィザード（config_setup.py）
  - .env の対話式生成・更新を支援。
- 設定検証 CLI（validate_config.py）
  - .env / config/*.yaml の存在や基本的な妥当性チェック。
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、重み計算、ポジションサイズ算出、セクターキャップ・レジーム乗数。
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム/ボラティリティ/バリュー）、将来リターン、IC 計算、統計サマリー。
- AI モジュール（kabusys.ai）
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector: マクロ記事 + ETF MA を用いて市場レジーム判定し保存
- ユーティリティ
  - ロギング設定（logs 日次ローテート）
  - プロセス優先度設定 / CPU affinity ヘルパ
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポート生成

セットアップ手順（ローカル / 開発向け）
1. Python 環境を用意
   - Python 3.9+ を想定（使用するライブラリの互換性に合わせて調整してください）
2. 依存ライブラリをインストール
   - 必要な外部ライブラリ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証を行う場合に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （実環境では requirements.txt / Poetry 等を用意するのを推奨）
3. 初期設定
   - リポジトリルートで以下を実行して .env を対話式に作成できます:
     - python -m kabusys.config_setup
   - 既存の .env を手動で作る場合は .env.example を参照してください（リポジトリにある場合）。
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
5. データディレクトリ作成（自動で作られることが多いですが確認）
   - デフォルトで data/ と logs/ を使用します

主要な環境変数（抜粋）
- 必須（サービス動作で必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意
  - KABUSYS_ENV: execution モード（development / paper_trading / live）。デフォルト: development
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading モードで使用、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（ログレベル）
  - OPENAI_API_KEY: OpenAI を利用する機能で必要
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番での通知に必要（任意）
- 自動 .env ロード
  - リポジトリルートにある .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

使い方（コマンド例）
- 環境作成（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- ExecutionEngine を起動（ローカル実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使い、data/paper_trading.db に出力されます
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト 60 秒）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI 機能（プログラムから）
  - kabusys.ai.score_news(), kabusys.ai.regime_detector.score_regime() を呼び出し可能。
  - OpenAI API キー（OPENAI_API_KEY）が必要。

監視・停止・フラグファイル
- stop_requested.flag
  - run_monitoring / run_execution のループを外部から停止するために利用されます（data/stop_requested.flag）。
  - 存在が検知されるとループを抜けて終了します。
- kill.flag
  - KillSwitch（リスク監視）が条件を満たした際に書き込まれるフラグ（data/kill.flag）。ExecutionEngine はこれを読んで停止します。
  - 設定で起動時に自動でクリアするオプション（KILL_FLAG_CLEAR_ON_START）がありますが、本番では 0 を推奨します。
- PID ファイル
  - run_execution は data/execution.pid 等に PID を書きます（Settings でパスを変更可能）。

ログ
- デフォルトで logs/ ディレクトリにアプリ別日次ローテーションログを出力します（kabusys.utils.logging_setup）。
- ログディレクトリは環境変数 LOG_DIR または setup_logging の引数で変更可能。
- ログレベルは LOG_LEVEL または setup_logging の引数で制御。

注意事項 / 設計上のポイント
- Paper Trading は本番 DB とは完全に分離されます（設定による）。
- AI モジュールは外部 API（OpenAI）に依存します。API 呼び出し失敗時はフェイルセーフ（多くは 0 相当やスキップ）で処理を継続する設計です。
- モジュールの多くは外部 DB コネクション（DuckDB / SQLite）を受け取り純粋関数的に動作することを想定しており、ユニットテストが書きやすい設計です。
- config モジュールはプロジェクトルートを .git または pyproject.toml から検出し、自動で .env を読み込みます（必要に応じて無効化可）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（ETF MA + LLM）
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
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py         (trade 関連モニタ)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py         (アラート送信ロジック; 実装がある場合)
  - execution/
    - execution_engine.py     (ExecutionEngine 本体)
    - broker_factory.py       (BrokerClient の生成)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                     (デフォルトのデータ / DB / フラグ格納先)
  - logs/                     (デフォルトログ出力先)

付録: よく使うコマンドまとめ
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行（本番 / ペーパー切替は KABUSYS_ENV）:
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

不明点や README に追加したい項目（CI 設定、Dockerfile、requirements.txt、実行環境の詳細など）があれば伝えてください。README をそれに合わせて拡張します。