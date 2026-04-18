README
======

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python パッケージ群です。本リポジトリには以下の主要機能群が含まれます。

- 実行エンジン（ExecutionEngine）：発注・注文管理・リスク管理の実装（run_execution.py）。
- 監視（Monitoring）：システム状態、データ鮮度、注文ログ、リスク指標の定期チェック（run_monitoring.py）。
- ポートフォリオ構築：候補選定、重み計算、ポジションサイズ計算、セクター制限など（kabusys.portfolio）。
- リサーチ：ファクター計算、特徴量探索、IC 計算など（kabusys.research）。
- AI 補助：ニュースの NLP スコアリング、レジーム判定（kabusys.ai）。
- 各種ツール：ペーパートレード検証レポート生成など（kabusys.tools.paper_verification_report）。
- 環境管理ツール：.env 対話式ウィザードと設定検証 CLI（config_setup.py / validate_config.py）。

主な設計方針として、実環境とペーパートレードの DB を分離し、監視は本番の監視 DB を使用、AI 呼び出しはフェイルセーフ（失敗時はスキップまたはフォールバック）となるように実装されています。

機能一覧
--------
- 実行（Execution）
  - Broker クライアントの抽象化（実ブローカー / MockBroker 切替）
  - Order 管理、リスクチェック、再整合（reconciler）
  - 発注ログの永続化（SQLite / DuckDB 組合せ）
- 監視（Monitoring）
  - CPU / メモリ / ディスク使用率の収集
  - Execution プロセス稼働検知（PID ファイル確認）
  - データ鮮度チェック（prices_daily 等）
  - トレードログ・滞留注文・約定異常の検出
  - ドローダウン / ポジション上限の監視と Kill Switch（kill.flag）発動
  - アラート送信のための AlertManager（実装箇所参照）
- ポートフォリオ構築
  - シグナルから候補選定（select_candidates）
  - 等金額 / スコア加重の重み算出
  - 単元丸め・リスクベースの株数決定（calc_position_sizes）
  - セクターキャップ適用、レジーム乗数
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI（OpenAI）
  - ニュース記事を LLM でセンチメント評価して ai_scores に保存
  - マクロニュースと ETF MA を使った市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成（P95 レイテンシ等の指標出力）
- 環境管理
  - .env の対話式作成（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

セットアップ手順
----------------
前提
- 推奨 Python バージョン: 3.10 以上（型注釈や union 型 | を使用）
- システム要件: DuckDB, psutil, openai 等の Python パッケージ

1. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. プロジェクトルートに移動して .env を作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考にする）
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な任意／デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB; デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB; デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能を使う場合）

4. 設定検証（実行前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い

5. データディレクトリ／ログディレクトリの確認
   - デフォルトで data/ と logs/ を使用します。権限とディスク空き容量を確認してください。

基本的な使い方
-------------

設定関連
- .env の作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

監視プロセス起動
- run_monitoring を直接起動（デフォルトで MONITOR_POLL_INTERVAL=60 秒）
  - python -m kabusys.run_monitoring
- ポーリング間隔を環境変数で変更:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- 停止方法:
  - プロジェクトルートの data/stop_requested.flag を作成すると監視ループが検知して終了します。

実行エンジン起動（発注系）
- 実行（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
- KABUSYS_ENV による動作切替:
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。
  - それ以外（development / live）は sqlite_path（デフォルト data/monitoring.db）を使用する構成に注意してください。
- 停止方法:
  - data/stop_requested.flag を作成すると実行エンジンに停止を指示します。
  - kill.flag は監視側から ExecutionEngine を停止させるために使用されます（KillSwitch により生成されます）。

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベース指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI / リサーチ機能（プログラム利用）
- ニューススコアリング（例）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="…")
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="…")

ロギング
- setup_logging() により logs/<app_name>.log に日次ローテーションで出力（既定: logs/）
- 環境変数 LOG_DIR で変更可能

重要なファイル・フラグ
- data/kill.flag — Kill Switch による ExecutionEngine 停止指示（監視が書き込む）
- data/stop_requested.flag — 手動で監視/実行スクリプトを安全に終了させるためのフラグ
- data/execution.pid — 実行プロセスの PID ファイル（実行時）
- .env / .env.local — 環境変数ファイル（自動ロードあり。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパー用 DB（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — AI 機能を利用する場合
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (1 = クリアする、デフォルト 0)

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数読み込み / Settings
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 起動前設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
    - data/                     — （実行時に使うことが想定されるディレクトリ）
    - logs/                     — ログ出力ディレクトリ（デフォルト）
    - ai/
      - __init__.py
      - news_nlp.py             — ニュース NLP スコアリング
      - regime_detector.py      — 市場レジーム判定
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
      - trade_monitor.py         — （trade_monitor がある想定）
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py         — （AlertManager 実装が存在する想定）
    - execution/
      - execution_engine.py     — 実行エンジン本体（EngineConfig など）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

開発上の注意 / トラブルシューティング
-------------------------------------
- 自動で .env を読み込む機能はプロジェクトルート検出に依存します（.git または pyproject.toml が起点）。テストなどで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 監視（Monitoring）は監視用 SQLite DB（SQLITE_PATH）を使用します。run_monitoring は KABUSYS_ENV に依らず本番の sqlite_path を使う設計ですので、意図しない DB を上書きしないよう注意してください。
- 実行エンジンのペーパートレードは PAPER_TRADING_SQLITE_PATH に完全分離して記録します（KABUSYS_ENV=paper_trading）。
- OpenAI API を使う機能を利用する場合は OPENAI_API_KEY を .env に設定してください。API 呼び出しはリトライやフォールバックを実装していますが、料金やレート制限に注意してください。
- ログディレクトリ作成やファイルハンドラ作成に失敗した場合、ログはコンソール出力のみになります。LOG_DIR の指定と書き込み権限を確認してください。
- run_monitoring / run_execution は stop_requested.flag の有無を参照してシャットダウンします。手動停止やオートメーション停止のために利用できます。

ライセンス・貢献
----------------
ライセンス情報やコントリビューションガイドはリポジトリのトップにある LICENSE / CONTRIBUTING を参照してください（存在しない場合は管理者に確認してください）。

謝辞
----
このドキュメントはリポジトリ内のソースコードの docstrings と構成に基づいて作成しました。実行前に python -m kabusys.validate_config で環境設定を必ず確認してください。