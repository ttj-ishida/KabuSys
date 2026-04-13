# KabuSys

日本株自動売買システムの一部コードベース向け README（日本語）

このリポジトリは、ポートフォリオ構築、発注実行、監視、リサーチ（ファクター計算）やニュースNLP を含むモジュール群を提供します。実行エンジン、監視ループ、Paper Trading 用ツール、Streamlit ダッシュボードなどが含まれます。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント群（戦略／ポートフォリオ構築、発注管理、監視、リサーチ、AI ベースのニュースセンチメント）をモジュール化したコードベースです。  
主な目的は、安全な発注フロー（再起動時のリコンシリエーションなど）と運用監視の仕組みを備えたプロダクション運用を想定しています。

重要な設計方針（抜粋）
- 環境変数／.env による設定管理（自動読み込みあり、無効化可能）
- Paper Trading（仮想ブローカー）と Live（実口座）を明確に分離
- DuckDB を用いた研究用データ処理（prices_daily / raw_financials 等）
- OpenAI を利用したニュース NLP / レジーム判定（失敗時はフェイルセーフ処理）
- 監視は SQLite（monitoring.db）へログを永続化し、Streamlit で可視化可能

---

## 主な機能一覧

- Execution
  - 起動スクリプト: run_execution.py
  - Broker クライアントの抽象化（Paper Trading 時は Mock）
  - OrderManager：状態遷移／発注フロー管理（重複防止、2相永続化など）
  - Reconciler：再起動時の注文・ポジション同期

- Monitoring
  - 起動スクリプト: run_monitoring.py
  - SystemMonitor: CPU/MEM/Disk、プロセス生存、データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン／ポジション上限監視、dashboard 更新・リスクログ
  - KillSwitch: 条件で kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（monitoring DB を読み取り表示）

- Research / Portfolio
  - factor_research: Momentum / Value / Volatility ファクター計算（DuckDB）
  - feature_exploration: 将来リターン、IC、統計サマリ
  - portfolio: 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数

- AI
  - news_nlp: raw_news を OpenAI へ投げて銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: ETF (1321) の MA200 とマクロニュースを合わせて日次の market_regime を生成

- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成（DB から指標集計）

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.9+ を想定（typing の一部記法を使用）
- SQLite は標準で利用可能
- DuckDB、psutil、requests、openai、streamlit 等の外部パッケージが必要

推奨手順（例）:

1. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate    # Linux / macOS
   .venv\Scripts\activate       # Windows
   ```

2. 必要パッケージのインストール（requirements.txt が無ければ個別に）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   - 実運用では追加の依存やバージョン管理を requirements.txt / poetry 等で行ってください。

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（OS 環境変数 > .env.local > .env の優先順、自動ロード無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 主要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - KABUSYS_ENV: 起動環境（development | paper_trading | live）デフォルトは development
     - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - LOG_LEVEL: ログレベル（INFO 等）
     - PID_FILE_PATH, KILL_FLAG_PATH: 実行制御関連
   - 簡易 .env の例（プロジェクトルートに配置）:
     ```
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. データベース初期化
   - run_monitoring.py / run_execution.py は起動時に監視用テーブルを冪等に作成します（init_monitoring_db を呼ぶため特別な事前初期化は不要）。

---

## 使い方（代表的なコマンド）

- 監視ループを起動（monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。

- 実行エンジンを起動（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - Paper Trading を使う場合:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    Paper Trading モードでは MockBroker を用い、デフォルトで data/paper_trading.db を使用して本番 DB と分離します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB を明示する場合:
    ```
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```

- Streamlit ダッシュボード（監視 DB の可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と OpenAI API キーが必要です。呼び出し時に api_key 引数で渡せます（未指定時は OPENAI_API_KEY を参照）。
  - API 呼び出しはレートリミットやエラーでリトライ・フォールバック処理が実装されていますが、APIキーの管理・料金に注意してください。

---

## 設定（重要な挙動のまとめ）

- KABUSYS_ENV:
  - development（デフォルト）
  - paper_trading（MockBroker を使い Paper DB を使用）
  - live（本番）
- PAPER_FILL_MODE（paper_trading 時の約定挙動）:
  - instant / partial / never / reject（不正値は例外）
- .env 自動ロード:
  - プロジェクトルートを .git または pyproject.toml を基準に探索し `.env` / `.env.local` を読み込みます。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- プロセス優先度:
  - run_monitoring / run_execution 起動時に set_process_priority("high") を実行します（psutil を使用、権限不足時は警告でスキップ）。
- Kill Switch:
  - RiskMonitor により条件を満たすと kill.flag（KILL_FLAG_PATH）を書き込み、ExecutionEngine 停止シグナルとして機能します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数読み込み・Settings
  - run_monitoring.py                 — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py    — Paper Trading 検証レポート CLI
  - monitoring/
    - monitoring_db.py                — SQLite 監視 DB 永続化層
    - system_monitor.py               — システム & データ鮮度監視
    - trade_monitor.py                — 注文滞留・約定異常監視
    - risk_monitor.py                 — ドローダウン・ポジション監視
    - kill_switch.py                  — kill.flag 制御
    - alert_manager.py                — LINE Push 通知
    - monitoring_engine.py            — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py          — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - ... (発注関連)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/
    - pipeline.py, stats.py 等（DuckDB / prices データ処理）

（上記はコードベースで確認できる主なファイル群の抜粋です）

---

## 運用上の注意 / ヒント

- DB の分離:
  - Paper Trading と監視 DB は用途に応じて別ファイルを使う設計です。間違えて本番 DB を上書きしないよう .env を管理してください。
- フェイルセーフ:
  - AI 呼び出し失敗やデータ不足時にシステムは例外を投げずにフォールバックする箇所が多くあります（ログ出力して継続）。
- ログ:
  - ログレベルは環境変数 LOG_LEVEL で制御可能。デフォルトは INFO。
- マイグレーション:
  - init_monitoring_db は既存 DB に対してカラム追加（簡易マイグレーション）を行う仕組みがあります。

---

## 貢献 / 拡張案（簡単に）

- tests: 各純粋関数・DB 操作・モニタ系のユニットテスト追加
- requirements.txt / poetry による依存管理
- Dockerfile / systemd ユニットファイルでの運用化
- 権限周り（nice, affinity）のオプション化とエラーハンドリング改善
- ストックマスタに lot_size 等を追加して position_sizing を銘柄別対応

---

この README はコードベースの主要部分を基に作成しています。さらに実行や CI／デプロイ手順が必要なら、その目的に合わせてセクションを追記できます。必要な追加情報や具体的な実行例（systemd ユニットや Docker 化など）があれば教えてください。