# KabuSys

日本株向け自動売買プラットフォームの一部実装。ポートフォリオ構築、注文発行・管理、監視、研究（ファクター計算）およびニュースNLP/レジーム判定などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。主な役割は以下の通りです。

- 市場データ（DuckDB）を用いたファクター計算・特徴量探索
- ポートフォリオ構築と銘柄ウェイト・株数決定
- 注文発行・状態管理・再同期（Reconciler）
- 監視（System / Trade / Risk）とアラート（LINE）
- Paper Trading 用の検証レポート生成ツール
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（news_nlp, regime_detector）
- Streamlit を使った監視ダッシュボード

設計方針として、DB 操作は明確に分離し、外部 API 呼び出し（ブローカー・OpenAI 等）は抽象化／フェイルセーフを重視しています。

---

## 主な機能一覧

- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重配分、スコアに基づく株数算出（単元丸め、上限・集約制約）
  - セクターキャップ、レジームによる投下資金乗数

- 研究（research）
  - Momentum / Volatility / Value 等ファクター計算（DuckDB を利用）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー

- 実行（execution）
  - OrderManager / ExecutionEngine（発注・リスク管理）
  - Reconciler による起動時の状態同期（ブローカーとローカルの突合作業）

- 監視（monitoring）
  - SystemMonitor（プロセス・CPU/メモリ/ディスク・データ鮮度）
  - TradeMonitor（滞留注文・約定異常価格）
  - RiskMonitor（ドローダウン・ポジション上限）
  - KillSwitch（フラグファイルで ExecutionEngine 停止）
  - AlertManager（LINE Push）
  - Monitoring DB（SQLite）への永続化、Streamlit ダッシュボード

- AI
  - news_nlp: news をまとめて OpenAI に投げ、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む
  - regime_detector: ETF MA とマクロニュースを組み合わせて日次レジームを判定

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## 必要環境 / 依存ライブラリ

主に以下の Python パッケージが必要です（バージョンは適宜選定してください）。

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード起動時)
- その他標準ライブラリ：sqlite3, pathlib, datetime 等

例（pip）:
```
pip install duckdb psutil requests openai streamlit
```

注意: 実行環境により追加の依存や OS 権限（プロセス優先度設定等）が必要になる場合があります。

---

## セットアップ手順

1. リポジトリをクローン／展開
2. Python 環境を準備（venv 推奨）
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定（.env をプロジェクトルートに置くことが可能。自動読み込みあり）
   - 自動読み込みを無効化したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. データディレクトリ（デフォルト `data/`）の作成:
```
mkdir -p data
```
6. 必要に応じて DuckDB / SQLite の初期データを配置
   - monitoring 用の SQLite（デフォルト `data/monitoring.db`）は実行時に初期化されます

サンプル .env（プロジェクトルート）:
```
KABUSYS_ENV=development          # development | paper_trading | live
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
PAPER_FILL_MODE=instant         # instant|partial|never|reject
```

---

## 環境変数（主要）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（既定: development）
  - paper_trading の場合、run_execution は MockBrokerClient を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します（本番 DB と分離）。
- SQLITE_PATH: 監視（monitoring）用 SQLite DB（既定: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（既定: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（既定: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各外部 API 用トークン/パスワード
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（既定: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（既定: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、既定: 60）
- PAPER_FILL_MODE: paper_trading の MockBroker 動作モード（instant|partial|never|reject）

設定値は `kabusys.config.Settings` クラス経由で取得され、必要な場合にバリデーションされます。

---

## 実行方法

### 監視ループの起動
SystemMonitor をポーリングで起動します。MONITOR_POLL_INTERVAL 環境変数で間隔変更可能（デフォルト 60 秒）。実行中は monitoring 用 SQLite（settings.sqlite_path）と DuckDB に接続します。

```
python -m kabusys.run_monitoring
```

主な挙動:
- プロセス優先度を "high" に設定を試みる
- monitoring DB の初期化（テーブル作成・マイグレーション）
- SystemMonitor.check_once() を定期実行して system_status / risk_logs 等を記録
- Ctrl+C (KeyboardInterrupt) で終了

