# KabuSys

日本株自動売買システムの一部を含むコードベース向け README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成を記載しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買およびそれに付随する監視・リサーチツール群を含むパッケージです。本リポジトリの主要機能は次のとおりです。

- 実際の発注を行う ExecutionEngine（本番／紙トレードに対応）
- システム・注文・リスク監視（監視 DB への永続化、アラート送信）
- ポートフォリオ構築（候補選定、重み算出、株数決定）
- リサーチ（ファクター計算・特徴量解析）
- AI を用いたニュースセンチメントや市場レジーム判定（OpenAI API）
- 運用補助ツール（紙トレード検証レポート、Streamlit ダッシュボード等）

設計方針として、DuckDB/SQLite を用いたデータ永続化、外部 API 呼び出しのフェイルセーフ化、ルックアヘッドバイアス回避、プラットフォーム差分吸収（プロセス優先度など）を重視しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注、リスク管理、オーダー管理、リコンシリエーション）
  - Paper trading モード（KABUSYS_ENV=paper_trading）で本番 DB と分離した専用 SQLite を使用
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・プロセス生存確認・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新、risk_logs 記録
  - KillSwitch：条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio
  - 候補選定、スコア基準・等分配・リスクベース配分、セクター制限、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン計算、IC、統計サマリ）
- AI
  - news_nlp: ニュース記事を集約して OpenAI により銘柄ごとのセンチメントを計算し ai_scores へ書込
  - regime_detector: ETF の MA とマクロニュースセンチメントを合成して市場レジーム判定
- Tools
  - paper_verification_report: 紙トレード DB を集計して検証レポートを生成
  - streamlit_dashboard: 監視 DB を可視化

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに new union 型や構文を使用）
- SQLite は標準ライブラリに含まれます

推奨手順（UNIX 系）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - 基本的に以下をインストールしてください（requirements.txt がない場合の一例）:
     - pip install duckdb psutil requests openai streamlit
   - 追加で使用するパッケージがあれば適宜インストールしてください。

3. 環境変数設定
   - ルートに `.env` / `.env.local` を配置することで自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとスキップ）。
   - 主要な環境変数（必須・オプション）:
     - 必須（Execution 等で必要）
       - JQUANTS_REFRESH_TOKEN — J-Quants（必須の場合）
       - KABU_API_PASSWORD — kabuステーション API パスワード
     - AI 関連（AI を使う場合）
       - OPENAI_API_KEY — OpenAI API キー
     - 運用・挙動
       - KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
       - LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
       - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
       - PAPER_FILL_MODE — paper_trading の注文約定モード（instant|partial|never|reject）
     - ファイルパス（デフォルト値は下記）
       - DUCKDB_PATH (default: data/kabusys.duckdb)
       - SQLITE_PATH (default: data/monitoring.db)
       - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
       - PID_FILE_PATH (default: data/execution.pid)
       - KILL_FLAG_PATH (default: data/kill.flag)

4. データディレクトリの作成（必要に応じて）
   - mkdir -p data

注意:
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要コマンド例）

前提: パッケージをプロジェクトルートから実行するか、PYTHONPATH を設定して `python -m kabusys.<module>` で実行します。

1. ExecutionEngine 起動（本番 or paper_trading）
   - 本番（デフォルト KABUSYS_ENV=development または live に応じて設定）
     - KABUSYS_ENV=live python -m kabusys.run_execution
   - 紙トレード
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - 紙トレード時は MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録されます。

   挙動:
   - 起動時に Process priority を "high" に設定（psutil の許可がない場合は警告で継続）。
   - stop フラグ（data/stop_requested.flag）が存在すると起動をスキップまたは実行中に停止します。
   - 実行中は PID を data/execution.pid に書きます（Settings.pid_file_path）。

2. Monitoring 起動（ポーリング監視）
   - MONITOR_POLL_INTERVAL を秒で指定可能（例: MONITOR_POLL_INTERVAL=30）
   - python -m kabusys.run_monitoring
   - 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に関係なく本番 DB を使う点に注意）。

3. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only URI 経由で DB を開きます。MonitoringEngine が書き込んでいる DB を想定。

4. 紙トレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション --db で PAPER_TRADING_SQLITE_PATH を上書き可能。

