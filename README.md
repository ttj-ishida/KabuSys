# KabuSys

日本株向け自動売買システムのサブコンポーネント群（監視 / 実行 / ポートフォリオ構築 / 研究 / AI ニューススコアリング 等）。

このリポジトリは、ExecutionEngine の実行・監視、Paper Trading の検証、ファクター計算、ニュース NLP による銘柄別センチメントスコア生成などの機能を含みます。

---

## プロジェクト概要

主な目的は日本株の自動売買を安全に運用するためのコンポーネント提供です。構成要素の一部は以下です。

- ExecutionEngine 起動スクリプト（run_execution.py）：ブローカー連携・リスク管理・発注管理を行う
- Monitoring（run_monitoring.py, MonitoringEngine 等）：システム状態・注文監視・リスク監視、LINE による通知、kill.flag による停止シグナル
- Streamlit ダッシュボード（監視データ可視化）
- Paper Trading 検証レポート生成ツール
- portfolio モジュール：候補選択・重み計算・ポジションサイズ計算・セクター制限
- research モジュール：ファクター計算・IC / 将来リターン・統計要約
- ai モジュール：ニュースを LLM（OpenAI）でスコアリング、レジーム判定

---

## 主な機能一覧

- 環境別設定管理（Settings。.env/.env.local 自動読み込み）
- SQLite（監視ログ）と DuckDB（時系列価格等分析）を併用
- ExecutionEngine：ブローカー抽象化、OrderManager、RiskManager、Reconciler（再起動時の同期）
- MonitoringEngine：SystemMonitor / TradeMonitor / RiskMonitor のポーリング、KillSwitch、AlertManager（LINE通知）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 用 DB 分離（KABUSYS_ENV=paper_trading）
- OpenAI を使ったニュースセンチメントスコア（batch 処理・リトライ・検証ロジック）
- ファクター計算（momentum / volatility / value）と研究用ユーティリティ（IC、ランキング、統計サマリー）
- ポートフォリオ構築の純粋関数群（候補選定、重み、サイズ決定、セクターキャップ、レジーム乗数）

---

## 動作要件（推奨）

- Python 3.10+
- 必要パッケージ（代表的なもの）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit

例:
```bash
python -m pip install duckdb psutil openai requests streamlit
```
プロジェクトに requirements.txt があればそちらを使ってください。

---

## セットアップ手順

1. ソースをクローン／配置する。
2. Python 仮想環境を作る（推奨）。
3. 必要パッケージをインストール（上記参照）。
4. 環境変数を設定する:
   - .env / .env.local をプロジェクトルートに置けば自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すると自動読み込みを無効化）。
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API 用） — Settings.jquants_refresh_token が未設定だとエラー
     - KABU_API_PASSWORD: 必須（kabuステーション API）
     - OPENAI_API_KEY: AI 機能を使う場合に必要
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading のモック約定動作（instant | partial | never | reject）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は送信をスキップ）
     - PID_FILE_PATH / KILL_FLAG_PATH: 起動時に使用するパス（デフォルト: data/execution.pid / data/kill.flag）
     - LOG_LEVEL: DEBUG|INFO|...（Settings.log_level）

5. data ディレクトリ等の書き込み権限を確認。SQLite / DuckDB ファイルはデフォルトで `data/` 配下を参照します。

---

## 使い方

以下は主要な起動方法と利用例です。プロジェクトルートで実行することを想定しています。

### 監視ループを起動（Monitoring）
MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。

例（本番モード）:
```bash
export KABUSYS_ENV=live
export MONITOR_POLL_INTERVAL=60
python -m kabusys.run_monitoring
# または
python src/kabusys/run_monitoring.py
```

- 起動時にプロセス優先度を high に設定しようとします（権限不足等で失敗しても継続）。
- monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用します。

### 実行エンジンを起動（Execution）
Paper Trading（モックブローカー）と本番で DB を分離します（KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用）。

例（Paper Trading）:
```bash
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
# または
python src/kabusys/run_execution.py
```

例（本番）:
```bash
export KABUSYS_ENV=live
python -m kabusys.run_execution
```

- ブローカークライアントは BrokerClientFactory により生成され、paper_trading では MockBrokerClient が使われます。
- Execution 起動時もプロセス優先度を high に設定します。

### Streamlit ダッシュボード（監視可視化）
コメントにもある通り、read-only モードで DB を開いて表示します。

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

