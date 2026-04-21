KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買やそれを支える監視・リサーチ機能を備えた Python パッケージです。  
主な目的は戦略の実行（ExecutionEngine）とシステム監視（Monitoring）を分離して安全に運用できること、また DuckDB を用いたファクター計算や LLM を用いたニュースセンチメント評価などの研究機能を提供することです。

主な特徴
--------
- 実行エンジン（ExecutionEngine）
  - live / paper_trading / development の環境切替
  - ブローカーインターフェース抽象化（実ブローカ or Mock）
  - リスク管理（Position / Drawdown / Rate limiting 等）
- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）やデータ鮮度をポーリング監視
  - 注文ログ・ポジション・リスクログの永続化（SQLite）
  - Kill Switch（異常時に ExecutionEngine 停止のためのフラグ書き込み）
  - アラート管理（LINE 連携等を想定）
- ポートフォリオ構築ユーティリティ（選定、重み付け、ポジションサイズ計算）
- 研究モジュール（DuckDB ベースのファクター計算、特徴量探索、IC 計算）
- AI モジュール（OpenAI を使ったニュース NLP スコアリング、レジーム判定）
- 運用・検証ツール
  - .env 対話式作成ウィザード（config_setup）
  - 起動前チェック（validate_config）
  - ペーパートレード検証レポート生成ツール

セットアップ手順
----------------

1. リポジトリをクローンする（パッケージ配布・配置済みの想定でも同様）:
   - git clone … && cd <project_root>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .\.venv\Scripts\activate

3. 依存関係をインストール
   - 必要な主なライブラリ:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML 検証に使用）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt を実行）

4. ディレクトリ作成（データ・ログ用）
   - mkdir -p data logs
   - あるいは Windows であれば explorer 等で作成

5. 環境変数の設定 (.env)
   - 対話式ウィザードを使って .env を生成:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参考に）
   - 重要な環境変数（抜粋・デフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視DB、デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: INFO（デフォルト）
     - OPENAI_API_KEY: OpenAI API を使用する場合に必要

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit 1）

使い方
------

1. 監視プロセスを起動
   - デフォルトで poll interval は 60 秒
   - 環境変数で上書き可能: MONITOR_POLL_INTERVAL（秒）
   - 実行:
     - python -m kabusys.run_monitoring
   - 補足:
     - 監視は Settings に従い sqlite_path を使用します（monitoring は環境にかかわらず本番 sqlite を参照します）
     - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します

2. 実行エンジン（ExecutionEngine）を起動
   - paper_trading モード（MockBroker）で起動する例:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - live モード:
     - KABUSYS_ENV=live python -m kabusys.run_execution
     - ※ 本番モードでは必ず設定内容を確認してください（LINE 通知、kill flag 設定等）
   - 実行前に kill flag を自動クリアしたくない場合は KILL_FLAG_CLEAR_ON_START=0（デフォルト）

3. ペーパートレード検証レポート
   - SQLite に保存されたペーパートレードログから簡易レポートを生成
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パス指定:
     - --db path/to/paper_trading.db
     - または 環境変数 PAPER_TRADING_SQLITE_PATH を設定

4. AI 関連（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY）
   - プログラム的に呼ぶ関数:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意:
     - API 呼び出し失敗時はフォールバックを採るよう設計（フェイルセーフ）

運用上のポイント
----------------
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）、デフォルト 60
- 停止制御:
  - プロセス停止要求: data/stop_requested.flag を作成（run_* スクリプトは検知して終了）
  - Kill Switch（致命的なリスク到達時に ExecutionEngine を止める）: data/kill.flag を書き込む仕組みあり
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力（デフォルト 30 日保存）
  - setup_logging を全スクリプトで使用して一貫したログ設定
- DB:
  - 監視ログは SQLite（Settings.sqlite_path）
  - 分析用は DuckDB（Settings.duckdb_path）
  - paper_trading を選ぶと execution は paper_sqlite_path を使い本番 DB と分離

ディレクトリ構成（主なファイル）
------------------------------
（src/kabusys 以下を想定した簡易ツリー）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 定義（デフォルト値・検証含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - execution/                  — 実行エンジン関連（BrokerFactory, ExecutionEngine, Order 管理等）
    - (複数モジュール: execution_engine.py, order_manager.py, risk_manager.py ... )
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ初期化 + Persistence API
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文ログ監視（滞留注文・約定異常等）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 管理
    - monitoring_engine.py     — 各 Monitor を統合してポーリング
    - alert_manager.py         — アラート送信（LINE 等、抽象化）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 発注株数計算・丸めロジック
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Value/Volatility 等ファクター計算（DuckDB）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py              — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py       — マクロ + ETF MA200 で市場レジーム判定
  - data/                      — （運用時に使用）データベース・フラグ等を置く想定ディレクトリ
  - logs/                      — ログ出力先（デフォルト）

補足（設計上の注意）
-------------------
- 設定の自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local を自動読み込みします。
  - テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は存在チェックと簡易マイグレーション（カラム追加）を行います（冪等）。
- フェイルセーフ
  - AI 呼び出しや外部 API 呼び出しはリトライやフォールバック（0.0 スコア等）を備え、例外でプロセスを止めない設計です。

よく使うコマンドまとめ
---------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 監視起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ライセンス・貢献
----------------
- この README はコードベースの説明を目的としたドキュメントです。実際のライセンス・貢献ルールはリポジトリの LICENSE や CONTRIBUTING を参照してください。

お問い合わせ・次のステップ
-------------------------
- 開発環境を構築したら、まず python -m kabusys.config_setup → python -m kabusys.validate_config を実行して設定を確認してください。  
- DuckDB に価格データや raw_news 等のテーブルを投入すると research / ai 機能を試すことができます。

必要であれば README に「起動例」「環境変数の全リスト」「詳細なディレクトリツリー（ファイル毎の説明）」を追加で出力します。どの情報を追記しますか？