例: ポーリングを30秒にしたい場合:
```
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

### 実行エンジン（ExecutionEngine）の起動
注文発行等の実行エンジンを起動します。KABUSYS_ENV により paper_trading 時は MockBroker を使用します。

```
python -m kabusys.run_execution
```

注意:
- Paper トレード時は SQLite パスに PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と分離されます。
- 起動時に Reconciler による自動復旧（未送信注文の突合など）が行われます。
- 実行前に必要な環境変数（API キー等）を確認してください。

### Paper Trading 検証レポート生成
paper_trading 用の SQLite DB を指定して、検証レポートを標準出力へ出力します。

```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB パスを直接指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

出力内容:
- システム稼働率（system_status）
- 注文成功率・送信率（trade_logs）
- リスク却下数（risk_logs）
- API レイテンシ（trade_logs.latency_ms）
- PASS/FAIL の簡易判定（既定閾値あり）

### Streamlit ダッシュボード
監視データを可視化する簡易ダッシュボード。 MonitoringEngine が生成する SQLite DB を読み取りモードで開きます。

```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

### AI モジュール（news_nlp / regime_detector）の利用（API として）
CLI は提供していませんが、ライブラリ関数を直接呼び出して利用できます。いずれも DuckDB 接続と target_date、OpenAI API キーが必要です。

例（news_nlp.score_news）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
print("written:", n_written)
conn.close()
```

例（regime_detector.score_regime）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 04, 10), api_key="sk-...")
conn.close()
```

注意:
- OPENAI_API_KEY が引数で渡されない場合は環境変数を参照します。
- API 呼び出し失敗時はフェイルセーフで継続（既定のフォールバック値やスキップ挙動あり）。

---

## 開発時の補足

- 設定（.env）自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` があれば自動的に読み込みます。
  - OS 環境変数は保護され、`.env.local` は上書き可能。
  - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- ログ出力
  - 多くのスクリプトは logging.basicConfig(level=logging.INFO) を使用。`LOG_LEVEL` 環境変数で設定可能。

- プロセス優先度設定
  - `kabusys.utils.process_priority.set_process_priority` で Windows/Linux の違いを吸収。権限がない場合は警告を出してスキップします。

---

## 主要ディレクトリ構成（src/kabusys 以下、主要ファイルのみ抜粋）

- kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理（Settings クラス）
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py    — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py            — 候補選定・等重/スコア重み
    - position_sizing.py              — 株数決定・集約制約・単元丸め
    - risk_adjustment.py              — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py              — Momentum/Volatility/Value 計算
    - feature_exploration.py          — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py                     — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py              — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py                — SQLite テーブル初期化・DB レイヤ
    - system_monitor.py               — システム監視
    - trade_monitor.py                — 注文監視
    - risk_monitor.py                 — ドローダウン / ポジション制限監視
    - kill_switch.py                  — フラグファイルでの停止シグナル
    - alert_manager.py                — LINE 通知ユーティリティ
    - monitoring_engine.py            — 各モニタ束ねるエンジン
    - streamlit_dashboard.py          — Streamlit ダッシュボード
  - execution/
    - order_manager.py                — 注文状態遷移とブローカー呼び出し
    - reconciler.py                   — 起動時の状態再同期
    - ...                             — （ブローカー・Engine 等は別ファイル）

各モジュールは責務が明確に分かれており、DuckDB/SQLite などの永続化層や外部 API 呼び出しは分離されています。

---

## 注意事項 / 運用上のヒント

- Paper Trading と Live のデータは明示的に分離する設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 利用部分は API レート制限やネットワーク障害を考慮したリトライ実装が含まれますが、API キー管理とコストには注意してください。
- KillSwitch（data/kill.flag）を書き込むと ExecutionEngine に停止信号を送ります。起動時に該当フラグをクリアするオプションがあります（Settings.kill_flag_clear_on_start）。
- DuckDB/SQLite のバックアップ・バージョン管理は運用で検討してください（特に本番データ）。

---

もし README に追記したい項目（例: 各モジュールの API サンプル、CI / デプロイ手順、詳しい設定例など）があれば教えてください。必要に応じて追記・整備します。