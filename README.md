KabuSys — 日本株自動売買システム
================================

本ドキュメントはこのリポジトリ（src/kabusys）に含まれる主要コンポーネントの概要、機能、セットアップ手順、実行方法、およびディレクトリ構成をまとめた README です。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システム（プロトタイプ）です。主な目的は以下です。

- シグナルからの発注管理とブローカー連携（実口座／ペーパートレード）
- 実行時のリスク管理（ドローダウン監視・ポジション上限など）
- システム監視（プロセス生存／リソース使用率／データ鮮度）
- ポートフォリオ構築・株数決定ロジック（等配分・スコア加重・リスクベース 等）
- 研究用ファクター計算 / 特徴量解析（DuckDB を用いたオンチェーン解析）
- AI（LLM）を用いたニュースのセンチメント評価・市場レジーム判定
- 運用検証・レポート生成ツール、監視用 Streamlit ダッシュボード

重要設計方針の抜粋：
- 本番・ペーパートレードは DB 層で分離（paper_trading 用 DB が使用可能）
- ルックアヘッドバイアス回避のため、対象日付の処理では date.today() 等を不用意に参照しない実装
- 外部 API（OpenAI 等）失敗時はフェイルセーフで続行する設計

機能一覧
--------
- Execution
  - ExecutionEngine を起動してシグナルを受け発注（kabuステーション等のブローカー経由）
  - Reconciler による起動時リコンシリエーション（注文／ポジションの突合）
  - OrderManager / OrderRepository による注文状態管理
  - RiskManager による上限・レート制限管理
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch: 条件達成時にフラグファイルを書き ExecutionEngine 停止を促す
  - AlertManager: LINE Push による通知（オプション）
  - Streamlit ダッシュボード（読み取り専用）
- Portfolio
  - 候補選定、等配分／スコア配分、リスク調整（セクターキャップ・レジーム乗数）
  - 株数決定（単元丸め・利用可能現金に基づくスケールダウン等）
- Research
  - ファクター計算（Momentum/Volatility/Value）
  - 将来リターン、IC 計算、統計サマリー
- AI
  - news_nlp: ニュースの銘柄別センチメントを OpenAI で取得 → ai_scores テーブルへ
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を算出
- Tools
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを出力

セットアップ手順
----------------
以下はローカルで動かす際の基本的な手順例です。

1. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必要パッケージの例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

3. データディレクトリ作成
   - デフォルトでは data/ 配下のファイルを参照します。存在しない場合は作成してください。
     - mkdir -p data

4. 環境変数 / .env
   - 必須（運用時）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を実行する場合:
     - OPENAI_API_KEY
   - その他（デフォルトが設定されているものも含む）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading の約定挙動
     - PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL / CPU/MEM/DISK 閾値 など
   - .env 自動読み込み:
     - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動で読み込みます。
     - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DB 初期化
   - run_monitoring.py / run_execution.py 実行時に init_monitoring_db が呼ばれ、監視用 SQLite のテーブルを作成します。
   - DuckDB（prices_daily / raw_financials 等のテーブル）は事前にデータを用意してください（研究機能を使う場合）。

使い方（コマンド例）
-------------------

- ExecutionEngine を起動（本番 or paper_trading は KABUSYS_ENV による）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - KABUSYS_ENV=live python -m kabusys.run_execution

- Monitoring を起動（ポーリングループ）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（デフォルト 60）。
  - python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path を用いて動作します（KABUSYS_ENV に依らず本番 DB を監視）。

- Streamlit ダッシュボード（監視情報の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

主要な環境変数（主要項目）
-------------------------
- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 認証トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文約定モード）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行中プロセス制御用ファイルパス

注意点／運用メモ
----------------
- run_execution / run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（psutil を利用）。アクセス権がない場合は警告が出ますが、処理は継続します。
- kill.flag による停止シグナルは KillSwitch によって作成され、ExecutionEngine 側は起動時にこのフラグをチェックして停止できます（設定により起動時にフラグをクリアする挙動あり）。
- Paper Trading は本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API 呼び出しは外部サービスへの依存があるため、API 失敗時は安全側でスコア 0 等にフォールバックする実装です。API キーが未設定の場合は例外を投げる箇所があります（呼び出し側でキャッチしてください）。
- DuckDB は大規模データ分析用に使われるため、prices_daily / raw_financials 等の事前ロードが必要です（研究機能）。

ディレクトリ構成（src/kabusys の抜粋）
------------------------------------
以下は主要なサブパッケージと役割の一覧です（ファイル名は代表例）。

- kabusys/
  - __init__.py (パッケージ情報)
  - config.py — 環境変数 / .env の読み込みと Settings 抽象化
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - execution_engine.py (実行エンジン) — （実装ファイルの一部はリポジトリ内に存在）
    - order_manager.py — 注文の状態遷移・送信ロジック
    - order_repository.py — SQLite を使った注文永続化
    - reconciler.py — 起動時リコンシリエーション
    - broker_factory.py, broker_api.py — ブローカークライアント関連

  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル定義と簡易 API
    - system_monitor.py — システムリソース／データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルを用いた停止シグナル
    - alert_manager.py — LINE 通知（push）
    - monitoring_engine.py — Monitor を束ねるループ
    - streamlit_dashboard.py — 監視ダッシュボード（Streamlit）

  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value の計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー

  - ai/
    - news_nlp.py — ニュースの LLM によるセンチメント評価と ai_scores 書き込み
    - regime_detector.py — 市場レジーム判定と market_regime 書き込み

  - tools/
    - paper_verification_report.py — ペーパートレード DB から検証レポートを生成

  - utils/
    - process_priority.py — psutil を使った優先度 / CPU affinity 設定ユーティリティ

開発・拡張ポイント
------------------
- DuckDB の prices_daily / raw_financials 等のデータ整備は研究モジュールの前提。
- ブローカークライアントは抽象化されており、Mock / 実ブローカーの切り替えが可能。
- 単元（lot_size）や銘柄マスタ等の拡張は将来的に portfolio 側で想定（コメントに TODO あり）。
- AI 関連のテストは外部 API をモック(_call_openai_api を patch) して行えるように設計されています。

トラブルシューティング（よくある問題）
------------------------------------
- OpenAI API キー未設定で AI 機能を呼んだ場合：ValueError が発生します。OPENAI_API_KEY を設定してください。
- psutil による優先度設定で AccessDenied が出る場合：権限不足であり、処理は継続します（警告ログ）。
- Streamlit ダッシュボードが DB を開けない場合：MonitoringEngine が起動していて DB ファイルが存在するか確認してください。起動時に monitoring DB を初期化します。
- MONITOR_POLL_INTERVAL に 0 や負の値を設定した場合：警告ログが出てデフォルト 60 秒にフォールバックします。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報やコントリビュート手順はプロジェクトルート（pyproject.toml や LICENSE 等）を参照してください。

問い合わせ
----------
- 実装や運用方法についての質問・修正提案はリポジトリの Issue を通じてお願いします。

以上が KabuSys の概要と利用方法のまとめです。必要に応じて README にサンプル .env.example の追加や requirements.txt の整備を行ってください。