KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコア実装です。  
エンジン（発注実行）、監視（モニタリング）、ポートフォリオ構築、リサーチ（ファクター計算）、
および OpenAI を用いたニュース NLP / レジーム判定などを含むモジュール群で構成されています。

主な機能
--------

- 実行エンジン（ExecutionEngine）
  - kabuステーションやモックブローカー経由での注文発行（KABUSYS_ENV により paper_trading / live を切替）
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカー等）
  - 注文管理・再調整（Reconciler / OrderManager）
- 監視（Monitoring）
  - システムリソース、プロセス状態、データ鮮度の定期監視（SystemMonitor）
  - 注文/約定ログ監視（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）
  - Kill Switch（条件により data/kill.flag を書き込み、ExecutionEngine を停止）
  - 監視データの永続化（SQLite）
- ポートフォリオ構築（Portfolio）
  - シグナルから候補選定、重み計算、ポジションサイズ算出（等分配・スコア加重・リスクベース）
  - セクター上限・レジーム乗数の適用
- リサーチ（Research）
  - DuckDB を利用したファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等の探索ツール
- AI モジュール
  - ニュースを LLM（OpenAI）でスコアリングし ai_scores に保存（news_nlp）
  - ETF（1321）MA とマクロニュースを組合せた市場レジーム判定（regime_detector）
- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定管理・検証
  - .env を対話的に作成するウィザード（config_setup.py）
  - 起動前に設定と YAML ファイルを検証する CLI（validate_config.py）
- ユーティリティ
  - 統一ログ設定（logs に日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

前提 / 必要環境
----------------

- Python 3.10 以上（PEP 604 の union 型や型ヒントの記法を使用）
- 必要な Python パッケージ（最低限の例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の検証を行う場合に推奨）
- ローカルファイルシステムに以下のディレクトリ作成権限
  - data/（SQLite / PID / フラグファイル用）
  - logs/（ログファイル用）

インストール例
--------------

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを利用してください。）

セットアップ手順
--------------

1. リポジトリルートに移動し、data/logs ディレクトリを作成
   - mkdir -p data logs

2. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードで KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等を設定します。
     - .env は絶対に Git にコミットしないでください。

3. 設定検証
   - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります。

4. DB ファイルの準備
   - 通常は初回起動時に必要テーブルが自動作成されます（monitoring_db.init_monitoring_db 等）。
   - Paper Trading 用に分離された DB を使用する場合は PAPER_TRADING_SQLITE_PATH を設定してください。

重要な環境変数（代表）
----------------------

- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録
  - live: 実際に発注を行う（注意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- PAPER_FILL_MODE — ペーパートレードの約定振る舞い（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリア（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（主要コマンド）
--------------------

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（デフォルトは settings.env に依存）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading を設定するとモックブローカーを使い data/paper_trading.db に記録します。

- 監視モニター起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

停止・Kill Switch
-----------------

- 実行ループの停止:
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を監視しています。ファイルを作成するとループが検知し終了します。
  - KillSwitch（監視側）によりリスク条件が満たされると data/kill.flag が書き込まれ、ExecutionEngine 側で検知して安全に停止します。
- kill.flag の自動クリアは .env の KILL_FLAG_CLEAR_ON_START=1 で制御します（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
------------------------------

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / Settings 管理（.env 自動ロード機能あり）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続層
    - system_monitor.py — システム・データ鮮度の監視
    - trade_monitor.py — （trade 監視ロジック）※実装詳細ファイルあり
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — 通知管理（LINE 等への送信ラッパー）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数算出・資金配分ロジック
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - utils/
    - logging_setup.py — 統一的なロギング設定
    - process_priority.py — プロセス優先度 / CPU affinity
  - execution/、data/ など（注文管理やデータアクセス層、実装ファイル群）

開発上の注意点 / トラブルシューティング
--------------------------------------

- Python バージョンを確認してください（3.10 以上推奨）。
- DuckDB / SQLite は大量データを扱うため適切なストレージ容量を確保してください。
- OpenAI 関連機能を使うには OPENAI_API_KEY が必要です。API エラー時は処理がフェイルセーフ（スコアは 0 等）となりますが、API キーが無いと一部機能は動作しません。
- Logs: logs/<app_name>.log に日次ローテーションで出力されます。ログディレクトリの作成に失敗するとコンソールのみで出力されます。
- 一部モジュールは外部設定ファイル（config/*.yaml）を参照します。validate_config はそれらの存在や YAML パースの検証も行います（PyYAML が必要）。

内部 API / プログラム的利用
------------------------

本プロジェクトはモジュール化されているため、各機能はプログラムから直接呼び出して利用できます。例:

- ニューススコアリング（プログラム呼び出し）
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

- ポートフォリオ関数群
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

貢献 / 変更時のガイド
--------------------

- 設定項目（.env, config/*.yaml）を追加する場合は config_setup.py と validate_config.py を更新してください。
- DB スキーマ変更は monitoring_db.init_monitoring_db にマイグレーション処理を追加してください（既存 DB との互換性に配慮）。
- ログメッセージは utils/logging_setup.py で統一されたフォーマットで出力されます。新しいスクリプトも必ず setup_logging を最初に呼ぶようにしてください。

ライセンス
---------

（この README にはライセンス記載がありません。リポジトリルートの LICENSE を参照してください。）

以上がこのコードベースの概要と基本的な利用方法です。必要であれば「特定モジュールの使い方」「.env の推奨テンプレート」「運用チェックリスト」などを追記します。どのトピックを詳しく書きますか？