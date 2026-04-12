# KabuSys — README

このリポジトリは日本株自動売買システムの一部モジュール群を含むコードベースです。本 README はコードから得られる情報を元に、プロジェクト概要、機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買/リサーチ/監視を目的としたモジュール群です。主に以下の責務を持つコンポーネントで構成されています。

- 注文作成・送信・状態管理（Execution）
- 監視（Monitoring）：システム状態、注文滞留、リスクアラート、kill switch 等
- ポートフォリオ構築（Portfolio）：候補選定、重み算出、ポジションサイズ計算
- リサーチ / ファクター計算（Research）：モメンタム、ボラティリティ、バリュー等
- AI モジュール（AI）：ニュースの NLP によるセンチメント集約、レジーム判定
- ユーティリティ（utils）：プロセス優先度、設定読み込み等
- 運用ツール（tools）：Paper Trading 検証レポート生成など

設計方針として、DuckDB/SQLite をローカルに用いてデータを扱い、外部 API（kabuステーション、OpenAI 等）は抽象化して呼び出す構成になっています。自動起動・監視機能やフェイルセーフ（ログを残す、リトライ、部分書き込みでの安全性等）を重視しています。

---

## 主な機能一覧

- Execution
  - 注文作成 / 送信 / 同期 / リコンシリエーション（Reconciler）
  - Paper Trading モード（本番 DB と分離された data/paper_trading.db を使用）
  - RiskManager（発注量・利用率・サーキットブレーカー等）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度チェック
  - TradeMonitor：滞留注文、約定価格異常チェック
  - RiskMonitor：ドローダウン・ポジション上限の監視とダッシュボード更新
  - KillSwitch：フラグファイルで ExecutionEngine の停止を指示
  - AlertManager：LINE push による通知（クールダウン付き）
  - Streamlit ダッシュボード（監視データ参照）
- Portfolio
  - 候補選定、等ウェイト/スコア加重、セクターキャップ適用、ポジションサイズ算出
- Research
  - ファクター算出（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- AI
  - news_nlp：OpenAI（gpt-4o-mini）を用いたニュースごとのセンチメント算出・ai_scores への書き込み
  - regime_detector：ETF（1321）MA200 とマクロニュースの LLM センチメントを合成し日次レジーム判定
- Tools
  - paper_verification_report：Paper Trading DB から検証レポートを生成

---

## セットアップ

前提
- Python 3.10 以上（型注釈で Python 3.10 の union 型 `X | Y` を使用）
- SQLite（標準ライブラリ）
- DuckDB（pip 経由でインストール）

推奨インストール手順（プロジェクトルートで実行）:

1. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   requirements.txt が無い場合は以下の代表的な依存を手動で入れてください：
   ```bash
   pip install duckdb psutil requests streamlit openai
   ```
   - duckdb: データ処理
   - psutil: プロセス優先度・リソース計測
   - requests: LINE 通知等
   - streamlit: ダッシュボード
   - openai: AI モジュール（news_nlp / regime_detector）での呼び出し

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 重要な環境変数（一部）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
     - PAPER_FILL_MODE: paper trading の fill 動作（instant / partial / never / reject、デフォルト: instant）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH: Execution の pid ファイルパス（デフォルト: data/execution.pid）
     - KILL_FLAG_PATH: kill フラグファイルパス（デフォルト: data/kill.flag）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用 LINE 設定（未設定時は送信スキップ）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   例（.env の簡易例）:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   ```

---

## 使い方（起動・ツール）

※すべてプロジェクトルートで実行し、仮想環境を有効にしていることを前提とします。

1. 監視ループ（Monitoring）
   - 監視用ポーリングループを起動します。MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で上書きできます（デフォルト 60 秒）。
   - 監視は常に本番用の SQLite（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない点に注意）。
   ```bash
   python -m kabusys.run_monitoring
   # 例: ポーリング間隔を 30 秒に設定して起動
   MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   ```

2. 実行エンジン（ExecutionEngine）
   - 実際の発注処理を行うエンジンを起動します。Paper Trading モードのときは mock ブローカーを使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
   - 起動前に KABUSYS_ENV を設定してください（paper_trading / live / development）。
   ```bash
   # Paper Trading モード
   KABUSYS_ENV=paper_trading python -m kabusys.run_execution

   # 本番モード
   KABUSYS_ENV=live python -m kabusys.run_execution
   ```
   - 実行時はプロセス優先度を "high" に設定し、指定された pid ファイル (Settings.pid_file_path) を参照します（SystemMonitor と連携）。

3. Streamlit ダッシュボード（監視データ参照）
   - 監視 DB を読み取り専用で開いて可視化します。MonitoringEngine が生成する monitoring.db を指定して起動します。
   ```bash
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

