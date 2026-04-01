# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J‑Quants や RSS、OpenAI（LLM）を用いてデータ収集・品質管理・特徴量生成・ニュースセンチメント評価・市場レジーム判定・監査ログを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J‑Quants API からの株価・財務・カレンダー取得（ETL）
- ニュース収集・前処理・LLM によるニュースセンチメント算出
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- ファクター計算・研究用ユーティリティ（モメンタム・バリュー・ボラティリティ等）
- データ品質チェック・監査ログ（発注・約定のトレーサビリティ）
- DuckDB ベースのデータ格納と冪等保存ロジック

設計面では「ルックアヘッドバイアス防止」「冪等処理」「堅牢なリトライ」「DB優先のカレンダー判定」などに重点を置いています。

---

## 主な機能一覧

- data/jquants_client: J‑Quants API との通信・取得・DuckDB への保存（差分取得・ページネーション・トークン自動リフレッシュ・レートリミット）
- data/pipeline: 日次 ETL パイプライン（run_daily_etl）、個別 ETL（run_prices_etl 等）と ETL 結果クラス
- data/quality: 欠損・スパイク・重複・日付不整合の品質チェック
- data/news_collector: RSS 収集、前処理、SSRF 対策、トラッキングパラメータ除去
- data/calendar_management: JPX カレンダー管理、営業日判定/前後営業日取得、カレンダー更新ジョブ
- data/audit: 発注／約定の監査テーブル定義と初期化（init_audit_schema / init_audit_db）
- data/stats: zscore 正規化など共通統計ユーティリティ
- ai/news_nlp: ニュースを LLM（gpt-4o-mini）でセンチメント評価して ai_scores に保存する score_news
- ai/regime_detector: ETF 1321 の MA200 乖離とマクロニュース LLM 評価を合成して市場レジームを判定・保存する score_regime
- research: ファクター計算（calc_momentum / calc_value / calc_volatility）・特徴量探索（calc_forward_returns / calc_ic / factor_summary）

---

## 必要条件（推奨）

- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - openai (OpenAI の Python SDK)
  - defusedxml
- ネットワーク接続（J‑Quants API、RSS、OpenAI）

注: このリポジトリに requirements.txt は含まれていないため、プロジェクト利用時は必要パッケージをインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# その他、プロジェクトで必要なパッケージを追加
```

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動ロードされます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主要な環境変数（Settings で参照されるもの）:

- JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（省略時 data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイル（省略時 data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime に渡すことも可能）

.env 例（最低限）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -e .
# または必要パッケージを個別にインストール
pip install duckdb openai defusedxml
```

2. 環境変数を設定
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を作成してください。
   - 必須変数: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD（用途により OPENAI_API_KEY）

3. DuckDB ファイル・監査DBの初期化（任意）
```python
from kabusys.config import settings
import duckdb
from kabusys.data.audit import init_audit_db, init_audit_schema

# 既存アプリの DB 接続を使う場合
conn = duckdb.connect(str(settings.duckdb_path))
# 監査スキーマを同一接続に追加する場合
init_audit_schema(conn)

# 監査専用 DB を作る場合
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（例）

以下は主要機能の利用例です。すべて look-ahead バイアスを避けるため明示的に date を渡す設計になっています。

- 日次 ETL を実行（prices / financials / calendar を差分取得し品質チェック）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成して ai_scores に保存
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print(f"written: {n_written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース LLM の合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
```

- ファクター計算・研究用ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

---

## 開発メモ / テスト時の注意

- OpenAI API を呼ぶ関数（news_nlp._call_openai_api / regime_detector._call_openai_api）はテスト時に patch して差し替えやすく設計されています。ユニットテストではこれらをモックしてください。
- .env 自動読み込みはパッケージロード時に行われます。テストで自動ロードを抑制したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany はバージョンによって空リストを受け付けない制約があり、コード内で保護処理を行っています。テストデータを扱う際は留意してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイルおよびモジュールの概観です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースの LLM スコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J‑Quants API クライアント（取得・保存）
    - pipeline.py                  — ETL パイプラインと ETLResult
    - etl.py                       — ETL の公開インターフェース再エクスポート
    - stats.py                     — zscore_normalize 等の統計ユーティリティ
    - quality.py                   — データ品質チェック
    - news_collector.py            — RSS 収集と前処理
    - calendar_management.py       — JPX カレンダー管理 / 営業日判定
    - audit.py                     — 監査ログ（発注/約定）スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py       — calc_forward_returns / calc_ic / rank / factor_summary
  - monitoring/ (パッケージとして __all__ に含まれますが実装がない場合あり)
  - strategy/ (同上)
  - execution/ (同上)

（実際のファイル・サブパッケージはリポジトリ内のソースを参照してください）

---

## ライセンス / 貢献

この README にはライセンス情報や貢献ルールは含まれていません。運用・公開にあたってはリポジトリルートの LICENSE / CONTRIBUTING を確認してください。

---

何か追加してほしいトピック（例: デプロイ手順、CI 設定、より詳しい API 使用例など）があれば教えてください。README を拡張して追記します。