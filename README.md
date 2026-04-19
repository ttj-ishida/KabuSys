KabuSys — 日本株自動売買システム
================================

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買・研究・監視を支援する Python ベースのシステムです。  
主要機能は以下の通りです:

- ExecutionEngine（発注エンジン）: 実際の発注またはペーパートレードを実行
- Monitoring（監視）: システム稼働・注文・リスクを定期チェックし、Kill Switch を発動
- Portfolio Construction: 候補選定・重み計算・ポジションサイズ決定、セクター制限・レジーム補正
- Research: ファクター計算、将来リターン・IC 計算、統計サマリー
- AI 補助: ニュース記事の NLP によるセンチメント評価、マクロニュースを用いた市場レジーム判定
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード・検証 CLI、各種レポート生成

特徴
----
- 環境変数 / .env による設定管理（config_setup による対話的作成サポート）
- Paper Trading（ペーパートレード）は本番 DB と分離（data/paper_trading.db がデフォルト）
- DuckDB を用いた分析向けデータアクセス、SQLite を監視・ログ保存に使用
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定機能（API キー必須）
- 監視系は kill.flag / stop_requested.flag / pid ファイルでプロセス制御・連携可能

主要機能一覧
--------------
- kabusys.run_execution: ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い Paper DB に記録
  - Execution の PID ファイル管理・停止フラグ検知対応
- kabusys.run_monitoring: SystemMonitor ポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可（デフォルト 60 秒）
  - Monitoring は環境に関わらず本番 sqlite_path を参照して監視ログを記録
- kabusys.config_setup: 対話式 .env 作成・更新ウィザード
- kabusys.validate_config: .env と config/*.yaml を起動前にチェックする CLI（--strict あり）
- kabusys.tools.paper_verification_report: ペーパートレード検証レポート生成
- kabusys.ai.news_nlp: ニュース記事を LLM でスコアリングして ai_scores に保存
- kabusys.ai.regime_detector: ETF とマクロ情報を組み合わせて市場レジーム判定
- kabusys.portfolio.*: 候補選定 / 重み計算 / ポジションサイズ / セクター制限等の純粋関数群
- kabusys.monitoring.*: MonitoringDB、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine
- kabusys.utils: ロギング設定（ログは logs/<app_name>.log に日次ローテート）・プロセス優先度/CPU affinity 設定

セットアップ手順
----------------
1. 必要環境
   - Python 3.9+（コードは型注釈で Python 3.10 以降を想定している箇所がありますが、3.9 でも動作する想定）
   - システムパッケージ: ビルドツール等（環境による）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
   - 任意（機能により）:
     - PyYAML（config/*.yaml の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

4. .env を用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動作成（.env.example を参照して .env を作成）
   - 重要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (PAPER_TRADING 用 DB パス、デフォルト data/paper_trading.db)
     - OPENAI_API_KEY （AI 機能を使う場合に必須）
     - LOG_LEVEL, LOG_DIR 等

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告もエラーにしたい場合は --strict を付与

使い方（起動 / CLI）
------------------
- ExecutionEngine（本番／ペーパートレード起動）
  - python -m kabusys.run_execution
  - 動作挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用し MockBrokerClient で動作
    - data/stop_requested.flag があると起動せず終了
    - 実行中は PID ファイル (data/execution.pid デフォルト) を管理
    - 設定に応じて risk_manager, order_manager, reconciler が組み合わされて発注を実行

- Monitoring（システム監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を指定（デフォルト 60）
  - 監視は monitoring DB (sqlite_path) にログを書き、KillSwitch 条件を満たせば data/kill.flag を作成
  - 停止は data/stop_requested.flag を作成すると監視ループを終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB 指定可能

- AI 機能（スコアリング / レジーム判定）
  - ニューススコアリング:
    - kabusys.ai.score_news を呼び出し（プログラム内 API）または利用予定のラッパー CLI を実装して使用
    - OPENAI_API_KEY が必要
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime（同上、API キー必須）

注意:
- AI 機能は OpenAI API キー（OPENAI_API_KEY）を必要とします。API 利用料・レート制限に注意してください。
- .env ファイルは機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。

設定関連
---------
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を基点）から .env と .env.local を自動的に読み込みます
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーションで出力（30日保持）
  - setup_logging() により root ロガーを統一的に設定
  - LOG_DIR / LOG_LEVEL 環境変数で調整可能

プロセス制御 / フラグファイル
----------------------------
- stop_requested.flag (data/stop_requested.flag)
  - run_monitoring / run_execution が監視している停止要求フラグ（ファイル存在でプロセス終了）
- kill.flag (Settings.kill_flag_path デフォルト data/kill.flag)
  - Monitoring の KillSwitch が条件を満たした際に作成。ExecutionEngine はこの flag を検出して停止する仕組みを想定
- PID ファイル:
  - ExecutionEngine は起動時に PID ファイルを書き、停止時に削除する（_EXECUTION_PID = data/execution.pid）

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys 以下）
- __init__.py
- config.py                — 環境変数 / 設定管理（Settings）
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py            — ニュース NLP スコアリング
  - regime_detector.py     — マクロ + ETF でレジーム判定
- monitoring/
  - monitoring_db.py       — SQLite ベースの永続層（schema init + MonitoringDB クラス）
  - system_monitor.py      — システム稼働・データ鮮度監視
  - trade_monitor.py       — 発注 / 約定監視（省略ファイルあり）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag 書き込みロジック
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - alert_manager.py       — アラート配信（LINE 等）※実装に依存
- portfolio/
  - portfolio_builder.py   — 候補選定、等重/スコア重み計算
  - position_sizing.py     — 株数決定・aggregate cap・単元丸め
  - risk_adjustment.py     — セクター上限、レジーム乗数
- research/
  - factor_research.py     — Momentum / Volatility / Value ファクター計算（DuckDB 利用）
  - feature_exploration.py — forward returns / IC / summary
- tools/
  - paper_verification_report.py — Paper Trading 向け検証レポート生成
- utils/
  - logging_setup.py       — ロギング初期化ユーティリティ
  - process_priority.py    — プラットフォーム抽象化による優先度設定（psutil 利用）

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では LOG_LEVEL や KILL_FLAG_CLEAR_ON_START 等の設定を慎重に確認してください。
- .env に含まれる機密情報は厳重に管理してください。
- OpenAI を利用する機能は API 費用・レート制限の影響を受けます。大量呼び出しやバッチ運用時は注意してください。
- モニタリングは監視 DB（SQLite）を用いますが、運用でデータ膨張が予想される場合はバックアップ/ローテーションを検討してください。

開発者向けメモ
----------------
- DuckDB 接続を渡して各 research / ai 関数を呼ぶ設計になっています（外部 DB からの読み込みを関数内で行う）。
- 多くの関数は「副作用なし」の純粋関数になっており、単体テストがしやすい設計です。
- テスト時は環境変数の自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制すると便利です。
- OpenAI 呼び出し部分は内部で _call_openai_api を呼んでいるため、ユニットテストでは該当関数をモックできます。

ライセンス / コントリビューション
---------------------------------
（この README には記載がありません。プロジェクトルートの LICENSE を参照してください。）

以上がこのリポジトリの概要・セットアップ・基本的な使い方です。  
必要であれば、各モジュール（例: ExecutionEngine の詳細、TradeMonitor の仕様、alert_manager の接続方法など）に関する追記ドキュメントを作成します。どの項目を詳しくしますか？