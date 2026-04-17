# KabuSys

KabuSys は日本株自動売買・研究・監視を目的とした小規模なシステムです。本リポジトリは以下の機能群を提供します：

- 注文の作成・管理・実行（ExecutionEngine）
- システム稼働監視・リスク監視・アラート（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ用ファクター計算・特徴量解析（Research）
- ニュースの NLP による銘柄別センチメント付与（AI）
- 各種ユーティリティ（プロセス優先度・DB 永続化など）
- Paper Trading の検証レポート生成ツール

以下に概要、セットアップ、使い方、ディレクトリ構成をまとめます。

---

## 主要機能（抜粋）

- Execution
  - ブローカー抽象（実ブローカー / モックの切替）
  - OrderManager による注文作成・状態遷移管理
  - Reconciler による再起動時の突合（OrderSent の復旧、ポジション差分検出）
- Monitoring
  - SystemMonitor: CPU・メモリ・ディスク、工程 PID、データ鮮度の監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視、ダッシュボード更新
  - AlertManager: LINE Push による通知（クールダウン管理）
  - KillSwitch: 条件を満たせばフラグファイルを書き、ExecutionEngine を停止させる仕組み
  - Streamlit ダッシュボード（読み取り専用で監視情報を可視化）
- Portfolio
  - 候補選定（score / rank に基づく選抜）
  - 重み付け（等配分、スコア配分）
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ決定（単元株丸め、aggregate cap 対応）
- Research
  - momentum / volatility / value 等のファクター計算（DuckDB 利用）
  - 将来リターン、IC、統計サマリー、rank utilities
- AI
  - news_nlp.score_news: OpenAI を用いたニュースのセンチメント算出 → ai_scores へ書き込み
  - regime_detector.score_regime: MA200 とマクロセンチメントを合成して市場レジームを判定

---

## 前提・依存（例）

- Python 3.9+
- pip からインストールする主なパッケージ（代表）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード利用時)
  - openai (AI 機能利用時)
- SQLite（ファイルベースで同梱される）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests streamlit openai
```

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## 環境変数（主なもの）

KabuSys は環境変数 / .env ファイルを参照します。自動ロード機構があり、リポジトリルートに `.env` / `.env.local` があれば読み込まれます（テスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要な環境変数:

- KABUSYS_ENV: 起動環境（development / paper_trading / live）  
  - paper_trading の場合、MockBrokerClient を使用し Paper 用 DB に記録します（本番 DB と分離）。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB パス（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

簡易 .env 例:

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=xxxxx
LINE_USER_ID=Uxxxxxx
```

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージのインストール
   - pip install duckdb psutil requests streamlit openai

3. .env を作成して必要な環境変数を設定
   - リポジトリルートに .env を配置

4. data ディレクトリを作成（任意）
   - mkdir -p data

5. DuckDB / SQLite の初期テーブルは各起動スクリプトが必要に応じて作成するため、手動での初期化は不要（例: run_monitoring や run_execution が init_monitoring_db を実行します）。

---

## 使い方（実行例）

- ExecutionEngine を起動（本番 / デバッグ）
  - デフォルト（KABUSYS_ENV による動作差分）
  - 実行:
    ```bash
    python -m kabusys.run_execution
    ```
  - paper_trading の場合:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 停止シグナル:
    - プロセスは data/stop_requested.flag の検出でシャットダウンするようになっています（または kill.flag による停止判定も利用）。

- Monitoring（監視ループ）を起動
  - 実行:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - ポーリング間隔を上書き:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依存せず本番 DB を使います）。

- Streamlit ダッシュボード（監視可視化）
  - 実行:
    ```bash
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 読み取り専用で DB を開きます（start してモニタリングが DB を更新していることが前提）。

- Paper Trading 検証レポート生成
  - `kabusys.tools.paper_verification_report` をモジュール実行:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - デフォルト DB は data/paper_trading.db。`--db` オプションで指定可能。

- AI 機能（ニュース NLP / レジーム判定）
  - DuckDB コネクションを用意し、API キーを環境変数にセットして関数を呼ぶ:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```

---

## 停止／フラグの仕組み

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py はこのファイルの存在を検出して安全に停止します（手動終了用）。
- data/kill.flag
  - KillSwitch が条件を満たすと書き込まれ、ExecutionEngine に停止シグナルとして機能します（実行時に Settings.kill_flag_clear_on_start が有効なら起動時にクリアされます）。
- PID ファイル
  - ExecutionEngine は PID を data/execution.pid に出力し、SystemMonitor がそれを参照してプロセスの生存を確認します。

---

## ディレクトリ構成（主要ファイルのみ）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定管理
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py ...
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py, regime_detector.py
- data/ (ランタイムで生成されることが多い)
  - monitoring.db (default SQLITE_PATH)
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid / stop_requested.flag / kill.flag

（上記は主要モジュールの抜粋です。細かな実装ファイルはソース内をご確認ください。）

---

## 実装上の注意点・設計メモ

- Settings は .env ファイル自動ロードを行う（プロジェクトルートを .git / pyproject.toml で探索）。
- Monitoring の DB 初期化（init_monitoring_db）は冪等でマイグレーション処理を行います。
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。PAPER_FILL_MODE により約定挙動を調整可能。
- AI 呼び出しは OpenAI の Chat Completions（gpt-4o-mini 想定）を利用。API 呼び出しはリトライ・バリデーションが実装されています。
- プロセス優先度や CPU affinity の設定は psutil に依存し、クロスプラットフォームで失敗しても警告ログを出して継続します。
- DuckDB によるリサーチ系はテーブル（prices_daily / raw_financials / raw_news 等）を前提とします。データ投入は別途実行してください。

---

## トラブルシュート（よくある項目）

- DB が見つからない / 読み込み不可
  - Monitoring ダッシュボードは読み取り専用 URI を使用します。ファイルパスが正しいか確認してください。
- OpenAI API エラー
  - APIキーの設定とネットワークアクセスを確認。429 / 5xx は自動リトライの対象となりますが、ログを参照してください。
- Execution がすぐ停止する
  - data/stop_requested.flag や data/kill.flag の存在を確認。PID ファイルが存在するがプロセスが死んでいる場合は stale PID として削除されます。

---

必要なドキュメント（例）
- 各モジュールの設計詳細（PortfolioConstruction.md, StrategyModel.md 等）がコードコメントで参照されています。実装変更時は該当ドキュメントと整合性を保ってください。

---

以上が本リポジトリの簡易 README です。追加で「実行シナリオ別の手順」「環境ごとの推奨設定例」「テストの書き方（モック例）」など詳しいドキュメントが必要であれば教えてください。