4. Paper Trading 検証レポート
   - Paper Trading DB のデータから検証レポートを出力します。
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB を直接指定する場合
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```

5. AI モジュール
   - news_nlp.score_news(conn, target_date, api_key) や regime_detector.score_regime(conn, target_date, api_key) として Python から呼び出します。内部で OPENAI_API_KEY を参照しますが、引数で渡すことも可能です。
   - OpenAI を利用するため、適切な API キーとネットワークアクセスが必要です。

6. テスト用 / ライブラリ的利用
   - MonitoringEngine を組み合わせて単発実行したい場合は `MonitoringEngine.run_once()` を使えます（テスト目的での単回実行）。

---

## 監視・フェイルセーフの挙動（重要）

- KillSwitch: RiskMonitor からのアラート等を受け、データ/ファイル（例: data/kill.flag）を書き込むことで ExecutionEngine に停止指示を出します。kill.flag は冪等書き込み（既にある場合は書き直さない）。
- PID ファイル: Execution 起動時に PID を書き込み、SystemMonitor は PID ファイルの存在・プロセス存否をチェックして stale PID を検出・削除します。
- Monitoring は本番監視 DB を常に使う仕様（monitoring 用 DB は KABUSYS_ENV に依存しない）。
- Paper Trading は本番 DB と分離される（PAPER_TRADING_SQLITE_PATH）。

---

## 主要ファイル（概要）

- src/kabusys/config.py
  - .env ファイルのパーサー、Settings クラス（環境変数の読み取り・検証）
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（Paper Trading 時は mock ブローカー）
- src/kabusys/monitoring/
  - monitoring_db.py: SQLite テーブル定義・簡易マイグレーション・読み書きラッパー
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py
  - monitoring_engine.py: 各 Monitor を束ねる
  - streamlit_dashboard.py: ダッシュボード表示
- src/kabusys/execution/
  - order_manager.py, reconciler.py, ...（注文ライフサイクル、リコンシリエーション）
- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- src/kabusys/research/
  - factor_research.py, feature_exploration.py（ファクター・IC・統計）
- src/kabusys/ai/
  - news_nlp.py, regime_detector.py（LLM を利用したニュース評価 / レジーム判定）
- src/kabusys/tools/paper_verification_report.py
  - Paper Trading DB からの検証レポート生成

---

## ディレクトリ構成

（リポジトリルート / src 配下の抜粋構成）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py (参照されているがここにある想定)
      - execution_engine.py (参照あり)
      - broker_factory.py (参照あり)
      - broker_api.py (参照あり)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - utils/
      - __init__.py
      - process_priority.py
    - data/ (データ格納想定)
      - kabusys.duckdb
      - monitoring.db
      - paper_trading.db

---

## 開発上の注意点 / 実運用時のヒント

- DB 関連:
  - monitoring_db.init_monitoring_db() は冪等でテーブル作成と一部カラム追加（マイグレーション）を行います。
  - Paper Trading は本番 DB と分離する設計になっているため、実際に紙取引を試す際は KABUSYS_ENV=paper_trading を忘れずに。
- AI 呼び出し:
  - OpenAI を使う関数は API キーを環境変数または引数で受け取ります。API エラー発生時は多くがフェイルセーフで動作を継続するよう設計されています（既定では macro_sentiment=0.0 等にフォールバック）。
- プロセス優先度:
  - run_monitoring / run_execution は起動直後に set_process_priority("high") を呼びます。権限がない場合は警告を出してスキップします。
- ロギング:
  - 各スクリプトは logging.basicConfig(level=logging.INFO) で起動します。詳細ログを見たい場合は LOG_LEVEL 環境変数や直接コード側で設定してください。
- テスト:
  - 各モジュールは純粋関数や DB 抽象化に分かれているため、モックによる単体テストが行いやすい構造です。AI 呼び出し部は関数差し替え（patch）を想定した実装になっています。

---

## 最後に

この README はソースコードからの情報をもとに作成しています。実運用前には以下を確認してください：

- 必要な外部 API キー・認証情報が安全に設定されていること
- DB のバックアップ方針（特に本番環境）
- 運用時の監視（ログ・LINE 通知・Streamlit 等）の設定が適切であること

追加で README に記載したい内容（例: 詳細な環境変数サンプル、ユニットテストの実行方法、CI 設定等）があれば教えてください。必要に応じて追記します。