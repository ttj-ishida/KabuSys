# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。ETL、ニュースNLP（LLM を用いたセンチメント）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどを含むユーティリティを提供します。

---

## 概要

KabuSys は以下の目的を持つコンポーネント群をまとめた Python パッケージです：

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたデータ保存・ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ニュース収集と LLM（OpenAI）によるニュースセンチメント評価
- マクロセンチメントとテクニカル指標を組み合わせた市場レジーム判定
- ファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ、IC 等）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用スキーマ初期化ユーティリティ

パッケージはモジュール化されており、ETL / 研究 / 戦略 / 実行 / 監視といったワークフローで必要な機能を呼び出して使えます。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API からの取得（日次株価、財務、上場銘柄、マーケットカレンダー）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レート制御・リトライ・自動トークンリフレッシュ
- data.pipeline
  - 日次 ETL（calendar, prices, financials）の差分取得／保存
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - ETLResult による実行結果管理
- data.news_collector
  - RSS フィードの収集、前処理、raw_news への冪等保存
  - SSRF 対策、受信サイズ制限、XML の安全パース
- ai.news_nlp
  - 記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメントを計算して ai_scores に書き込む
- ai.regime_detector
  - ETF（1321）200日移動平均乖離とマクロニュース LLM スコアを合成して市場レジーム（bull/neutral/bear）判定
- research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary 等
- data.audit
  - 監査ログ（signal_events, order_requests, executions）のスキーマ初期化ユーティリティ

---

## 前提 / 必要環境

- Python 3.10 以上（`|`型注釈・その他記法を使用）
- 必須（主要）ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

インストール例（プロジェクト配布に requirements.txt がある場合はそちらを使用してください）:

```bash
python -m pip install duckdb openai defusedxml
```

※ 実際の運用ではその他ロギング等の依存があるかもしれません。プロジェクトの packaging 情報を参照してください。

---

## 環境変数 / 設定

KabuSys は環境変数または .env ファイルから設定値を読み込みます（自動ロードの挙動は `kabusys.config` を参照）。

主に使用される環境変数（一例）:

- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants 用リフレッシュトークン（data.jquants_client.get_id_token で使用）
- KABU_API_PASSWORD (必須)  
  - kabuステーション API のパスワード（execution 関連で使用）
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (必須 for AI 実行)  
  - OpenAI クライアントで使用
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)  
  - 通知連携などで使用
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START (監視プロセス用)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT (監視用閾値)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

.env の自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env`、次に `.env.local` を読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きできます。
- 自動読み込みを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル風の export 形式やコメント、クォート・エスケープ等に対応した独自実装です。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-directory>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt   # もし requirements.txt があれば
   # なければ最低限:
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成して必要なキーを設定してください（例）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動ロードが働かない場合は明示的に環境変数を export してください。

5. データベース用ディレクトリの準備
   ```bash
   mkdir -p data
   ```

---

## 使い方（クイックスタート）

以下はいくつかの代表的な呼び出し例です。実行する前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続の作成例:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:

```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しなければ今日（ローカル）を対象
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）のスコアを作る:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 例: 2026-03-20 を対象
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DuckDB データベース初期化:

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブル類が作成されます
```

- 研究用ユーティリティ（ファクター計算）:

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum_records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化:
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(momentum_records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

注意:
- AI（OpenAI）呼び出しは API キーを必要とします。`OPENAI_API_KEY` を環境変数にセットするか、関数引数で `api_key=...` を渡してください。
- 関数はルックアヘッドバイアスを避けるよう設計されています（target_date に依存し、内部で datetime.today() などを参照しない実装方針が多く採用されています）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なファイルと説明です（src/kabusys をルートとする）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード・設定取得用（Settings）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの集約・LLM によるセンチメント付与（ai_scores 書き込み）
    - regime_detector.py  — ETF MA200 とマクロセンチメントの合成によるレジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント、取得・保存ユーティリティ
    - pipeline.py         — 日次 ETL パイプライン（run_daily_etl など）
    - etl.py              — ETLResult 再エクスポート
    - news_collector.py   — RSS 収集・前処理・保存
    - calendar_management.py — 市場カレンダー判定・更新ロジック
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py            — 監査ログテーブルの DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - research パッケージやその他に strategy / execution / monitoring のサブパッケージが期待される（プロジェクト全体設計に依存）。

---

## 実運用上の注意点

- 認証情報（API トークン）は厳重に管理し、公開リポジトリに置かないでください。
- OpenAI の呼び出しはコストが発生します。バッチサイズやリトライ設定を確認してください（news_nlp、regime_detector にリトライ制御あり）。
- DuckDB ファイルは単一プロセスでのアクセスが想定される場合があります。運用時は適切な接続管理を行ってください。
- ETL は外部 API に依存するため、ネットワーク障害や API 仕様変更に備えた監視とログが重要です。

---

## 貢献 / 開発

- バグ報告・機能提案は Issue を立ててください。
- 新しい機能追加や修正は PR を送り、既存のユニットテスト（ある場合）を実行してください。
- 自動テスト・CI の設定はプロジェクトルートの設定に従ってください（該当ファイルがあれば）。

---

この README はコードベースの主要機能をまとめた概要です。各モジュールの詳細な API、引数仕様や戻り値は該当ファイルの docstring を参照してください。必要であれば、具体的な利用例（ETL スケジューリング、戦略からの発注フロー等）を追記します。