# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュース収集、AI によるニュース分析、ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質チェック・特徴量作成・AIによるニュース評価・市場レジーム判定・監査ログ管理など、運用・研究・アルゴリズム取引のための基盤機能をまとめた Python モジュール群です。  
主な設計方針は次のとおりです。

- DuckDB を中心としたローカル DB をデータプラットフォームとして利用する
- ETL は差分取得・冪等保存・品質チェックを含む
- ニュース収集は SSRF 対策・サイズ制限等の安全対策を実施
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価／市場レジーム判定をサポート（JSON mode）
- ルックアヘッドバイアスを避ける設計（内部で date.today()/datetime.today() を不用意に参照しない）
- 外部 API のレート制御・リトライを実装

---

## 機能一覧

- data
  - ETL（株価・財務・市場カレンダー）: 差分取得 / 保存（J-Quants 経由）
  - カレンダー管理（営業日判定 / next/prev / SQ判定）
  - ニュース収集（RSS）: 正規化・SSRF防御・冪等保存の前提で収集
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - J-Quants API クライアント（トークン取得・ページネーション・保存ユーティリティ）
  - 監査ログスキーマ作成 / 初期化（signal_events / order_requests / executions）
  - 統計ユーティリティ（Zスコア正規化）
- ai
  - news_nlp.score_news: ニュースを銘柄毎に集約し LLM でスコア化して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM センチメントを合成して market_regime に保存
- research
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（スピアマン）計算、基本統計サマリー
- audit
  - 監査ログ初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## 要件（主な依存ライブラリ）

- Python 3.10+
- duckdb
- openai
- defusedxml

（プロジェクトに requirements.txt がある場合はそちらを使用してください。なければ上記を pip でインストールしてください。）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-dir>
```

2. 仮想環境作成と依存インストール（上記要件参照）

3. 環境変数の設定
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化可能）。

主要な環境変数（必須／任意）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
- OPENAI_API_KEY (必須 for AI モジュール) — OpenAI API キー
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — development | paper_trading | live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG | INFO | WARNING | ERROR | CRITICAL

サンプル `.env`:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DB 初期化（監査ログなど）
- DuckDB 接続を取得してスキーマを初期化できます。例:

```python
import duckdb
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
conn.close()
```

---

## 使い方（主要な例）

※ 以降の例では settings から path/環境変数を読む設計です。必要に応じて明示的な引数で API キー等を渡せます。

1) DuckDB 接続取得:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date省略で今日（内部で営業日に調整）
print(result.to_dict())
```

3) ニュースのスコアリング（AI）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY で解決されます
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

4) 市場レジーム判定（AI）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) ニュース RSS 取得
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

6) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

7) 監査ログ用 DB 初期化（専用ファイル）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.duckdb")
# audit_conn を使って監査テーブルへ書き込み可能
```

---

## 注意点 / 運用上のポイント

- OpenAI 呼び出しは外部API料金・レート・応答変動の影響を受けます。API制限や費用に留意してください。
- ニュース収集では SSRF 対策や受信サイズ制限を行っていますが、運用に応じて追加対策を検討してください。
- J-Quants API にはレート制限があります（コード内で固定間隔レートリミッタ／リトライを実装）。
- 環境変数自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV はデプロイモードを定義します（development / paper_trading / live）。live の場合は外部発注など特権的な動作に注意してください。

---

## ディレクトリ構成

（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py                — ETF MA とニュースセンチメントを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - etl.py                            — ETL 結果クラスの再エクスポート
    - news_collector.py                 — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py            — マーケットカレンダー管理（営業日判定等）
    - quality.py                        — データ品質チェック
    - stats.py                          — 統計ユーティリティ（zscore）
    - audit.py                          — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py                — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py            — 将来リターン / IC / 統計サマリー
  - research/... (他ユーティリティ)
- data/                                  — デフォルトの DB ファイル保存先（.gitignore で分離すること）

---

## コントリビューション / 開発

- 新しい機能や修正はブランチを切ってプルリクエストを送ってください。
- 重要な設計方針（ルックアヘッドバイアス回避、冪等性、セキュリティ対策）を壊さないよう注意してください。
- テストは外部 API を直接叩かないようモックを利用してください（コード内でもテストしやすいように _call_openai_api 等を分離しています）。

---

不明点や追加で README に載せたい項目があれば教えてください。必要に応じてサンプルスクリプトや具体的な運用手順（cron／Airflow など）も追記できます。