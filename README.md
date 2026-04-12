# KabuSys

日本株向け自動売買システムのコアライブラリ群（軽量プロトタイプ）。

このリポジトリは、取引エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI（ニュースセンチメント／レジーム判定）などの主要機能を含むモジュール群で構成されています。実際のブローカー接続は抽象化されており、Paper Trading（モックブローカー）と Live モードの両方を想定しています。

---

## 主な特徴

- ExecutionEngine（発注エンジン）とそれを支える OrderManager / OrderRepository / Reconciler による堅牢な発注フロー
- Monitoring サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）によるプロセス・データ鮮度・滞留注文・ドローダウン監視
- KillSwitch による外部停止フラグ（data/kill.flag）で ExecutionEngine を安全に停止
- DuckDB / SQLite を用いたデータ・ログ永続化（prices_daily, raw_financials, ai_scores など）
- portfolio モジュール：候補選定・重み算出・ポジションサイズ計算・セクター上限・レジーム乗数
- research モジュール：ファクター計算（Momentum/Value/Volatility）、特徴量解析（IC, summary）
- ai モジュール：OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングと市場レジーム判定（フェイルセーフ実装）
- スクリプト・ツール類：
  - 監視ポーリング起動スクリプト（run_monitoring）
  - Execution 起動スクリプト（run_execution）
  - Paper Trading 検証レポート生成ツール（paper_verification_report）
  - Streamlit 監視ダッシュボード（streamlit_dashboard）

---

## 動作要件（概略）

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード使用時）
- SQLite（標準ライブラリで利用）
- ネットワーク（LINE API、OpenAI を利用する場合）

パッケージのインストール例（仮）:
```bash
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数 / 設定（Settings）

Settings クラスは `.env` / `.env.local` または OS 環境変数から設定を読み込みます（プロジェクトルートは `.git` または `pyproject.toml` を探索して自動検出されます）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（省略可能なものとデフォルト）:
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG","INFO",...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant/partial/never/reject、デフォルト: instant）
- PID_FILE_PATH — PID ファイル path（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）

例（.env の一部）:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## セットアップ手順

1. リポジトリをクローン:
   ```bash
   git clone <this-repo>
   cd <this-repo>
   ```

2. Python 環境を用意（推奨: venv）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb psutil requests openai streamlit
   ```

3. 必要な環境変数を `.env` または OS 環境に設定（上記参照）。`.env` を作ると自動で読み込まれます（ただし OS 環境変数が優先）。

4. デフォルト DB パス（data/）を作成:
   ```bash
   mkdir -p data
   ```

5. 初回は各スクリプトが起動時に DB スキーマを自動作成します（monitoring のテーブルは init_monitoring_db により冪等に作られます）。

---

## 使い方（主要スクリプト／ツール）

注意: パッケージをインストールせずソース位置から実行する場合は、プロジェクトルートを PYTHONPATH に含めるか `python -m` を使います。以下はプロジェクトルート直下で実行する例。

- 監視ポーリングを起動（監視は sqlite の監視 DB に記録）:
  ```bash
  # 環境変数 MONITOR_POLL_INTERVAL で間隔秒を上書き可能（デフォルト 60）
  python -m kabusys.run_monitoring
  ```
  実行時の挙動:
  - プロセス優先度を "high" に設定しようとする（失敗しても続行）
  - Settings から sqlite_path を読み、monitoring テーブル群を init
  - DuckDB も接続
  - SystemMonitor.check_once() をポーリングで呼び続ける（MONITOR_POLL_INTERVAL 秒）

- ExecutionEngine を起動:
  ```bash
  # 本番モード（KABUSYS_ENV=live）:
  export KABUSYS_ENV=live
  python -m kabusys.run_execution

  # Paper Trading モード（DB 分離、MockBroker を使用）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  注:
  - paper_trading モードでは `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離します。
  - 起動時に Reconciler による注文/ポジションの同期・復旧が行われます。
  - PID ファイル（Settings.pid_file_path、デフォルト data/execution.pid）を利用してプロセス生存チェックを行います。

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  レポートは稼働率・注文成功率・送信率・P95 レイテンシ等を表示し、PASS/FAIL を判定します。

- Streamlit 監視ダッシュボード:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  読み取り専用で監視 DB を開いてダッシュボードを表示します。

- AI 系関数（Python API）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols から銘柄別ニュースを集約し OpenAI に問い合わせて ai_scores を更新します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 1321 の MA200 乖離とマクロニュースでレジーム（bull/neutral/bear）を算出して market_regime テーブルへ書き込みます。

  これらを利用する場合は OpenAI API キー（環境変数 OPENAI_API_KEY または引数）を設定してください。API 呼び出しは冗長な失敗対策（リトライやフェイルセーフ）があります。

---

## 重要な動作上のポイント / 注意点

- Monitoring は Settings.env に関わらず常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。Execution は KABUSYS_ENV に応じて paper_trading 用 DB を切り替えます（分離）。
- PID ファイル（デフォルト data/execution.pid）を用いたプロセス監視を行います。stale PID 検出時は PID ファイルを削除してアラート記録します。
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。KillSwitch はリスクモニタ（ドローダウン / ポジション上限）でトリガーされます。
- OpenAI を使う機能は外部 API 呼び出しを行うため、API 利用制限や課金に注意してください。失敗時はフェイルセーフとしてスコアをゼロ扱いにする等の設計になっていますが、想定外事象への対応は運用で補う必要があります。
- Paper Trading の約定挙動は Settings.paper_fill_mode で制御できます（instant/partial/never/reject）。
- .env ファイルパーサはシェル風の quoted strings、コメント処理に対応していますが、複雑な書式は避けるのが無難です。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下）

- __init__.py
- config.py
  - Settings（環境変数・.env 読み込み、各種 path / モード判定）
- run_monitoring.py
  - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading で MockBroker を使用）
- monitoring/
  - monitoring_db.py — SQLite スキーマ・永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 滞留注文・約定異常監視
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の書込み・評価
  - alert_manager.py — LINE push 通知ラッパ
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py, order_repository.py, reconciler.py, etc. — 発注フローと復旧ロジック
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - position_sizing.py — 発注株数計算・集約制約
- research/
  - factor_research.py — Momentum / Volatility / Value の計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）と ai_scores 書込み処理
  - regime_detector.py — マクロニュース + MA200 によるレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

その他、duckdb や SQLite 用のテーブル定義や DB 操作は各モジュールで実装されています。

---

## 開発・テストに関するメモ

- DuckDB 接続は通常ファイル（data/kabusys.duckdb）を使います。軽量な分析や factor 計算に適しています。
- 単体関数群（portfolio/*.py、research/*.py）は副作用が少なくユニットテストを書きやすい設計になっています（純関数志向）。
- OpenAI 呼び出し部分はテストでモック化しやすいよう、内部呼び出し関数を patch する設計です（例: kabusys.ai.news_nlp._call_openai_api の patch）。
- Settings はプロジェクトルートを .git や pyproject.toml を基に探索して `.env` を自動読み込みします。テスト時に自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

問題や追加で README に載せたい内容（例: サービスとしての起動方法 systemd ユニット、より詳しい環境変数一覧、CI 用手順など）があれば教えてください。必要に応じて README を拡張します。