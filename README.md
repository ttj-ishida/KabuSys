KabuSys — 日本株自動売買システム（README）
=======================================

概要
---
KabuSys は日本株の自動売買・モニタリング・リサーチ用ユーティリティ群を含む小規模なシステムです。本リポジトリは次の責務を持ちます。

- 注文発行とリスク管理（ExecutionEngine / OrderManager / Reconciler）
- 監視・アラート（SystemMonitor / TradeMonitor / RiskMonitor / AlertManager）
- ポートフォリオ構築（候補選定・重み計算・ロット丸めなど）
- リサーチ（ファクタ計算・将来リターン・IC 等）
- ニュースの NLP によるセンチメント評価（OpenAI を利用）
- Paper Trading 用の検証・レポート生成ツール

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 DB に完全分離して記録
  - ブローカークライアント生成、OrderManager・RiskManager 等の組み立て、実行セッションの開始
- Monitoring（run_monitoring.py / MonitoringEngine）
  - CPU/メモリ/ディスク使用率・データ鮮度・プロセス存在チェック
  - 注文滞留、約定価格異常、ドローダウン・ポジション上限の監視
  - kill.flag 書き込みによる ExecutionEngine 停止シグナル
  - LINE によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Portfolio utilities
  - 候補選定（select_candidates）、等分/スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- Research utilities
  - モメンタム / ボラティリティ / バリューファクタ計算（DuckDB 上の prices_daily/raw_financials を参照）
  - 将来リターン / IC 計算 / 統計サマリ
- AI（ニュースNLP / レジーム判定）
  - OpenAI（gpt-4o-mini）でニュースのセンチメント評価を行い、ai_scores に格納
  - market_regime 判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

動作要件（主な依存ライブラリ）
----------------------------
- Python 3.10+
- duckdb
- psutil
- requests
- openai (OpenAI Python SDK)
- streamlit（ダッシュボード利用時）
- sqlite3（標準ライブラリ）

インストール例
--------------
Python 仮想環境を作成して依存を入れてください（以下は例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

設定（環境変数）
----------------
設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数とデフォルト値・備考:

- KABUSYS_ENV: 起動モード。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J‑Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知設定（未設定時は通知を送らない）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の模擬約定挙動（instant | partial | never | reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill switch 用フラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合必須）

セットアップ手順
----------------
1. リポジトリをクローンし、Python 仮想環境を用意して依存をインストール。
2. 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を .env に設定するか、OS 環境変数で用意。
3. DuckDB / SQLite のデータファイルは初回起動時に必要なテーブル作成処理が自動実行されます（monitoring の init_monitoring_db 等）。ただし prices_daily / raw_financials 等のデータ投入は別途用意してください。
4. Paper Trading を使う場合: KABUSYS_ENV=paper_trading を設定し、PAPER_TRADING_SQLITE_PATH が参照されます（本番 DB と分離）。

使い方（起動・コマンド例）
-------------------------

- 監視ループを起動（Monitoring）
  - デフォルトで本番 sqlite_path を使用（モニタは常に本番監視 DB を利用）
  - ポーリング間隔を変更するには MONITOR_POLL_INTERVAL を設定
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    # または
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- ExecutionEngine を起動（注文実行）
  - paper_trading モードでは MockBrokerClient を使い、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB とは分離
  - 実行:
    ```bash
    python -m kabusys.run_execution
    # Paper trading の場合
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

- Streamlit ダッシュボード（監視 UI）
  - 実行:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 指定 DB は読み取り専用で開かれます（起動に監視エンジンが必要）。

- Paper Trading 検証レポート生成
  - 実行:
    ```bash
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- AI（ニューススコアリング / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を設定し、DuckDB 接続オブジェクトを作成して下記関数を呼び出します。
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB の raw_news / news_symbols / ai_scores / prices_daily 等のテーブルを参照します。

監視・アラート設計メモ
---------------------
- Monitoring は MonitoringDB（SQLite）へログを永続化します。init_monitoring_db() により必要なテーブルは冪等的に作られます。
- SystemMonitor は ExecutionEngine の PID ファイルを監視し、プロセスが存在しない stale PID を検出するとフラグファイルを書きます。
- KillSwitch は RiskMonitor 等の結果に基づき data/kill.flag を書き、ExecutionEngine に停止シグナルを伝えます（ExecutionEngine 側で kill.flag の存在を監視する設計）。

注意点 / 実装上の注記
--------------------
- .env 読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して行います。CWD に依存しない設計です。
- Paper Trading は本番 DB とデータを完全分離する設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 呼び出し処理は API エラー時にリトライやフェイルセーフ（ゼロスコアやスキップ）で安全側に振る舞います。
- process priority（優先度）と CPU affinity 設定は psutil を使いプラットフォーム差分を吸収します。権限不足や未対応 OS の場合は警告を出してスキップします。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定読み込み
  - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 監視 DB 永続化層（init / CRUD）
    - system_monitor.py             — CPU/メモリ/ディスク/データ鮮度 / PID チェック
    - trade_monitor.py              — 注文滞留 / 約定異常の検出
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag 書き込みユーティリティ
    - alert_manager.py              — LINE push 通知
    - monitoring_engine.py          — 各 monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py        — Streamlit ベースの監視ダッシュボード
  - execution/
    - reconciler.py                 — 起動時のリコンシリエーション
    - order_manager.py              — 発注処理の外向け API / 状態遷移
    - order_repository.py           — （DB 操作：未掲示だが存在想定）
    - order_record.py               — 注文状態モデル（未掲示だが存在想定）
    - broker_factory.py / broker_api.py — ブローカークライアント生成・API
    - execution_engine.py           — 実行エンジン本体（未掲示だが参照あり）
  - portfolio/
    - portfolio_builder.py          — 候補選定 / 等重・スコア重み
    - position_sizing.py            — 発注株数計算・集約キャップ
    - risk_adjustment.py            — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py            — ファクター計算（momentum / volatility / value）
    - feature_exploration.py        — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py                   — ニュース記事の LLM スコアリング
    - regime_detector.py            — マクロ + MA200 合成による市場レジーム判定
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading レポート生成ツール

補足 / 開発者向けメモ
--------------------
- DuckDB のテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等）は外部で ETL して用意する想定です。
- Execution 周り（broker client 実装や execution_engine の詳細）は本 README の範囲外ですが、Reconciler や OrderManager の実装方針はコードコメントに記載されています。
- 単体テストや CI の雛形は含まれていません。ユニットテスト作成時は config の自動 .env ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD）を利用してください。

問い合わせ / 貢献
-----------------
- バグ修正・機能追加は Pull Request を歓迎します。プルリク前に issue を立てて方針を相談してください。

以上。必要であれば README に含めるサンプル .env や起動スクリプトの詳細なオプション、さらに ExecutionEngine の具体的な実行フロー図などを追加します。どの情報を優先して拡充しますか？