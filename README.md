KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター研究、AI を用いたニュースセンチメント評価などの主要機能を提供します。小規模なローカル実行からペーパートレード、本番運用まで想定した設計になっています。

主な特徴
--------
- ExecutionEngine：ブローカークライアント経由での注文管理、リスク管理、照合（reconciler）を備えた実行エンジン
- Monitoring：システム稼働状況、注文ログ、リスク（ドローダウン・ポジション数）等のポーリング監視とアラート連携
- Portfolio Construction：候補選定、重み付け、ポジションサイズ計算、セクター制限・レジーム調整
- Research：DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー等）、特徴量解析（IC, forward returns 等）
- AI モジュール：OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）・市場レジーム判定
- ユーティリティ：ログ設定、プロセス優先度設定、環境設定ウィザード・検証ツール、paper trading 検証レポート生成

要件
----
- Python 3.10 以上（typing の新構文を使用）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の検証を行う場合に必要）
- SQLite は標準ライブラリで使用
- 外部サービス（運用に応じて）:
  - kabuステーション（実売買用）
  - J-Quants API（データ取得）
  - OpenAI（ニュース評価・レジーム判定）

セットアップ手順
--------------
1. レポジトリを取得
   - git clone … またはソースを展開

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt）

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考に）

5. 設定の検証
   - python -m kabusys.validate_config
   - 本番前に --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / PID / フラグ等は data/ 配下を想定しています:
     - data/kabusys.duckdb (DuckDB)
     - data/monitoring.db (SQLite, 監視ログ)
     - data/paper_trading.db (Paper トレード用 SQLite)
     - data/execution.pid, data/kill.flag, data/stop_requested.flag

基本的な環境変数
----------------
主な環境変数（重要度順）:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用 / 推奨
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant/partial/never/reject、デフォルト: instant）
- OPENAI_API_KEY — OpenAI を使う際に必要（AI 機能）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知を使う場合

監視・プロセス制御関連
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START などは Settings クラスで参照

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い、data/paper_trading.db に記録して本番 DB と分離されます
  - 実行中に停止したい場合は data/stop_requested.flag を作成すると起動スクリプトが検知して停止します
  - ExecutionEngine 側に停止指示を出す（Kill Switch）には data/kill.flag を書き込みます（KillSwitch モジュール経由）

- 監視ループ（SystemMonitor）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可。デフォルト 60 秒
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を参照します（監視ログは一元管理）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH もしくは環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラムからの呼び出し例）
  - kabusys.ai.score_news(conn, target_date, api_key=None) — OpenAI API を使いニュースをスコア化して ai_scores テーブルに書き込み
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定

運用上の注意点
---------------
- KABUSYS_ENV=live 設定時はすべての設定を慎重に確認してください（validate_config に警告あり）。
- .env は決して Git にコミットしないでください（config_setup は明記）。
- OpenAI キーやブローカーパスワード等は安全に管理してください。
- Paper trading は本番 DB と分離しますが、本番環境での設定ミスは重大な損失につながるため注意してください。
- プロセス優先度・CPU Affinity の設定には psutil が使用されます。アクセス権限によっては設定できない場合があります（ログに警告出力）。

ディレクトリ構成（抜粋）
----------------------
プロジェクト内の主要なモジュール一覧（src/kabusys 配下）:

- __init__.py
- config.py
  - Settings クラス: 環境変数読み込み、自動 .env ロード（.git / pyproject.toml ベースでルート探索）
- config_setup.py
  - 対話式 .env ウィザード
- validate_config.py
  - 起動前チェック CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト
- utils/
  - logging_setup.py — 統一的ログ設定（stdout + 日次ローテート）
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- execution/ (実行関連コンポーネント)
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py など
- monitoring/
  - monitoring_db.py — SQLite の永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py など
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py など
- research/
  - factor_research.py, feature_exploration.py, etc.（DuckDB を用いたファクター計算）
- ai/
  - news_nlp.py — ニュースセンチメント集約・OpenAI 呼び出し
  - regime_detector.py — マクロ + MA200 を用いる市場レジーム判定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

ログ / DB / フラグ類
-------------------
- logs/ — 日次ローテーションされたログファイル（ログディレクトリは環境変数 LOG_DIR で変更可）
- data/
  - kabusys.duckdb（デフォルト）
  - monitoring.db（監視用 SQLite、デフォルト）
  - paper_trading.db（ペーパートレード用 SQLite）
  - execution.pid（ExecutionEngine の PID ファイル）
  - stop_requested.flag（監視 / 実行スクリプトに外部から停止を伝えるためのフラグ）
  - kill.flag（Kill Switch による ExecutionEngine 停止フラグ）

開発者向け補足
--------------
- DuckDB のテーブル（prices_daily, raw_financials, raw_news, ai_scores など）を想定しており、research / ai モジュールはこれらのテーブルを参照します。
- モジュールの多くは副作用を最小化する純粋関数を志向して実装されています（特に portfolio / research 部分）。
- テストでは .env 自動読み込みを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。
- OpenAI 呼び出し部や外部 API 呼び出しは抽象化されており、ユニットテストではパッチ／モックできます（モジュール内で明示的に記載あり）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報・貢献ルール等はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問題の報告 / コントリビュート
----------------------------
不具合や改善提案は issue を作成してください。Pull Request の前に issue にて相談いただけるとスムーズです。

---
上記 README はコードベース（src/kabusys/*.py）を基に作成しています。デプロイや本番運用を行う際は、各種 API キーの管理・監査ログ、運用手順（起動/停止/監視）およびフェイルセーフ（Kill Switch の取り扱い）を十分に整備してください。