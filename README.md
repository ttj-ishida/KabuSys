README
======

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした Python ベースのシステムです。本リポジトリには発注エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築ロジック・ファクター計算・AI を用いたニュースセンチメント/レジーム判定や実行結果検証ツールが含まれます。DB 永続化には SQLite（監視ログ・orders 等）と DuckDB（価格データ・ファクター計算用）を使用します。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - ブローカークライアント抽象化（実口座／ペーパートレード切替）
  - リスク管理（ポジション上限・利用率等）
  - 起動時のリコンシリエーション（ブローカーと注文・ポジションの突合）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度監視
  - TradeMonitor: 滞留注文、約定価格の異常検出
  - RiskMonitor: ドローダウン / ポジション数監視、ダッシュボード更新
  - KillSwitch: しきい値到達で flag ファイルを書いて ExecutionEngine 停止を促す
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重配分、リスク調整（セクター制約、レジーム乗数）、株数決定（単元丸め・aggregate cap）
- Research（ファクター計算 / 特徴量解析）
  - Momentum, Volatility, Value 等のファクター算出
  - 将来リターン、IC（Spearman）計算、統計サマリ
- AI モジュール
  - ニュースを OpenAI（gpt-4o-mini）でセンチメント評価して ai_scores に書込
  - マクロニュース + ETF MA200 乖離で市場レジーム（bull/neutral/bear）を判定
  - 再試行・バッチ化・レスポンス検証・フェイルセーフ設計
- ツール
  - Paper Trading の検証レポート生成スクリプト（期間指定可）

依存関係（代表）
----------------
最低限インストールが必要なパッケージ（例）：
- python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード使用時)

インストール例:
pip install -r requirements.txt
（requirements.txt がない場合は上記パッケージを個別に pip install してください）

セットアップ手順
---------------
1. リポジトリをクローンして作業ディレクトリに移動します。
2. Python 仮想環境を作成・有効化（推奨）。
3. 依存パッケージをインストールします（上記参照）。
4. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置くと自動でロードされます（OS 環境変数が優先）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
5. 主要な環境変数（主なもの）:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に必要
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading 時に使用、デフォルト: data/paper_trading.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH: ExecutionEngine 用 pid ファイルパス（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill flag ファイルパス（デフォルト: data/kill.flag）
   - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト: instant）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
   - LOG_LEVEL: ログレベル（DEBUG, INFO, ...）
6. データディレクトリ作成:
   mkdir -p data

使い方（実行例）
----------------

- ExecutionEngine（運用・ペーパー切替自動）
  - 本番/開発/ペーパーは KABUSYS_ENV で切替。
    - ペーパー時は MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（または data/paper_trading.db）に記録されます。
  - 起動:
    python -m kabusys.run_execution
  - 起動直後にプロセス優先度を "high" に設定し、DB 初期化・ブローカー生成・エンジン起動を行います。

- Monitoring（ポーリング監視）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（デフォルト 60 秒）。
  - 起動:
    python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path を使って監視テーブルを記録します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード（監視の可視化）
  - 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを提供します。

- Paper Trading 検証レポート
  - 使い方:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パス指定可能（優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）。

- AI 関連（ニューススコア / レジーム判定）
  - ニュースセンチメントを ai_scores に書き込む:
    - モジュール関数を呼ぶか、該当スクリプトから実行（API キーが必要）。
    - score_news(conn, target_date, api_key=None) を使用。api_key が None の場合は OPENAI_API_KEY を参照します。
  - レジーム判定:
    - score_regime(conn, target_date, api_key=None) を呼ぶと market_regime テーブルに冪等書込みされます。
  - 注意:
    - API 呼び出しはバッチ化・リトライ・レスポンス検証済みで、失敗時は安全にフォールバック（例: macro_sentiment = 0.0）します。

運用上の注意
------------
- kill.flag: KillSwitch は条件達成時に KILL_FLAG_PATH（デフォルト data/kill.flag）を書きます。ExecutionEngine はこのフラグに応じて停止します。起動時にフラグをクリアする設定もあります（Settings.kill_flag_clear_on_start）。
- PID ファイル: ExecutionEngine は PID ファイルを data/execution.pid に書きます。SystemMonitor はこの PID を見てプロセス生存を検査します。
- DB マイグレーション: monitoring_db.init_monitoring_db() は必要なテーブル／インデックスを作成し、既存 DB に不足カラムがあれば簡易マイグレーション（ALTER TABLE を用いたカラム追加）を行います。
- 環境変数は .env/.env.local から自動読み込みされます（プロジェクトルートの検出に .git または pyproject.toml を使用）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py: パッケージ定義・バージョン
  - config.py: 環境設定読み込み（.env サポート）、Settings クラス
  - run_execution.py: ExecutionEngine 起動スクリプト
  - run_monitoring.py: SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py: ペーパートレード検証レポート CLI
  - execution/
    - reconciler.py: 起動時の注文・ポジションリコンシリエーション
    - order_manager.py: 発注フロー（状態遷移・send/recv）
    - order_repository.py, order_record.py ...（発注関連DB/モデル）※一部省略
    - broker_factory.py, broker_api.py, ...（ブローカー抽象化）
  - monitoring/
    - monitoring_db.py: SQLite による監視ログ層（テーブル作成・CRUD）
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: 注文滞留・約定異常監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag 制御
    - alert_manager.py: LINE 通知
    - monitoring_engine.py: 監視コンポーネント統合
    - streamlit_dashboard.py: streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py: 候補選定・重み計算
    - risk_adjustment.py: セクター制約・レジーム乗数
    - position_sizing.py: 株数決定・aggregate cap
  - research/
    - factor_research.py: Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC などの解析ユーティリティ
  - ai/
    - news_nlp.py: ニュースセンチメント取得（OpenAI）
    - regime_detector.py: マクロ + ETF MA200 でレジーム判定
  - data/, logs/ 等の格納はプロジェクトルートの data ディレクトリを想定

開発者向けメモ
---------------
- 設定は Settings クラスを通じて取得してください（kabusys.config.Settings）。
- DuckDB 接続はリサーチ・AI モジュールで使われます。prices_daily / raw_financials / raw_news 等のテーブルが存在することが前提です。
- AI 呼び出し箇所（news_nlp, regime_detector）は OpenAI SDK のエラー種別（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対応したリトライ設計になっています。テスト時は _call_openai_api をモックしてください。
- process priority / cpu affinity の設定は utils/process_priority.py に集約されています。プラットフォーム差分を吸収する実装です。

ライセンス・貢献
----------------
（ここにライセンス情報や貢献方法を追記してください）

お問い合わせ
------------
不明点やバグ報告は Issues をご利用ください。

以上。README の内容をプロジェクトの実態に合わせて調整してください。