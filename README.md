KabuSys — 日本株自動売買システム (README)
======================================

本ドキュメントは、与えられたコードベースに基づく簡易 README です。日本語での導入手順・使い方・ディレクトリ構成をまとめています。

1. プロジェクト概要
------------------
KabuSys は日本株向けの自動売買 / 研究基盤です。主な役割は以下の通りです。

- 注文実行エンジン（ExecutionEngine）: ブローカークライアントを使った発注、注文管理、リスク管理、約定の記録など
- 監視サブシステム（Monitoring）: システム稼働状態・データ鮮度・注文の異常を定期チェックし、必要に応じて Kill Switch を発動
- ポートフォリオ構築ライブラリ: 候補選定、重み付け、ポジションサイズ計算、セクター上限・レジーム調整等
- 研究ツール（Research）: DuckDB を用いたファクター計算・将来リターン/IC 計算・特徴量集計
- AI 補助（AI）: ニュースの NLP によるセンチメント評価、レジーム判定（OpenAI API を利用）
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード、構成検証ツール、検証レポート生成等

2. 機能一覧
------------
- 設定管理:
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を優先順で読み込み）
  - 対話式ウィザードで .env を作成/更新（kabusys.config_setup）
  - 起動前チェック（kabusys.validate_config）
- 実行:
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に分離
    - PID ファイル、停止フラグ対応
  - Monitoring 起動スクリプト（run_monitoring.py）
    - 定期ポーリングで system/trade/risk をチェック、ログ保存、kill.flag 書き込み等
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視 DB 永続化（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard を管理
- ポートフォリオ構築: 候補選定、等重/スコア重み付け、リスクベースのポジション計算、セクター上限、レジーム乗数
- 研究モジュール（DuckDB 経由）: モメンタム・ボラティリティ・バリュー等のファクター計算、IC 計算、将来リターン
- AI 機能:
  - news_nlp.score_news: OpenAI でニュースセンチメントを算出して ai_scores テーブルに書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースを組み合わせて日次レジーム判定
- ツール:
  - paper_verification_report: ペーパートレード DB から運用検証レポートを生成

3. 前提 / 必要環境
-------------------
- Python 3.10 以上（型ヒントの | 演算子などを使用）
- 推奨パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config ファイルの検証を行う場合に推奨）
- 環境変数の設定（主要なものは次節参照）

4. 初期セットアップ手順
----------------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 必要なパッケージをインストールします（例）:
   - pip install duckdb psutil openai

   （依存リストがない場合はプロジェクトに合わせて適宜追加してください）

3. 環境設定ファイルの作成:
   - 対話式ウィザード: python -m kabusys.config_setup
     → .env を生成 / 更新します（機密値はマスクして保存されます）

4. 設定検証（推奨）:
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合は --strict を付けます

5. 主要な環境変数（概要）
------------------------
最低限設定が必要な必須変数:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

運用に関わる代表的な変数（デフォルト値あり）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - paper_trading: 実運用 DB と分離した専用の paper_trading DB を使用
  - live: 本番
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（monitoring.db デフォルト）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY — OpenAI API を利用する場合に設定
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0。本番では 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、run_monitoring でのみ有効。デフォルト 60）

6. 実行方法（主要コマンド）
---------------------------
- ExecutionEngine を起動（常用）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にした場合、paper_trading 専用 DB に記録され、本番 DB と分離されます。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）。

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（DB パスを明示する場合）
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使うこともできます。

- AI 機能（スコアリング / レジーム判定）:
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - どちらも OPENAI_API_KEY（または api_key 引数）を必要とします。API 呼び出しは失敗に寛容なフォールバック実装が含まれていますが、キーなしでは動作しません。

7. ログ / DB / フラグファイルについて
-----------------------------------
- ログ:
  - デフォルトで logs/ ディレクトリにアプリ別のログファイルが日次ローテートで出力されます（例: logs/execution.log, logs/monitoring.log）。
  - コンソール出力は stdout に流れます。

- DB:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite（監視）: data/monitoring.db（monitoring 用）
  - Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading のとき実行エンジンが使用）

- PID / 停止フラグ:
  - data/execution.pid — ExecutionEngine の PID 保存先（起動時に書き込み）
  - data/stop_requested.flag — 実行スレッドの停止を要求するためのフラグ（run_execution/run_monitoring が監視）
  - data/kill.flag — Kill Switch（監視が条件に応じて書き込む）。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 に設定すると自動クリアします（本番では推奨しません）。

8. 主要モジュールの簡単な説明
----------------------------
- kabusys.config: 環境変数/.env の読み込み、Settings クラスでのラップ
- kabusys.config_setup: .env を対話的に生成/更新するウィザード
- kabusys.validate_config: .env や config/*.yaml の事前チェック
- run_execution.py: ExecutionEngine の起動スクリプト（paper_trading で DB 分離）
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
- kabusys.monitoring.*:
  - monitoring_db: SQLite スキーマと CRUD ヘルパ
  - system_monitor / trade_monitor / risk_monitor: 各種チェックロジック
  - monitoring_engine: 各 Monitor を束ねる実行ループ
  - kill_switch: 条件に応じて kill.flag を書き込むロジック
  - alert_manager:（アラート送信ロジック、コードベースに依存）
- kabusys.portfolio.*: 候補選定・重み付け・セクター制限・ポジションサイズ計算
- kabusys.research.*: DuckDB を使ったファクター計算と統計ツール
- kabusys.ai.*: OpenAI を使ったニュース NLP とレジーム判定
- kabusys.utils:
  - logging_setup: ログの一括設定ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity の設定

9. ディレクトリ構成（抜粋）
--------------------------
以下はコードベースの主要ファイル/ディレクトリの簡易ツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (注: 実装依存)
  - execution/          (ExecutionEngine関連の実装群)
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - data/               (データパイプライン・DuckDB 関連実装)
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py

（実際のリポジトリではさらにファイルが存在します。上は主要箇所の抜粋です。）

10. 運用上の注意点 / ベストプラクティス
--------------------------------------
- 本番運用時は KABUSYS_ENV=live の設定を十分確認してください（validate_config は live で警告を出します）。
- kill.flag / stop_requested.flag の取り扱いに注意してください。KILL_FLAG_CLEAR_ON_START=1 は本番では推奨されません。
- OpenAI API を使う機能は API キーとコストに注意して運用してください。API リトライ・部分成功の保護ロジックが組み込まれていますが、レート制限やコストは運用で管理してください。
- ログは logs/ に日次ローテートで出力されます。ディスク容量の監視も行ってください。
- Paper Trading モードは本番 DB と完全に分離するよう設計されています。検証や QA に活用してください。

11. よく使うコマンドまとめ
-------------------------
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate

- 必要パッケージのインストール（例）
  - pip install duckdb psutil openai PyYAML

- .env の作成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution

- 監視起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
本 README はコードベースの主要機能と運用上のポイントをまとめた簡易ドキュメントです。実際のデプロイ・本番運用時は config/*.yaml（存在する場合）、運用ドキュメント、テストを併せて十分に確認してください。必要であれば、各モジュールの詳細な API ドキュメントやサンプル設定ファイルを別途作成できます。