5. AI 機能（ニューススコア / レジーム判定）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - conn: DuckDB 接続
     - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
     - API キー未設定の場合は ValueError を発生
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - OpenAI API を用いてマクロセンチメントと ETF(ma200) を合成し market_regime テーブルへ書き込み

6. 停止用フラグ
   - 実行中のプロセスを止めさせるにはデータディレクトリに停止フラグを書きます:
     - data/stop_requested.flag — run_monitoring/run_execution はこのファイルを検知して優雅に終了します
     - data/kill.flag — KillSwitch により書き込まれ、ExecutionEngine に停止命令を送る用途で使用されます

---

## 重要な設計上の挙動・注意点

- .env 自動読み込み
  - OS 環境変数 > .env.local > .env の順で読み込み（既存の OS 環境変数は上書きされない）。
  - ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト用）。
- Monitoring の DB 使用
  - run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
- Paper trading
  - KABUSYS_ENV=paper_trading の場合、専用の PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）を使い本番 DB と分離します。
  - PAPER_FILL_MODE により MockBroker の約定挙動を制御できます（instant/partial/never/reject）。
- OpenAI 呼び出しの堅牢性
  - news_nlp/regime_detector は 429/タイムアウト/5xx 等を指数バックオフでリトライし、最終的にフォールバック値（例: macro_sentiment=0.0）で継続する設計です。API の失敗でプロセス全体が落ちることは基本的にありません。
- プロセス優先度設定
  - psutil による優先度/nice 値設定を試みますが、権限不足や未対応 OS の場合は警告を出してスキップします。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルと役割（リポジトリルートが src を含む構成を想定）。

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — Settings クラス（環境変数読み込み、既定値、検証）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- src/kabusys/execution/
  - order_manager.py — 発注 API を呼ぶ外向き API
  - reconciler.py — 起動時のリコンシリエーション（同期）
  - ...（broker_factory, execution_engine, order_repository 等が存在する想定）
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化 API（MonitoringDB）
  - system_monitor.py — システム状態 / データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — 停止フラグ生成
  - alert_manager.py — LINE 通知送信
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数決定、スケールダウンロジック
  - risk_adjustment.py — セクター制約、レジーム乗数
- src/kabusys/research/
  - factor_research.py — モメンタム、ボラティリティ、バリュー計算（DuckDB 利用）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- src/kabusys/ai/
  - news_nlp.py — ニュースを OpenAI に送り銘柄別センチメントを算出
  - regime_detector.py — マクロセンチメント＋ETF MA によるレジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — 紙トレード DB の検証レポート生成
- src/kabusys/utils/
  - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ

---

## よくある運用時の問合せ／トラブルシュート

- DB が初回起動で schema が足りない、カラムがないといったエラー：
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と簡易マイグレーション（カラム追加）を行います。適切な DB ファイルパス（Settings の SQLITE_PATH 等）を確認してください。
- OpenAI API 呼び出しが失敗する：
  - OPENAI_API_KEY が正しく設定されているか確認。API 呼び出しは失敗時もフォールバックする設計ですが、スコアが取れない場合があります。
- プロセス優先度が設定できない警告：
  - psutil の権限不足や OS 非対応の可能性があります。警告ログは出ますが通常動作は継続します。
- 監視・実行の停止方法：
  - data/stop_requested.flag を配置すると run_monitoring/run_execution はループ中に検知して優雅に終了します。KillSwitch が発動した場合は data/kill.flag が書かれます。

---

## 開発・拡張のヒント

- DuckDB 接続を渡す設計なので、research/ai のテストではインメモリ DuckDB を作ってテストデータを投入すると良いです。
- OpenAI 呼び出しはモジュール内で `_call_openai_api` として分離されているため unittest.mock.patch で差し替えてテスト可能です。
- データ鮮度チェックや各モニタは依存性注入（conn, repo, duckdb_conn 等）を受け取るため、ユニットテストが容易に書けます。
- Paper trading を活用して本番 DB と完全に分離したテストが可能です（PAPER_TRADING_SQLITE_PATH を指定）。

---

README に書かれているコマンドやパスはプロジェクトのルート構成に依存します。パッケージをインストールして利用する場合は適宜パス/モジュール名を調整してください。必要があれば使用例（.env の雛形、systemd / supervisor 用のユニット例、docker-compose 例）も追記できます。ご希望あれば作成します。