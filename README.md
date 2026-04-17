# KabuSys

日本株自動売買システムの軽量実装サンプル。戦略・ポートフォリオ構築、発注エンジン、監視、研究・ファクター計算、ニュースNLP（OpenAI）連携などのコンポーネントを含みます。

---

## 概要

KabuSys は以下の責務を持つモジュール群で構成された自動売買基盤のプロトタイプです。

- Execution: 注文作成・送信、リコンシリエーション、リスク管理
- Monitoring: システム状態、注文異常、ドローダウン等の監視およびアラート送信（LINE）
- Research: DuckDB を用いたファクター計算・特徴量解析
- Portfolio: 候補選定・重み付け・ポジションサイズ算出
- AI: ニュースのセンチメント解析・市場レジーム判定（OpenAI）
- Tools: Paper Trading 検証レポート、Streamlit の監視ダッシュボード

設計方針としては、テストしやすい純粋関数群、DB 分離（paper_trading 専用 DB）、ルックアヘッドバイアスの排除などが盛り込まれています。

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / paper_trading 切替（KABUSYS_ENV）
  - Broker クライアント抽象化（Mock を含む）
  - 起動時リコンシリエーション（Reconciler）
  - PID ファイル・停止フラグによる制御

- Monitoring（run_monitoring.py, MonitoringEngine）
  - CPU/MEM/DISK、Execution プロセス死活、データ鮮度監視
  - 注文滞留・約定異常検出
  - ドローダウン／ポジション上限監視と KillSwitch（kill.flag）発動
  - LINE へのアラート送信（AlertManager）
  - Streamlit ダッシュボード（streamlit_dashboard.py）

- Research
  - Momentum / Volatility / Value 等のファクター算出（DuckDB）
  - フォワードリターン、IC 計算、統計サマリ

- AI
  - ニュースを OpenAI（gpt-4o-mini）で解析して ai_scores へ格納
  - 市場レジーム判定（ma200 + マクロセンチメントの組合せ）

- Portfolio
  - 候補選定、等ウェイト／スコアウェイト、リスクベースのポジション計算
  - セクター上限適用、レジーム乗数

- Tools
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）
  - Streamlit ベース監視ダッシュボード

---

## 要求環境

- Python 3.10 以上（| 型注釈等の構文を使用）
- SQLite（組み込み）
- 推奨パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit

インストール例:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install duckdb psutil requests openai streamlit
```

（プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール（上記参照）

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（既存の OS 環境変数は保護）。
   - 必須の環境変数（実行に必要なもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使用する機能を使う場合:
     - OPENAI_API_KEY
   - 監視やアラートで LINE を使う場合:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - 便利な設定:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL（監視のポーリング間隔秒、デフォルト: 60）

   例 (.env):
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

5. （任意）既定の SQLite / DuckDB ファイルは起動時に必要なテーブルを自動作成します（init_monitoring_db 等）。

---

## 使い方

- ExecutionEngine を起動（通常実行）
  ```
  # デフォルトで KABUSYS_ENV=development
  python -m kabusys.run_execution
  ```
  - paper_trading モードで起動する場合:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    - paper_trading では MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。

- Monitoring を起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定できます（例: 30 秒）。
    ```
    export MONITOR_POLL_INTERVAL=30
    ```

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 停止 / キル
  - Monitoring / Execution はフラグファイルや PID ファイルで相互に制御します。
    - run_execution/run_monitoring が使用する停止フラグ: data/stop_requested.flag（監視プロセス自身がこのファイルの存在を見て終了します）
    - KillSwitch（監視側）が発動すると data/kill.flag を書き込み、ExecutionEngine に停止シグナルとなります（Settings.kill_flag_path）。
  - 手動で停止ファイルを置く例:
    ```
    touch data/stop_requested.flag      # run_monitoring のポーリングループ停止
    echo "reason" > data/kill.flag      # ExecutionEngine に停止を促す（KIllSwitch と同等）
    ```

---

## 簡単な運用フロー例

1. 監視を常時起動
   - run_monitoring をデーモンとして実行（systemd 等で管理推奨）
   - MONITOR_POLL_INTERVAL を適宜設定

2. ExecutionEngine を起動
   - run_execution を起動（本番では KABUSYS_ENV=live、paper 環境は分離された DB を使用）

3. 異常検知時
   - Monitoring → KillSwitch が条件を満たすと data/kill.flag を生成 → ExecutionEngine は停止する
   - AlertManager が LINE に通知（設定済みの場合）

4. 再起動時
   - ExecutionEngine は起動時に Reconciler を走らせ、OrderSent 等の状態を復元・突合する

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - execution/
    - execution_engine.py         — 実際のエンジン（起動・セッション管理）
    - broker_factory.py           — Broker クライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - order_record.py
    - ...（発注関連）
  - monitoring/
    - monitoring_db.py            — SQLite スキーマ / 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                  — ニュース NLU / OpenAI 連携
    - regime_detector.py
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - data/                          — 実行時に使用される DB・フラグファイル等（推奨作成）

（上記は主要ファイルのみ抜粋。詳細は src/kabusys 配下の各モジュールを参照してください）

---

## 重要な注意点 / ヒント

- KABUSYS_ENV により挙動が変わります。paper_trading は本番 DB と完全に分離された DB を使用するため、テストに便利です。
- OpenAI API を使う機能は API キーの設定が必須です。使用時はコストとレイテンシに注意してください。
- Monitoring は本番 sqlite_path を利用してログを記録します（run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用します）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- プロセス優先度設定や CPU affinity の変更は権限に依存します。設定に失敗した場合は警告が出て処理は継続します。

---

## 開発者向け

- 単体関数群（portfolio、research 等）は外部副作用が少なくテストしやすい設計です。ユニットテストを作成しやすい領域が多くあります。
- DB スキーマ変更は monitoring_db.init_monitoring_db 内のマイグレーションロジックを参照してください（既存カラムの有無をチェックして ALTER TABLE を実行する設計）。

---

問題・拡張提案・ドキュメントの追記希望があれば教えてください。README に追記・修正して対応します。