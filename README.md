README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の骨組み（ライブラリ）です。  
主要な機能群は「Execution（発注エンジン）」「Monitoring（監視）」「Portfolio（銘柄選定／サイズ算出）」「Research（ファクター計算・特徴量解析）」「AI（ニュース NLP / レジーム判定）」等で構成されています。  
設計方針として、現物の発注ロジックとデータ解析ロジックを分離し、ペーパートレード環境や本番環境に応じた挙動切替や冪等性、フェイルセーフ（部分失敗でシステム全体が止まらない）を重視しています。

主な機能一覧
-------------
- Execution
  - 実取引（live）／ペーパートレード（paper_trading）を切り替えて実行可能
  - ブローカークライアントの抽象化（BrokerClientFactory）
  - 発注管理（OrderManager / ExecutionEngine）
  - リスク管理（RiskManager / Reconciler）
- Monitoring
  - システム状態・データ鮮度監視（SystemMonitor）
  - 注文ログ・約定監視（TradeMonitor）
  - ドローダウン／ポジション上限監視（RiskMonitor）
  - Kill Switch による外部停止（data/kill.flag）
  - 監視ログの永続化（SQLite via monitoring_db）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等比・スコア加重）
  - ポジションサイズ算出（リスクベース、等配分、スコア配分）
  - セクター制限・レジーム乗数の適用
- Research
  - ファクター計算（モメンタム/バリュー/ボラティリティ等、DuckDB を利用）
  - 将来リターン計算 / IC 計算 / 統計サマリー
- AI
  - ニュースを LLM（OpenAI）でスコアリングし、ai_scores に保存（news_nlp）
  - マクロニュース＋ETF MA200 乖離から日次レジーム判定（regime_detector）
  - API 呼び出しは堅牢なリトライ・バリデーション実装
- ツール
  - config_setup: .env を対話式に作成
  - validate_config: 起動前チェック（env, config YAML, DB パス等）
  - paper_verification_report: ペーパートレードの検証レポート生成

セットアップ手順
----------------
前提:
- Python 3.10+ を推奨（コードは型ヒントで新しい構文を使っているため）
- 必要な Python パッケージ（主なもの）:
  - duckdb, psutil, openai, PyYAML（任意・設定検証用）など

推奨手順（プロジェクトルートで実行）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - .venv\Scripts\activate (Windows) / source .venv/bin/activate (Unix)

2. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 無い場合の例（最低限）:
     - pip install duckdb psutil openai PyYAML

3. 環境変数設定（.env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考）  
     重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live。デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（instant|partial|never|reject、デフォルト: instant）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動消去する場合は 1。production では 0 推奨）
     - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒数、デフォルト 60）

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになる

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

使い方
------
各コンポーネントの実行方法（モジュールとして起動可能）:

- Execution Engine を起動
  - 本番/ペーパートレードは KABUSYS_ENV によって切替
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 SQLite（data/paper_trading.db）へ記録して本番 DB とは完全に分離されます
    - 起動時に data/stop_requested.flag が存在する場合は起動を行いません
    - 実行中に data/stop_requested.flag を作成すると Engine が安全に停止します

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（環境に無関係に同じ監視 DB を使用）

- .env の生成/編集（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付与すると警告も失敗扱い

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- AI 機能（プログラム的に呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=...)  # conn: duckdb connection
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

ログ・プロセス管理
- ログは kabusys.utils.logging_setup.setup_logging により統一管理され、デフォルトで logs/<app_name>.log に日次ローテートで出力されます。
- 起動スクリプトは set_process_priority("high") を呼び出してプロセス優先度を上げます（プラットフォーム依存）。
- モニタ／実行エンジンの停止:
  - 外部から停止リクエストを出すにはプロジェクトの data/stop_requested.flag を作成します（run_monitoring/run_execution はこれを見て停止します）。
  - KillSwitch（監視）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine はこれを検出して停止します。

重要なファイル／DB
- data/monitoring.db — 監視ログ（SQLite）
- data/kabusys.duckdb — 分析用 DuckDB
- data/paper_trading.db — (KABUSYS_ENV=paper_trading時の) ペーパートレード用 SQLite
- data/kill.flag — Kill Switch による停止フラグ
- data/stop_requested.flag — 手動停止リクエスト（プロセスが起動中に存在すれば停止）

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                   — .env 自動読み込み / Settings
- config_setup.py             — .env 対話式ウィザード
- validate_config.py          — 起動前検証 CLI
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — SystemMonitor 起動スクリプト

subpackages:
- ai/
  - news_nlp.py                — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py        — 日次レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py          — SQLite テーブル定義 + 永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py          — （アラート送信管理：LINE 等）
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- data/
  - pipeline.py (prices_daily 取得等）  ※ (参照される想定)
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

注意事項 / 運用メモ
------------------
- 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨します。1 にすると起動時に既存の kill.flag を自動でクリアしてしまい安全性が低下します。
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）と API 利用ルールに従って利用してください。大量バッチ処理はレート制限に注意。
- DuckDB / SQLite のパスは Settings で制御可能。開発時はデフォルトの data/ 配下を使いますが、本番では絶対パスを推奨します。
- .env は決して Git にコミットしないでください（README と config_setup のヘッダにも明記されています）。
- validate_config で config/*.yaml の存在確認を行います。PyYAML が無い場合は YAML 検証をスキップします（警告）。

貢献 / 拡張案
--------------
- ストラテジー / シグナル生成モジュールの追加（strategy パッケージ）
- ブローカークライアントの実装（kabuステーション ラッパー等）
- 単元株サイズや銘柄別 lot_size のマスタ対応（position_sizing の拡張）
- モニタリング通知先の追加（Slack, PagerDuty 等）

ライセンス
----------
（このプロジェクトに付与されたライセンスをここに記述してください）

問い合わせ
----------
開発・運用に関する質問はリポジトリの ISSUE・Pull Request でお願いします。

以上。README に記載してほしい追加の詳細や、特定のコマンド例（systemd / supervisor 用の起動スクリプト等）が必要であれば教えてください。