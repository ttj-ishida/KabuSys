KabuSys — 日本株自動売買システム
=============================

このリポジトリは「KabuSys」と呼ばれる日本株向け自動売買システムのコードベースです。取引実行、監視、ポートフォリオ構築、研究（ファクター計算）、およびニュース NLP / レジーム判定などの補助ツールを含みます。

主な特徴
--------
- Execution Engine
  - ブローカークライアント経由で発注・状態管理を行う実行コンポーネント（再起動時のリコンシリエーション機能あり）。
  - paper_trading モードでは MockBrokerClient を使用し、本番 DB と完全分離された data/paper_trading.db に記録。
- Monitoring
  - システム状態（CPU/メモリ/ディスク）・プロセス監視、データ鮮度チェック、滞留注文・約定異常検出、ドローダウン・ポジション上限監視。
  - kill.flag による安全停止シグナル、LINE 通知（AlertManager）や Streamlit ダッシュボードを提供。
- Portfolio Construction
  - 候補選定、等配分／スコア加重配分、セクター制約、ポジションサイズ計算（単元株丸め・集約キャップ対応）などの純粋関数群。
- Research
  - DuckDB 上の価格・財務データからモメンタム／ボラティリティ／バリュー等のファクター計算、将来リターン計算・IC 等の解析ユーティリティ。
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリングと、それを用いた市場レジーム判定。API エラー時はフェイルセーフ（スコアを 0 にフォールバック）で動作。
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定で稼働率・成功率・レイテンシ等を表示）。
  - Streamlit ベースの監視ダッシュボード。

セットアップ手順
----------------
1. Python 環境（推奨: 3.10+）を用意し、仮想環境を作成・有効化します。
   - 例（Unix/macOS）:
     - python -m venv .venv
     - source .venv/bin/activate
2. 依存パッケージをインストールします。
   - 主要な依存例:
     - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （本リポジトリに requirements.txt がある場合はそれを利用してください）
3. データディレクトリを作成（デフォルトの DB パス用）:
   - mkdir -p data
4. 環境変数の設定:
   - プロジェクトルート（.git または pyproject.toml のある場所）に .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動読み込みを無効化できます）。
   - 主な必須/任意環境変数（Settings 参照）:
     - 必須（本番利用時）:
       - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
       - KABU_API_PASSWORD — kabuステーション API パスワード
     - 任意/設定:
       - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
       - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
       - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知
       - DUCKDB_PATH (default: data/kabusys.duckdb)
       - SQLITE_PATH (default: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
       - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動
       - PID_FILE_PATH, KILL_FLAG_PATH 等の監視関連パス
       - KABUSYS_ENV: development | paper_trading | live（default: development）
       - LOG_LEVEL（DEBUG/INFO/...）、MONITOR_POLL_INTERVAL（監視ポーリング秒 — 既定 60）
       - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT 等
5. データベース初期化:
   - run_monitoring/run_execution 実行時に監視用 SQLite のテーブルは自動作成（init_monitoring_db）されます。
   - DuckDB は prices_daily / raw_financials 等のテーブルが必要です（データ投入は別途行ってください）。

使い方（主要コマンド）
--------------------
- 実行エンジン起動（通常の実行）
  - python -m kabusys.run_execution
  - 注意: 実行前に環境変数 KABUSYS_ENV を適切に設定してください。
    - 本番: export KABUSYS_ENV=live
    - ペーパートレード: export KABUSYS_ENV=paper_trading
      - paper_trading 時は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH に記録します。
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は Settings による sqlite_path（監視用 DB）に永続化します（Monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）。
- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開く想定。MonitoringEngine 実行中に表示するのが推奨。
- AI / レジーム判定 / ニューススコア
  - kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime 等の関数をプログラムから呼び出せます（OpenAI API キーが必要）。
  - 例（スクリプト内）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

運用上の注意
-----------
- KABUSYS_ENV が paper_trading のときは、発注履歴や監視ログの DB を本番と分離して運用してください（既定で data/paper_trading.db を使用）。
- Monitoring の process チェックは pid ファイル（Settings.pid_file_path）を参照します。ExecutionEngine は自身の PID を該当ファイルに書き込む設計（本コード内の該当処理を確認してください）。
- OpenAI API を使用する機能は外部 API 呼び出しを伴うため、API 料金・レート制限に注意してください。実行時は OPENAI_API_KEY を設定してください。
- .env の自動ロードはプロジェクトルート検出に基づき行われます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- LINE 通知は AlertManager によりクールダウン制御（カテゴリ毎）が行われます。チャンネル設定が未設定の場合は送信はスキップされログに記録されます。

ディレクトリ構成（主なファイル・モジュール）
----------------------------------------
- src/kabusys/
  - __init__.py — パッケージ情報（__version__ 等）
  - config.py — 環境変数 / 設定管理（Settings）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - execution/
    - order_manager.py — 発注ロジック（OrderManager）
    - reconciler.py — 再起動時のリコンシリエーション
    - その他（broker_factory 等 ブローカ関連）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブルの定義と永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag による停止シグナル生成
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数決定ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等の計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC 等
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）と ai_scores 書き込み
    - regime_detector.py — ETF MA + マクロセンチメントでレジーム判定
  - data/ （実行時に使用されるデフォルトパス）
    - kabusys.duckdb — DuckDB（データ投入が必要）
    - monitoring.db — 監視用 SQLite（自動作成）
    - paper_trading.db — paper_trading 用 SQLite（paper_trading 環境時）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

よくある質問 / トラブルシューティング
------------------------------------
- Q: DuckDB / prices_daily がないとどうなる？
  - A: research / ai / regime 判定など一部機能は prices_daily や raw_financials 等のテーブルを前提としています。これらがないと該当処理は失敗またはデフォルトフォールバック動作になります。事前にデータ投入してください。
- Q: OpenAI 呼び出しで頻繁に失敗する
  - A: リトライロジックは実装されていますが、API キー・レート制限・ネットワーク状況を確認してください。テスト時は外部呼出しをモックすることを推奨します。
- Q: MONITOR_POLL_INTERVAL に 0 を設定したら？
  - A: 0 以下の値は無効とみなされ警告が出てデフォルト（60 秒）にフォールバックします。

貢献 / 開発
-----------
- ローカル開発: 仮想環境を用意し、変更毎にユニットテスト・ローカルモジュールを実行して動作検証してください。
- .env.example を用意して環境変数のテンプレートを共有すると設定しやすくなります（本リポジトリに無ければ作成を推奨）。

ライセンス・その他
------------------
- 本 README ではライセンス情報は記載していません。実プロジェクトでは適切な LICENSE ファイルを追加してください。

最後に
-------
本 README はコードベースの主要な使い方・構成をまとめた簡易ドキュメントです。詳細は各モジュールの docstring（ソース）や Settings、各スクリプトのヘルプ（--help）を参照してください。必要なら実行例や .env.example のテンプレートを追加します。ご希望があれば作成します。