### Paper Trading 検証レポート生成ツール
対象期間の検証レポートを標準出力に出します。

```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
```

レポートは稼働率、注文成功率、送信率、P95 レイテンシ等を出力し、基準値を満たすか PASS/FAIL 判定を行います。

### AI ニューススコアリング（プログラム呼び出し）
DuckDB 接続を渡して programmatic に呼び出します（OPENAI_API_KEY 必須または api_key 引数で渡す）。

例（Python REPL / スクリプト内）:
```python
import duckdb, datetime
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
n_written = score_news(conn, datetime.date(2026, 4, 1), api_key='sk-...')
print(f"wrote {n_written} scores")
```

レジーム判定関数は kabusys.ai.regime_detector.score_regime を使用できます（同様に DuckDB 接続と API キーを渡します）。

---

## 主要な設定（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / DUCKDB_PATH: データベースのパス
- PID_FILE_PATH / KILL_FLAG_PATH: Execution の PID / kill flag パス
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート用 LINE 設定

Settings クラスにより .env ファイルまたは OS 環境から読み込まれ、バリデーションが行われます。不正な値があると例外が発生します。

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml がある場所）を探索して .env を読み込みます。
- .env.local が存在する場合は上書き読み込みされます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みを無効化できます。

---

## DB 初期化 / マイグレーション

- Monitoring の初期化は init_monitoring_db(sqlite_conn) を使います（冪等）。必要なテーブルとインデックスを作成します。
- 既存 DB に対する簡単なマイグレーション（列追加など）も実装されています（例: dashboard.peak_value や trade_logs.latency_ms の追加）。

---

## トラブルシューティング / 注意点

- psutil によるプロセス優先度設定や CPU affinity の操作は権限が必要になる場合があります。権限不足時は警告が出て処理は継続されます。
- OPENAI_API_KEY 未設定時、AI 機能は ValueError を投げます（明示的にエラーを出す設計）。
- Paper Trading は本番 DB と分離して動作するため、実際の注文イベントは data/paper_trading.db に記録されます。
- monitoring は本番 sqlite_path を使用します（環境に関わらず）。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開きます（起動に monitoring DB が必要）。

---

## ディレクトリ構成（主要ファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定管理（Settings）
    - run_monitoring.py               — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py                   — ニュース NLP / OpenAI スコアリング
      - regime_detector.py            — 市場レジーム判定（LLM + ETF MA）
    - monitoring/
      - __init__.py
      - monitoring_db.py              — SQLite 永続化層（init / CRUD）
      - system_monitor.py             — システム状態・データ鮮度監視
      - trade_monitor.py              — 注文滞留・約定異常監視
      - risk_monitor.py               — ドローダウン・ポジション上限監視
      - kill_switch.py                — kill.flag 管理
      - alert_manager.py              — LINE 通知ラッパー
      - monitoring_engine.py          — Monitor まとめ（ポーリング制御）
      - streamlit_dashboard.py        — streamlit ダッシュボード
    - execution/
      - order_manager.py              — 発注状態遷移・送信ロジック
      - reconciler.py                 — 再起動時の同期 / ポジション照合
      - (その他ブローカー関連 / order_repository 等)
    - portfolio/
      - portfolio_builder.py          — 候補選定・重み計算
      - risk_adjustment.py            — セクター上限・レジーム乗数
      - position_sizing.py            — 発注株数算出（ロット丸め等）
    - research/
      - factor_research.py            — momentum / volatility / value ファクター
      - feature_exploration.py        — 将来リターン / IC / 要約統計
    - tools/
      - paper_verification_report.py  — Paper Trading 検証レポート CLI
    - utils/
      - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
    - その他モジュール群（data, strategy, 等が別途存在する前提）

---

## 開発・拡張のポイント

- ファイル内の多くの関数・クラスは「純粋関数」「DB 参照のみ」「副作用最小化」といった設計方針に従っています。テストが書きやすく、モックしやすい構造です。
- AI 関連はリトライ・バリデーション・部分書き込み（fail-safe）等に配慮して実装されています。
- Execution と Monitoring は分離されており、kill.flag による外部停止・LINE 通知などで運用安全性を高めています。

---

必要であれば、以下の追加情報を作成します：
- フルな requirements.txt の推定
- 具体的な .env.example（必須変数・推奨値）
- よくある運用コマンドのシェルスクリプト雛形（systemd ユニット例 等）
- 各モジュールの API ドキュメント（関数シグネチャと例）