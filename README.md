KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株を対象とした自動売買システムのパッケージです。本リポジトリはトレーディング実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）やニュース NLP を含む補助ツール群を提供します。  
設計上、Paper Trading と Live（本番）を切り替え可能で、監視用の SQLite、分析用の DuckDB、および外部 API （kabuステーション、J‑Quants、OpenAI 等）と連携します。

主な機能
---------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に分離して記録
  - プロセス優先度の設定、PID 管理、停止フラグの検出
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システムリソース、データ鮮度、発注ログ、リスク（ドローダウン・ポジション数）を定期検査
  - kill.flag による外部からの強制停止シグナル出力
  - Monitoring DB（SQLite）スキーマ自動初期化・マイグレーション
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等配分/スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap スケーリング）
- リサーチ（kabusys.research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）、統計サマリ等
- ニュース NLP（kabusys.ai）
  - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメント評価 → ai_scores テーブルへ保存
  - 市場レジーム判定モジュール（ETF MA とマクロセンチメントの合成）
- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
  - 統一ログ設定、プロセス優先度設定ユーティリティなど

準備（セットアップ）
-------------------
1. Python 環境（推奨: 3.10+）を用意
2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - psutil
     - openai
   - 開発・オプション:
     - PyYAML（config/*.yaml の検証に利用）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合はそれを使用してください）

4. .env の準備
   - プロジェクトルートに .env を置くか、対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う変数（例）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — DEBUG | INFO | WARNING | ...
     - OPENAI_API_KEY — ニュース NLP / レジーム判定用
     - PAPER_FILL_MODE — instant | partial | never | reject（paper_trading 用）
   - 自動ロード: .env / .env.local は起動時に自動読み込みされます（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要コマンド（使い方）
--------------------

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告があっても失敗扱い）: python -m kabusys.validate_config --strict

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する: MONITOR_POLL_INTERVAL 環境変数（秒）を設定（デフォルト 60）
  - 監視は常に production 用 sqlite_path を使います（環境に依らず data/monitoring.db 等）

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に書き込む（本番 DB と分離）
  - 実行停止: プロジェクトルートの data/stop_requested.flag を作成すると安全に停止します
  - ExecutionEngine は data/execution.pid を管理します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- AI（ニュース NLP / レジーム判定）利用（ライブラリ呼び出し例）
  - Python API から呼ぶ:
    - from kabusys.ai import score_news
    - cnt = score_news(duckdb_conn, target_date, api_key="sk-xxxx")
  - 同様に regime 判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="sk-xxxx")
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定

ログとデータ
-------------
- デフォルトログディレクトリ: logs/
  - ログは日次ローテーション（TimedRotatingFileHandler、30日分保持）
  - setup_logging 関数で統一設定（全起動スクリプトが呼び出します）
- データファイル（デフォルト）
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
- kill.flag / kill switch
  - KillSwitch は監視結果に基づき data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 推奨）

設定の注意点
------------
- KABUSYS_ENV による動作差
  - development: 開発モード（発注なし等）
  - paper_trading: 発注はモック。DB は paper_trading 用に分離
  - live: 実際の発注を行う（運用時は慎重に）
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）で行われます
- 重要な環境変数が未設定の場合、Settings クラスは起動時にエラーを投げます（必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
- OpenAI API 呼び出しは外部ネットワークに依存します。API制限・一時エラーはリトライ・フェイルセーフ化されていますが、キーの設定とレート管理に注意してください。

ディレクトリ構成（抜粋）
---------------------
以下はソースツリー（src/kabusys）のおおまかな構成です：

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading レポート生成
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング
      - regime_detector.py     — 市場レジーム判定
    - monitoring/
      - monitoring_db.py       — SQLite スキーマ / 永続化ラッパ
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — （発注ログ監視 ※実装参照）
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - kill_switch.py         — kill.flag 書き込みユーティリティ
      - monitoring_engine.py   — 監視エンジンの統括
      - alert_manager.py       — （アラート送信管理 ※実装参照）
    - portfolio/
      - portfolio_builder.py   — 候補選定・重み計算
      - position_sizing.py     — 発注株数計算
      - risk_adjustment.py     — セクター制限・レジーム乗数
    - research/
      - factor_research.py     — ファクター計算（momentum/value/volatility）
      - feature_exploration.py — 将来リターン・IC・統計ユーティリティ
    - utils/
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - execution/                — Execution 関連（broker_factory 等）
    - data/                     — 実行時に用いる data/ 以下のファイル（DB・PID・flags）

補足（開発者向け）
-----------------
- DB マイグレーションやテーブル追加は monitoring_db.init_monitoring_db の中で冪等に実行されます。実運用でスキーマ変更する場合は注意して対応してください。
- DuckDB クエリはパフォーマンスを考慮して SQL 内にウィンドウ関数等を多用しています。テスト環境でデータ量が少ないと None が返る設計の箇所があります（データ不足チェックに注意）。
- OpenAI 呼び出し部分はリトライ・バリデーションを備えていますが、外部サービス仕様変更の影響を受けやすいので SDK バージョンに応じたテストを推奨します。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

問題報告・貢献
--------------
バグ報告や機能提案は Issue を立ててください。Pull Request は歓迎します。開発用のテストや CI を整備の上、変更を提案してください。

— 以上 —