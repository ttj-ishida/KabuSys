KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。本リポジトリは以下の主要機能を含みます。

- 発注エンジン（ExecutionEngine）とペーパートレードの分離実行
- 監視プロセス（System / Trade / Risk の定期チェック）と Kill Switch
- DuckDB を用いたリサーチ（ファクター計算、特徴量探索）
- OpenAI を用いたニュース NLP（センチメント評価）／レジーム判定
- ポートフォリオ構築ユーティリティ（銘柄選定・配分・ポジションサイズ計算）
- ユーティリティ群（設定ウィザード、設定検証、ログ設定など）
- Paper Trading 検証レポート生成ツール

主な特徴
--------
- 環境変数/.env による設定管理（Settings クラス）
- 発注と監視はファイルベースのフラグ（data/kill.flag, data/stop_requested.flag など）で連携（簡素で運用しやすい設計）
- DuckDB / SQLite をデータ保存に利用（分析用 / 監視用に分離）
- OpenAI（gpt-4o-mini など）との連携によりニュースセンチメントやレジーム判定をサポート
- ロギングは統一的な setup_logging を提供（コンソール + 日次ローテーションファイル）

セットアップ
------------
前提
- Python 3.10+
- pip

推奨手順（開発環境）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai
   - 任意: PyYAML（config/*.yaml の検証を行いたい場合）: pip install PyYAML

（requirements.txt がある場合は pip install -r requirements.txt を使用）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに手動で .env を置く
   - 自動ロード: デフォルトで .env/.env.local は起動時に自動で読み込まれます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能で必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（KABUSYS_ENV=paper_trading 時の専用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒、デフォルト: 60）

設定検証
- .env と config/*.yaml の整合性を起動前にチェックできます:
  - python -m kabusys.validate_config
  - --strict オプションで警告を FAIL 扱いにできます（exit code 1）

使い方（CLI）
--------------
主要なエントリポイントと使い方の例。

1. Execution（発注エンジン）
   - 目的: 実際の発注・ペーパートレード実行
   - 実行:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db へ記録（本番 DB と分離）
     - プロセス優先度を "high" に設定し、内部で ExecutionEngine をスレッド実行
     - data/stop_requested.flag が存在すると起動しない / 実行中に検出すると停止処理を行う
     - PID ファイル（デフォルト data/execution.pid）を使用

2. Monitoring（監視ループ）
   - 目的: システム状態・注文状況・リスク（ドローダウン等）を定期監視し、必要なら Kill Switch を作動
   - 実行:
     - python -m kabusys.run_monitoring
   - オプション:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60）
   - 挙動:
     - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず本番 monitoring.db を参照）
     - stop flag（data/stop_requested.flag）検出でループ終了
     - MonitoringEngine にて System / Trade / Risk Monitor を組み合わせてチェック・アラート送信等を実施

3. Paper Trading 検証レポート
   - 目的: ペーパートレードの検証指標を期間指定で出力
   - 実行例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB を指定する場合: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも可）
   - 出力: 稼働率、注文成功率、レイテンシ等のサマリと PASS/FAIL 判定

4. 設定ウィザード / 検証
   - .env 作成: python -m kabusys.config_setup
   - 設定検証: python -m kabusys.validate_config [--strict]

AI / OpenAI 機能
----------------
- kabusys.ai.news_nlp.score_news: ニュース記事を OpenAI でスコアリングし ai_scores テーブルへ書き込む
- kabusys.ai.regime_detector.score_regime: ETF（1321）MA とマクロニュースを組み合わせて市場レジームを判定・保存
- 使用には OPENAI_API_KEY の設定が必要（引数で渡すことも可能）
- API 呼び出し時はエクスポネンシャルバックオフや部分失敗時のフェイルセーフ処理を備えています

ログ
----
- ログは setup_logging により統一設定される（StreamHandler → stdout、TimedRotatingFileHandler → 日次ローテーション）
- デフォルトログディレクトリ: logs/
- 各アプリ名でログファイルが生成される（例: logs/execution.log, logs/monitoring.log）
- 環境変数 LOG_LEVEL / LOG_DIR で制御可能

ファイルフラグ / 運用
--------------------
- data/stop_requested.flag: 起動スクリプト（monitoring / execution）の停止フラグとして参照
- data/kill.flag: KillSwitch が書き込む停止シグナル（ExecutionEngine 側で検知して安全停止）
- PID ファイル: data/execution.pid（ExecutionEngine 実行時に使用）

ディレクトリ構成（抜粋）
-----------------------
リポジトリの主要ディレクトリ / ファイル（本 README に出てくるファイルベースの概観）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - risk_adjustment.py      — セクター制限・レジーム乗数
    - position_sizing.py      — 発注株数算出
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定（OpenAI 連携）
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite 永続化層
    - system_monitor.py       — システム状態監視
    - trade_monitor.py        — （trade 関連監視 — 実装参照）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - monitoring_engine.py    — 各 Monitor を束ねる
    - kill_switch.py          — Kill Switch 実装
    - alert_manager.py        — アラート送信管理（LINE 等 — 実装参照）
  - execution/
    - execution_engine.py     — 発注エンジン本体（EngineConfig 等）
    - broker_factory.py       — ブローカークライアントの生成（Mock を含む）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/*, ai/*, research/* などの細部実装

データ・DB（既定）
- DuckDB: data/kabusys.duckdb（分析用、DuckDB へ接続して prices_daily 等のテーブルを参照）
- SQLite (monitoring): data/monitoring.db（監視ログ・注文ログ・ダッシュボード等）
- SQLite (paper_trading): data/paper_trading.db（ペーパートレード専用、KABUSYS_ENV=paper_trading 時に使用）

開発上の注意
-------------
- Settings は実行時に .env を自動ロードします（プロジェクトルート判定: .git または pyproject.toml を起点）
- .env は絶対に Git にコミットしないでください（config_setup.py の生成コメントにも明記）
- OpenAI API を使う機能は API キーの漏洩に注意してください
- monitoring は本番の sqlite_path を参照するため、監視環境の権限・パスには注意してください
- Python の型ヒントは 3.10 の union 型（X | Y） を使っています。3.10 以上を推奨します

よくある運用フロー（例）
1. .env を作成（python -m kabusys.config_setup）
2. 設定を検証（python -m kabusys.validate_config）
3. DuckDB / SQLite の初期データ投入（パイプラインやスクリプトに依存）
4. 監視プロセスをデーモン化して起動（python -m kabusys.run_monitoring）
5. Execution を起動（python -m kabusys.run_execution）
6. 必要に応じて Paper Trading レポートを実行（python -m kabusys.tools.paper_verification_report）

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ で管理（現在 0.1.0）
- ライセンス情報は本リポジトリのルートにある LICENSE / NOTICE 等を参照してください（存在する場合）

その他
-----
- config/*.yaml（各種設定テンプレート）は存在が期待されますが、PyYAML 未インストール時は検証をスキップするよう設計されています
- DuckDB / SQLite スキーマの初期化は init_monitoring_db 等で冪等に行われます

質問や追加のドキュメント（API リファレンス、運用手順）を希望であれば、どの部分を詳しく解説するか教えてください。