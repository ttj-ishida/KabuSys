# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。データ収集（J-Quants）、品質チェック、特徴量生成、ニュースの自然言語処理（OpenAI）、市場レジーム判定、監査ログ（発注〜約定のトレーサビリティ）など、売買戦略開発および運用に必要な機能群を提供します。

主な設計方針は「ルックアヘッドバイアスを避ける」「DB（DuckDB）中心で再現性を担保する」「冪等性・フェイルセーフを重視する」ことです。

---

## 主な機能一覧

- data
  - ETL（J-Quants API から日次株価、財務、カレンダーを差分取得・保存）
  - カレンダー管理（営業日・SQ判定、next/prev trading day 等）
  - ニュース収集（RSS -> raw_news、SSRF対策・正規化）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ）
  - 監査ログ初期化 / audit DB（signal/events/order/exec のテーブル群）
  - 汎用統計ユーティリティ（Zスコア正規化等）

- ai
  - ニュース NLP（銘柄ごとのセンチメントを OpenAI で評価して ai_scores に保存）
  - 市場レジーム判定（ETF 1321 の MA200乖離 と マクロニュースの LLMセンチメントを合成して日次で bull/neutral/bear を判定）

- research
  - ファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリのユーティリティ

- 設定・運用
  - 環境変数管理（.env 自動ロード、必須設定のチェック）
  - ログレベル・実行環境フラグ（development / paper_trading / live）
  - 監視・Slack 通知のための設定（トークン・チャンネルID）

---

## 必要条件 / インストール

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml

例（仮想環境内で）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクト配布が setuptools/poetry であれば `pip install -e .` のようにインストールしてください）

---

## 環境変数 / 設定

プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。自動ロードは .git または pyproject.toml を基準にプロジェクトルートを探索します。

主な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（運用通知）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（ai モジュールを使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行プロセスの PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例 `.env`（最小）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
```

---

## セットアップ（データベース初期化など）

監査ログ用の DuckDB を初期化する例:
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

conn = init_audit_db(settings.duckdb_path)  # ファイルを作成して接続を返す
```

DuckDB 接続の一例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

---

## 使い方（代表的な呼び出し例）

- 日次 ETL 実行（株価・財務・カレンダーの差分取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュースの NLP スコアを生成（ai -> ai_scores へ書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, date(2026, 3, 20))  # target_date を指定
print(f"written: {n_written}")
```

- 市場レジーム判定を実行（market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, date(2026, 3, 20))
```

- 監査 DB を別に作る（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

- OpenAI を使う機能をテストする際は、引数 `api_key` を直接渡すことで環境変数に依存しない実行が可能です（テスト用モックとも組みやすい設計）。

---

## 運用上の注意

- ルックアヘッドバイアス回避のため、各モジュールは内部で date.today()/datetime.today() を不必要に参照しない設計になっています。必ず target_date を明示して実行するか、run_daily_etl のように意図した日付で呼び出してください。
- OpenAI 呼び出しではリトライ・フェイルセーフが組み込まれており、API失敗時はスコアを 0.0 にフォールバックする等の保護があります。
- J-Quants クライアントはレート制限（120 req/min）とリトライ/トークン自動更新を実装しています。
- .env はプロジェクトルートの .env/.env.local を自動的に読み込みます。テスト時に自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany はバージョンや空リストに注意している箇所があります（コード中にガードあり）。

---

## ディレクトリ構成（抜粋）

リアルなリポジトリでは src/ 配下にパッケージが配置されています。代表的な構成は以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの NLP（OpenAI）
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py      — J-Quants API クライアント / 保存ロジック
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py      — RSS 収集（SSRF対策・正規化）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ（テーブル定義・初期化）
    - etl.py                 — ETL 公開インターフェース（ETLResult の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/, research/ 以下にそれぞれの公開 API が用意されています

---

## ライセンス / コントリビュート

（この README にライセンスやコントリビュート方法が必要であれば、その情報を追加してください）

---

必要であれば、README に以下を追加できます：
- CI / テストの実行方法（pytest 等）
- 詳しい .env.example（全キーと説明）
- よくあるエラーと対処法（OpenAI rate limit、J-Quants トークン期限切れ 等）
- 実運用時の起動スクリプト例（systemd / cron / airflow など）