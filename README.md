# KabuSys

日本株自動売買システムの一部（実行エンジン / 監視 / ポートフォリオ構築 / リサーチ / AI 補助など）の実装です。  
この README はリポジトリ内の主要スクリプトやモジュールの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント群（ExecutionEngine、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニュース解析など）を持つモジュール群です。  
主要な設計方針の例：

- 実行系と監視は sqlite / duckdb を用いて永続化／分析を行う
- Paper Trading（検証）モードでは本番 DB と分離された専用 SQLite を使用
- AI（OpenAI）を用いたニュースセンチメントやレジーム判定をサポート（API キー必須）
- 監視はデーモン的にポーリングし、状態に応じて kill.flag を書くことで ExecutionEngine を停止できる
- Streamlit で簡易監視ダッシュボードを提供

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution.py）
  - ランタイム環境により MockBroker（paper_trading）と実ブローカーを切替
  - OrderManager / RiskManager / Reconciler を組み立ててセッションを実行
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスクやプロセス・データ鮮度監視
  - TradeMonitor: 注文滞留や約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視（kill.flag 発行）
  - MonitoringEngine: 上記をまとめて定期実行、LINE 通知（AlertManager）にも対応
  - Streamlit ダッシュボード（監視用）
- Tools
  - paper_verification_report: Paper Trading の検証レポートを生成
- Portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - ファクター計算（Momentum/Value/Volatility 等）、特徴量探索、IC 計算
- AI
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores テーブルへ書き込み）
  - regime_detector: ETF + マクロニュースを使った日次レジーム判定

---

## 必要条件（例）

- Python 3.9+（コードは型アノテーション等を利用）
- 必須 Python パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（LINE/API 呼び出し・ブローカー API）

パッケージは requirements.txt が用意されている想定であれば次のようにインストールします：

```bash
pip install -r requirements.txt
# または個別
pip install duckdb psutil requests openai streamlit
```

---

## 環境変数（主なもの）

Settings クラスは .env / .env.local / OS 環境変数から読み込みます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主要な環境変数の例：

- KABUSYS_ENV: 起動環境（`development` | `paper_trading` | `live`）。デフォルト `development`
  - paper_trading の場合、MockBroker を使用し DB は `PAPER_TRADING_SQLITE_PATH` を参照
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: paper_trading の約定挙動（`instant`|`partial`|`never`|`reject`、デフォルト `instant`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）
- SQLITE_PATH: 監視用 SQLite（デフォルト `data/monitoring.db`）
- DUCKDB_PATH: DuckDB パス（デフォルト `data/kabusys.duckdb`）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト `data/execution.pid`）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト `data/kill.flag`）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔 (秒、デフォルト 60、1 以上でない場合はデフォルトにフォールバック)
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（`1` = 有効）

例（.env）:

```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境作成（推奨）と依存パッケージのインストール

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

3. .env をプロジェクトルートに配置（または環境変数を設定）
   - 自動読み込みは Settings モジュールで .git / pyproject.toml を基準に実施されます
4. data ディレクトリを作成（必要に応じて）

```bash
mkdir -p data
```

5. （任意）DuckDB / SQLite の初期テーブルは各起動スクリプトが起動時に作成します（init_monitoring_db が呼ばれます）。

注意: 監視用 DB（monitoring）は常に production sqlite_path を使う設計になっているため、paper_trading の場合は `PAPER_TRADING_SQLITE_PATH` を別途指定して本番データと分離してください。

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動する（本番 or paper_trading を KABUSYS_ENV で切替）:

```bash
# 本番・開発を環境変数で選ぶ
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

- Monitoring（システム監視）を起動する:

```bash
# ポーリング間隔を環境変数で上書き（秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- Streamlit ダッシュボードで監視状況を閲覧（read-only 接続可能なら起動）:

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポートを作成:

```bash
# デフォルト DB path は data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または別 DB を指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI 関連（ニューススコア／レジーム判定）は `OPENAI_API_KEY` の設定が必要です。モジュールは programmatic に呼び出す形です（例）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
```

---

## 監視まわりの概念メモ

- MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を順次実行し、KillSwitch（ドローダウン等で kill.flag を書く）と AlertManager（LINE push）を組み合わせて動作します。
- kill.flag（デフォルト data/kill.flag）が存在すると ExecutionEngine 停止を示すシグナルとなります。KillSwitch は冪等にファイルを書き、既存なら上書きしません。
- Monitoring は起動時に PID ファイル（ExecutionEngine の PID）をチェックし、stale PID を検出した場合は削除してログに残します。

---

## 開発者向け補足

- Settings モジュールは .env/.env.local を自動ロードしますが、テスト時など自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Process priority の設定は `psutil` を経由して行います。High に設定する際は OS 権限が必要な場合があります（set_process_priority）。
- DB マイグレーション（簡易）は monitoring_db.init_monitoring_db が実行時に行います（新しいカラムがなければ ALTER を適用）。

---

## ディレクトリ構成

大まかなファイル／モジュール一覧（主要ファイルのみ）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env 読み込み / Settings
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring（ポーリング）起動スクリプト
  - utils/
    - process_priority.py       — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py
    - order_record.py
    - ...                      — 発注関連
  - monitoring/
    - monitoring_db.py         — SQLite テーブル定義 / MonitoringDB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
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
    - pipeline.py               — DuckDB のデータ取得ユーティリティ等（参照される）
  - tools/
    - paper_verification_report.py

（上記はリポジトリ内の主要なモジュール配置の抜粋です。実際のファイル数や小モジュールはさらに存在します。）

---

## よくある質問 / 注意点

- 監視ログ（monitoring.db）と Paper Trading DB は分離してください。KABUSYS_ENV に応じて paper_trading 用の SQLite パスを指定できます。
- MONITOR_POLL_INTERVAL は 1 秒未満や 0 を与えると無効としてデフォルト（60 秒）に戻ります。
- OpenAI を利用する処理は API 呼び出し失敗時にフォールバック（多くの場合 0 やスキップ）するよう実装されていますが、API キーは必須です。ローカルでテストする際はモックが推奨されます。
- プロセス優先度や CPU affinity の変更は権限に依存します。失敗した場合は警告ログを出し続行します。

---

もし README に追加したい内容（例：要求される exact package versions、CI／テスト手順、より詳しい設定例、データスキーマ、API仕様書等）があれば教えてください。必要に応じてサンプル .env.example も作成します。