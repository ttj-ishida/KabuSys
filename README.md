# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリには以下の主要機能（注文管理、リコンシリエーション、監視、ポートフォリオ構築、リサーチ、AI ベースのニュースセンチメント等）が含まれます。

- パイプライン設計は DuckDB / SQLite を利用し、取引部分と監視ログは分離
- Paper Trading（検証）用に本番 DB と完全分離された動作モードをサポート
- 監視エンジンによるプロセス監視・注文監視・リスク監視・Kill Switch、LINE 通知
- AI（OpenAI）を用いたニュースセンチメント / レジーム判定モジュール
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 検証・運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

以下は開発者向け README（日本語）です。

---

## 機能一覧（抜粋）

- execution
  - ExecutionEngine / OrderManager / Reconciler：起動時リコンシリエーション、注文状態管理
  - BrokerClientFactory により本番 or Mock ブローカーを選択（KABUSYS_ENV に依存）
- monitoring
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス PID の監視
  - TradeMonitor：滞留注文・約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード永続化
  - KillSwitch：フラグファイルによる ExecutionEngine 停止トリガー
  - AlertManager：LINE Push による通知（クールダウン付き）
  - MonitoringEngine：各 Monitor を束ねたポーリングループ
  - streamlit_dashboard：監視データの可視化（Streamlit）
- research
  - factor_research, feature_exploration：DuckDB 上のファクター計算、IC／統計解析
- ai
  - news_nlp：OpenAI によるニュースセンチメント（ai_scores へ書き込み）
  - regime_detector：MA200 とマクロニュースを合成した市場レジーム判定
- tools
  - paper_verification_report：Paper Trading DB から検証レポートを生成

---

## 要求環境

推奨 Python バージョン: 3.9+

主な依存ライブラリ（抜粋）
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボードを使う場合）
- sqlite3（標準ライブラリ）
- その他（pip install で解決してください）

例:
```
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

設定は .env / .env.local / OS 環境変数の順で読み込まれます（但し KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須（使用する機能に依存）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必要に応じて）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（ブローカー接続に必須）

任意 / デフォルトあり:
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
  - paper_trading の場合、MockBroker を使い DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に分離
- OPENAI_API_KEY — OpenAI を利用する AI 機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視ログ SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine が書き込む PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

簡単な .env 例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

---

## セットアップ手順

1. リポジトリをクローン
```
git clone <repo-url>
cd <repo-root>
```

2. 仮想環境を作成・有効化（推奨）
```
python -m venv .venv
# Unix/macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

3. 必要パッケージをインストール
```
pip install -r requirements.txt
# requirements.txt がない場合は
pip install duckdb psutil requests openai streamlit
```

4. data ディレクトリを作成（プロセスが書き込むファイル用）
```
mkdir -p data
```

5. .env を作成して環境変数を設定（上記参照）
※ 自動ロードは config モジュールがプロジェクトルート（.git または pyproject.toml）を基に行います。

---

## 使い方

### 監視ループの起動（Monitoring）
監視は常駐プロセスとして system のリソースや注文状況を定期的に記録します。

```
python -m kabusys.run_monitoring
```

- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（例: export MONITOR_POLL_INTERVAL=30）
- 監視は Settings.sqlite_path（デフォルト data/monitoring.db）にログを書き込みます
- 停止するにはプロジェクトルート下の data/stop_requested.flag を作成することでループを終了できます

### 実行エンジン（ExecutionEngine）の起動
実際の注文実行エンジンを起動します。

```
python -m kabusys.run_execution
```

- KABUSYS_ENV=paper_trading の場合、MockBroker が使用され paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます（本番 DB と完全分離）
- Engine は pid ファイル（デフォルト data/execution.pid）を書き込みます
- 停止は data/stop_requested.flag を作成することでエンジンに通知され安全に停止します
- Kill Switch（data/kill.flag）が書かれると ExecutionEngine の停止をトリガーできます（KillSwitch は監視側で評価してフラグを書きます）

### Paper Trading 検証レポート出力
Paper Trading DB（デフォルト data/paper_trading.db）からレポートを生成します。

```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または明示的に DB 指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

出力内容: 稼働率、注文成功率、送信率、レイテンシ指標、PASS/FAIL 判定（閾値はコード中で定義）

### Streamlit ダッシュボード（監視ビュー）
監視 DB を読み込み、ブラウザでダッシュボードを表示します。

```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- DB は読み取り専用でオープン（存在しない場合はエラー表示）

### AI 機能（ニュース NLP / レジーム判定）
OpenAI API を利用するため OPENAI_API_KEY が必要です。関数として次のように使えます（コード内 API）：

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- API 呼び出しはリトライ・フェイルセーフを備えていますが、API キー未設定時は ValueError を投げます
- OpenAI 呼び出しにはモデル gpt-4o-mini 等を使用（設定はコード内定義）

---

## 停止 / フラグ操作

- モニタ／実行を強制的に停止するにはプロジェクトルートの data/stop_requested.flag を作成します（run_monitoring/run_execution が検出して終了）
- Execution 停止トリガー（Kill Switch）として data/kill.flag が使用されます。KillSwitch.clear() で削除（手動ではファイル削除を実行）
- PID ファイル: data/execution.pid（プロセス監視・stale PID 検出で使用）

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュール構成（src/kabusys）の抜粋：

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env の読み込み・Settings
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポートツール
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py      — レジーム判定（MA200 + macro）
  - data/ (想定)
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - execution.pid, stop_requested.flag, kill.flag
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 / 永続化 API
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py        — 注文滞留 / 約定異常監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — フラグファイルによる停止トリガー
    - alert_manager.py        — LINE 通知
    - monitoring_engine.py    — 各監視を束ねるエンジン
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - execution_engine.py
    - broker_factory.py
    - ...
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルのみ。詳細は src/kabusys 以下を参照してください）

---

## 注意事項 / 運用メモ

- Paper Trading（KABUSYS_ENV=paper_trading）では本番 API にアクセスせず、MockBroker を用いて data/paper_trading.db に記録されます。検証やCI向けに便利です。
- Settings は起動時に .env/.env.local を自動で読み込みますが、CI やテストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process priority / CPU affinity の設定はプラットフォーム依存です。許可がない場合は警告を出してスキップします。
- OpenAI を用いる機能は外部 API 呼び出しの課金が発生するため、テスト時にはモック化推奨（コード内で _call_openai_api を patch 可能）。

---

## 問い合わせ / 変更履歴

- バージョン: 0.1.0（src/kabusys/__init__.py）
- 仕様や設計に関するドキュメント（PortfolioConstruction.md, StrategyModel.md 等）が参照されています。詳細は該当ドキュメントを参照してください。

---

README は以上です。必要であれば、インストール用 requirements.txt、デプロイスクリプト、あるいは運用チェックリスト（起動順、監視・ログ確認手順）を別途追加します。どの部分を詳細化しますか？