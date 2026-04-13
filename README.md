KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買および研究用パイプラインを想定した Python パッケージです。
主な目的は以下です。

- 注文実行（ExecutionEngine）とリコンシリエーション
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio モジュール）
- リサーチ用ファクター計算（research モジュール）
- ニュース NLP による銘柄センチメント（OpenAI を利用、ai モジュール）
- Paper Trading 用検証ツール（tools）
- Streamlit を用いた監視ダッシュボード

主要な設計方針として、ルックアヘッドバイアス回避・DB分離（本番 / paper_trading）・API 呼び出しのフェイルセーフ化が組み込まれています。

機能一覧
--------
- Execution
  - 実際のブローカークライアントまたは Paper Trading (MockBrokerClient) による発注
  - リコンシリエーション（再起動後の同期処理）
  - リスク管理（RiskManager）と OrderManager（状態遷移管理）
- Monitoring
  - システム状態（CPU/Mem/Disk/プロセス PID）やデータ鮮度の定期ログ化
  - 注文滞留・約定異常の検出
  - ドローダウンやポジション数の監視 → kill.flag による安全停止シグナル
  - LINE Push によるアラート通知（AlertManager）
  - Streamlit ダッシュボード（監視情報の可視化）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - 将来リターン計算、IC 計算、統計サマリー
- AI
  - ニュースの銘柄別センチメント算出（OpenAI）
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト

セットアップ手順
----------------
※ 以下は推奨手順の例。プロジェクト独自の pyproject/requirements があればそちらに従ってください。

1. Python 仮想環境を作成・有効化（例: Python 3.10+ 推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   （実際の requirements.txt がある場合は pip install -r requirements.txt）

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数（.env）を準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限設定すべき主要キー（用途・デフォルト値付き）：
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定挙動: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
     - LOG_LEVEL — ログレベル（デフォルト: INFO）
     - PID_FILE_PATH / KILL_FLAG_PATH — PID / kill.flag のパス（デフォルトは data 以下）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値（%）
   - 例 .env 抜粋:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=yyyyy
     OPENAI_API_KEY=sk-...
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     ```

注意事項（Paper Trading）
- KABUSYS_ENV=paper_trading の場合、Execution は MockBrokerClient を使用し、Paper Trading 用 SQLite（data/paper_trading.db）へ記録され、本番 DB と分離されます。

使い方（コマンド）
-----------------

- 監視（Monitoring）を起動する（ポーリングループ）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔（秒）を上書きできます（デフォルト 60 秒、1 秒以上）。
  - 実行:
    - python -m kabusys.run_monitoring
  - 補足:
    - プロセス優先度を "high" に設定します（set_process_priority を呼びます）。
    - 監視は設定に関係なく sqlite_path（本番監視 DB）を使用します。

- 実行（ExecutionEngine）を起動する
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB を使用します。
  - 実行:
    - python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を read-only で開きます。MonitoringEngine が DB を作成・更新している必要があります。

- AI 機能（ニューススコア / レジーム判定）
  - ai.score_news / ai.score_regime を呼び出す際に OPENAI_API_KEY が必要です。
  - サンプル:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="sk-...")

プロセス優先度 / CPU affinity
- run_monitoring / run_execution の開始時に set_process_priority("high") を呼びます。
- この操作は OS と権限によって失敗することがあり、その場合はログに警告を出してスキップします。

監視・停止（kill.flag）
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止を促します（ExecutionEngine 側でこのフラグを監視する設計）。
- KillSwitch は重複書き込みを避け冪等に動作します。起動時にフラグを削除したい場合は設定やスクリプトから削除してください。Settings.kill_flag_clear_on_start を利用する設計があります。

主要ファイル・ディレクトリ構成
----------------------------
（src/kabusys 配下の主要モジュールを抜粋）

- src/kabusys/__init__.py
  - パッケージ定義、バージョン情報

- src/kabusys/config.py
  - 環境変数の自動読み込み (.env / .env.local)
  - Settings クラス（各種パス・閾値・フラグ等）

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時に MockBroker を利用）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 / 永続化 API（MonitoringDB）
  - system_monitor.py — CPU/Mem/Disk/データ鮮度/プロセス監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書込みロジック
  - alert_manager.py — LINE へのプッシュ通知
  - monitoring_engine.py — 各 Monitor の連携ループ
  - streamlit_dashboard.py — Streamlit ベースのダッシュボード

- src/kabusys/execution/
  - order_manager.py, reconciler.py など — 注文状態管理・リコンシリエーション関連

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・資金配分（lot 単位で丸め）
  - risk_adjustment.py — セクター上限・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum/Volatility/Value 計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- src/kabusys/ai/
  - news_nlp.py — ニュースから銘柄別センチメントを生成（OpenAI）
  - regime_detector.py — ma200 + マクロセンチメントでレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

データベース
------------
- 監視用 SQLite: Settings.sqlite_path（デフォルト data/monitoring.db）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを持つ。
- Paper Trading SQLite: Settings.paper_sqlite_path（デフォルト data/paper_trading.db）
  - Paper Trading 実行時に使用（本番 DB と分離）
- DuckDB: Settings.duckdb_path（デフォルト data/kabusys.duckdb）
  - prices_daily / raw_financials / raw_news 等の大型時系列データやリサーチ用データを格納

追加メモ / トラブルシューティング
--------------------------------
- MONITOR_POLL_INTERVAL は環境変数で監視間隔（秒）を設定できます。不正値や 0 以下はデフォルト 60 秒にフォールバックします。
- process priority の設定（高優先度）は OS 権限が必要になる場合があります。失敗しても処理は継続します。
- OpenAI 呼び出しはネットワークやレート制限が発生するため、内部でリトライやフェイルセーフ（失敗時は 0.0 等にフォールバック）を実装しています。
- DuckDB での executemany はバージョンによって空リストの扱いが異なるためコード上で guard しています。
- .env の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に基づきます。テスト等で自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス・貢献
---------------
このリポジトリのライセンス・コントリビュート方法はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（ここでは省略）。

以上。初期セットアップや特定機能の実行についてさらに詳細が必要であれば、どの機能（例: ExecutionEngine の起動オプション、AI モジュールの呼び出し方、DB スキーマ詳細 等）を知りたいか教えてください。