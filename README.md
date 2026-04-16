# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト群のリポジトリ。  
この README はコードベース（src/kabusys 以下）を参照して作成しています。

## プロジェクト概要
KabuSys は日本株の自動売買に必要な次の主要コンポーネントを含みます。

- 注文作成・管理・再同期（ExecutionEngine 周り）
- 監視（プロセス、システム、注文滞留、リスク監視）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出）
- リサーチ（ファクター計算、特徴量探索）
- AI 補助（ニュース NLP によるセンチメント、レジーム検出）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針の特徴：
- DuckDB / SQLite を用いたローカル DB ベースの解析・監視
- paper_trading（検証）環境と live（本番）環境の分離
- OpenAI を使ったニュース解析（外部 API キーは環境変数で管理）
- 可搬性を考慮した .env 自動読み込み（プロジェクトルートに基づく）

---

## 主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカークライアントの抽象化（paper_trading では Mock を使用）
  - 再起動後のリコンシリエーション（Reconciler）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度）
  - TradeMonitor（滞留注文、約定価格異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件を満たせば data/kill.flag を書き込み ExecutionEngine 停止）
  - AlertManager（LINE Push でアラート通知）
  - MonitoringEngine（複数モニターを束ねるポーリング機構）
  - Streamlit ダッシュボード（監視データ可視化）
- Portfolio
  - 候補選定、等金額/スコア加重配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ算出（ロット丸め、利用可能現金による調整）
- Research
  - Momentum/Volatility/Value ファクター計算（DuckDB 上の prices_daily/raw_financials）
  - 将来リターン・IC 計算・統計サマリ
- AI
  - ニュースを LLM（gpt-4o-mini 想定）で解析して銘柄別スコアを ai_scores に格納
  - マクロニュースと MA200 を組み合わせた市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）

---

## 動作要件（推奨）
- Python >= 3.10
- 必須パッケージ（主なもの）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- SQLite（Python 標準ライブラリに同梱）

（実際のプロジェクトでは requirements.txt を用意して pip install -r で管理してください）

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

4. 環境変数設定
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）が検出されれば `.env` と `.env.local` を自動でロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 例 `.env` に最低限設定する値（実運用では secrets を安全に管理してください）:
     ```
     KABUSYS_ENV=development          # development | paper_trading | live
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     ```
   - PAPER_FILL_MODE の有効値: instant | partial | never | reject（デフォルト: instant）

5. データディレクトリを作る
   - mkdir -p data

---

## 使い方（主な実行方法）

- 実行エンジン（ExecutionEngine）を起動
  - デフォルト（KABUSYS_ENV が production/live などの場合は実際のブローカーを使います）
    ```
    python -m kabusys.run_execution
    ```
  - Paper Trading（Mock ブローカー、専用 DB を使用）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - run_execution は起動時に data/execution.pid を作成し、data/stop_requested.flag の存在で停止します。停止命令は kill flag（data/kill.flag）を用いるか stop_requested.flag を作ることで制御できます。

- 監視ループ（Monitoring）を起動
  - デフォルトは sqlite の monitoring DB（data/monitoring.db）を使い、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に Settings.env にかかわらず本番 sqlite_path を使用して監視ログを永続化します。

- Streamlit ダッシュボード（監視 UI）
  - 起動:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - ローカルの監視 DB を読み取り専用で開き、ポートフォリオ・ポジション・直近の注文・システム状態を表示します。

- Paper Trading 検証レポート（ツール）
  - 使い方:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - または DB を明示する:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- AI モジュール利用例（ライブラリ関数として）
  - ニュース NLP（銘柄別スコアを ai_scores に書き込む）:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

---

## 運用上のファイル／フラグ
- data/stop_requested.flag
  - run_monitoring / run_execution のポーリングループを静かに終了させるためにチェックされるフラグファイル。
- data/kill.flag
  - KillSwitch が評価条件（ドローダウン超過 等）を満たした場合に書き込まれるファイル。ExecutionEngine に停止を促すために使用。
- data/execution.pid
  - ExecutionEngine の PID を記録するファイル。SystemMonitor はこの PID を監視してプロセスの生存を判定します。
- DB ファイル（デフォルト）
  - data/monitoring.db — 監視ログ（MonitoringDB）
  - data/paper_trading.db — Paper Trading 用 SQLite（paper_trading 環境時）
  - data/kabusys.duckdb — 価格・財務データ等の分析用 DuckDB

注意: kill.flag を手動でクリアするにはファイルを削除してください（KillSwitch.clear() があるためプログラムからも可能）。

---

## 主要環境変数（Settings で参照されるもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）の設定
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の成行／部分約定等のモード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

---

## 開発者向けメモ（実装で注目すべき点）
- Settings モジュールは .env/.env.local を自動ロードする（プロジェクトルートを検出）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- MonitoringDB.init_monitoring_db は既存 DB のスキーママイグレーションを幾つか行う（追加カラム等）。
- Execution と Monitoring は process priority を "high" に設定しようとします（psutil に依存）。
- AI 呼び出しはリトライロジック・レスポンスバリデーション等を実装しており、部分失敗時の DB 書き込み保護も考慮されています。
- Research / Factor modules は DuckDB 接続を受け取り、価格テーブル（prices_daily）や raw_financials を参照して純関数的に結果を返します。

---

## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- ai/
  - news_nlp.py                  — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py           — 市場レジーム判定
- monitoring/
  - monitoring_db.py             — SQLite 監視 DB 層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - reconciler.py
  - order_manager.py
  - ... (broker_factory や execution_engine 等、実装の一部は省略)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py

（上記は本 README を作成した時点で確認できる主要ファイルの抜粋です）

---

## よくある運用手順（例）
1. 開発環境で DuckDB に価格データ・raw_news を投入
2. KABUSYS_ENV=paper_trading で run_execution を起動して戦略検証
3. run_monitoring を別プロセスで起動してシステム状態を記録
4. Streamlit で監視 UI を開いて運用状況を確認
5. Paper Trading 検証レポートを定期的に出力して品質判定

---

## トラブルシューティング
- .env が読み込まれない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルート（.git や pyproject.toml）が適切に存在するか確認
- OpenAI API 呼び出し失敗:
  - OPENAI_API_KEY の設定を確認
  - ネットワーク / レート制限によりリトライされるためログを確認
- PID / stop flag 関連:
  - data/execution.pid が残っていると SystemMonitor はプロセス生存を検出します。古い stale PID は SystemMonitor によって削除される場合があります。

---

必要であれば、README に含めるコマンド例や .env.example の雛形を具体的に追記します。どの部分を詳しく書き加えますか？