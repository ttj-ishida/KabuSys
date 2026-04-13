# KabuSys

日本株向け自動売買システムの実装（ライブラリ＋起動スクリプト群）。

このリポジトリは、シグナル生成・銘柄選定・ポジションサイズ計算・注文管理（ExecutionEngine）・監視（MonitoringEngine）・AI を使ったニュースセンチメント/レジーム判定などのコンポーネントを含みます。コードは純粋関数群と永続化レイヤ（SQLite / DuckDB）で分離されており、Paper Trading 用のモックや監視ダッシュボードも備えています。

---

## 主な特徴（機能一覧）

- Execution
  - 注文作成・送信・状態同期（OrderManager, Reconciler）
  - リコンシリエーション（再起動時の自動復旧）
  - リスク管理（RiskManager）と発注前チェック
  - Paper Trading モード（モックブローカー、別 DB に記録）
- Portfolio Construction
  - 候補選定、等金額/スコア重み、リスクベースのポジションサイズ算出
  - セクター集中制限、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、ファクター統計
- AI
  - ニュースを OpenAI（gpt-4o-mini）でセンチメント化して ai_scores に書き込み（batch、リトライ、バリデーション付き）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（bull/neutral/bear）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期監視
  - 監視ログの永続化（SQLite）
  - KillSwitch（kill.flag）で ExecutionEngine に停止シグナルを送出
  - LINE によるアラート通知（AlertManager）
  - Streamlit ダッシュボード（監視情報の可視化）
- ツール
  - Paper Trading の検証レポート生成スクリプト（成功率・レイテンシ・稼働率など）

---

## 要件

主に以下のライブラリを使用しています（バージョンは適宜選択してください）。

- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- （SQLite は標準ライブラリ）

requirements.txt がない場合は手動でインストールしてください。例:

pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは上記の個別インストール

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（OS 環境変数が優先）。
   - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

---

## 主要な環境変数

Settings クラス（kabusys.config）で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（省略可）
- LINE_USER_ID — LINE 通知先ユーザー ID（省略可）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視ログ（production）SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする場合は "1"
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- Monitoring（監視）は KABUSYS_ENV にかかわらず常に production の sqlite_path（SQLITE_PATH）を使います。
- Paper Trading モード（KABUSYS_ENV=paper_trading）は専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番データと完全に分離します。

---

## 実行方法（使い方）

以下は主要な起動コマンド例です。プロジェクトルートから実行してください。

1. ExecutionEngine を起動（通常運用）
   - python -m kabusys.run_execution
   - 起動時にプロセス優先度を "high" に設定します。
   - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH に記録します。

2. Monitoring（ポーリング）を起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
   - 監視は指定の SQLite（SQLITE_PATH）と DuckDB を使用します。監視は system/trade/risk のチェックを周期的に行い、必要に応じて kill.flag を書きます。

3. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System を表示します。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションで別 DB パスを指定可能（優先度: --db > PAPER_TRADING_SQLITE_PATH > デフォルト）

5. AI 処理（ニューススコア付け / レジーム判定）
   - Python から関数を呼び出す（DuckDB 接続を渡す必要あり）。例:

     from datetime import date
     import duckdb
     from kabusys.ai import score_news
     conn = duckdb.connect('data/kabusys.duckdb')
     score_news(conn, date(2026, 4, 1), api_key='YOUR_OPENAI_KEY')

   - 同様に regime 判定関数は kabusys.ai.regime_detector.score_regime を使用できます。

6. その他ユーティリティ
   - 設定は kabusys.config.Settings を通じてアクセスできます。
   - プロセス優先度や CPU affinity は kabusys.utils.process_priority を参照。

---

## 実行上の重要な挙動・注意点

- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（権限により失敗する場合は警告）。
- Monitoring の DB 初期化（テーブル作成・簡易マイグレーション）は init_monitoring_db で行われます。起動は冪等です。
- KillSwitch:
  - 一度 kill.flag が書かれると ExecutionEngine 側でフラグを検出し終了します。
  - KillSwitch は drawdown やポジション上限などのリスク条件を検査してフラグを書きます。
- Paper Trading:
  - KABUSYS_ENV=paper_trading にすると mock ブローカーを利用し、本番 DB と分離して data/paper_trading.db に記録します。
- OpenAI API とのやり取りはリトライ・エラーハンドリングが組み込まれており、部分失敗でも他コードへの書き込みを保護する（部分的な DELETE → INSERT の戦略）設計です。

---

## ディレクトリ構成

リポジトリの主要ファイル/ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                         — 環境変数 / 設定読み込みロジック
    - run_execution.py                  — ExecutionEngine 起動スクリプト
    - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py    — Paper Trading 検証レポート生成スクリプト
    - ai/
      - __init__.py
      - news_nlp.py                     — ニュース NLP / OpenAI バッチ処理
      - regime_detector.py              — マクロ + MA200 によるレジーム判定
    - research/
      - __init__.py
      - factor_research.py              — Momentum / Volatility / Value 計算
      - feature_exploration.py          — 将来リターン / IC / 統計
    - portfolio/
      - __init__.py
      - portfolio_builder.py            — 候補選定・重み計算
      - position_sizing.py              — 株数計算・キャップ適用
      - risk_adjustment.py              — セクター制限・レジーム乗数
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py
      - order_record.py
      - broker_factory.py
      - execution_engine.py
      - ... (その他発注関連)
    - monitoring/
      - __init__.py
      - monitoring_db.py                — SQLite 永続化層（テーブル定義 + 操作）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
      - streamlit_dashboard.py
    - utils/
      - __init__.py
      - process_priority.py             — プロセス優先度 / affinity ユーティリティ
    - data/                              — （実行時に使う DB / PID / フラグ 等を置く想定）
      - kabusys.duckdb
      - monitoring.db
      - paper_trading.db
      - execution.pid
      - kill.flag

---

## 開発・デバッグのヒント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。CWD に依存しないため、パッケージ配布後も動作します。
- duckdb はメモリ内集計やファクター計算に使われます。prices_daily / raw_financials / raw_news 等のテーブルが必要です。
- Monitoring のテーブル定義・マイグレーションは init_monitoring_db() が担当します。既存 DB に対して列追加（例: latency_ms や peak_value）の処理が含まれます。
- AI 周りの関数は外部 API の失敗に対してフェイルセーフ（スコア=0.0 やスキップ）で動作するように設計されていますが、API キーは必須です。
- unit テストやモックを使う場合、OpenAI 呼び出しや外部 API 呼び出しはモック化してテストしてください（コード内で _call_openai_api などを patch する想定）。

---

この README はコードベースの主要な使い方と設計上の要点をまとめたものです。細かい挙動や API の仕様は各モジュール（kabusys/*）の docstring を参照してください。必要ならば追加のチュートリアルや設定例（.env.example、docker-compose、systemd サービス定義等）を作成します。