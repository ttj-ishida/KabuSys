# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。「データ収集（ETL）」「ニュース収集・NLP」「市場レジーム判定」「ファクター研究」「監査ログ（トレーサビリティ）」などを包括的に提供します。バックテスト／運用の両フェーズで使える設計思想（ルックアヘッドバイアス回避、冪等性、リトライ・レート制御、安全対策）を備えています。

主な特徴
- J-Quants API 経由の差分 ETL（株価、財務、マーケットカレンダー）
- RSS ベースのニュース収集と記事→銘柄紐付け
- OpenAI（gpt-4o-mini 想定）を利用したニュースセンチメント（ai_scores）生成
- ETF（1321）ベースの 200 日移動平均乖離 と マクロニュースセンチメントの合成による市場レジーム判定
- ファクター計算（モメンタム／ボラティリティ／バリュー）と特徴量探索ユーティリティ（将来リターン・IC・要約）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマ作成ユーティリティ
- DuckDB を中心としたローカルデータ永続化（冪等保存）

---

## 機能一覧（抜粋）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - 設定プロパティ（J-Quants / kabu API / Slack / DB パス / 環境）
- kabusys.data
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: API 呼び出し、ページネーション、保存（raw_prices / raw_financials / market_calendar）
  - news_collector: RSS 取得・前処理・SSRF 対策・raw_news への保存
  - calendar_management: 営業日判定・next/prev/get_trading_days 等
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマの初期化 / init_audit_db
  - stats: zscore_normalize 等
- kabusys.ai
  - news_nlp.score_news: ニュースを銘柄ごとにまとめて LLM でセンチメント取得 → ai_scores へ保存
  - regime_detector.score_regime: ETF（1321）MA200 瞬間値と LLM によるマクロセンチメントの合成で市場レジーム判定 → market_regime へ保存
- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.9+（typing, | を型注釈で使用しているため 3.10 推奨）
- DuckDB（Python パッケージとしてインストール）
- OpenAI SDK（OpenAI の Chat Completions を使う場合）
- defusedxml（RSS 安全パース用）

例（venv を使う）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発中ならパッケージを編集可能インストール
pip install -e .
```

環境変数（必須・主要）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- SLACK_BOT_TOKEN — Slack 通知が必要な場合
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注系を実装する際に使用）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（監視 DB 等、デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development | paper_trading | live）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動 .env 読み込み
- プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）が検出されると、
  ルートの `.env` → `.env.local` を自動的に読み込みます。
- テストなどで自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（例）

以下は Python から関数を呼び出す基本例です。 CLI は本リポジトリに含まれていないため、スクリプトとして呼ぶことを想定しています。

1) 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使う場合は settings.duckdb_path
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None で環境変数 OPENAI_API_KEY を参照
print(f"written {written} scores")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ DB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を利用して order / signal 周りを記録できます
```

5) カレンダー判定ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 4, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## 注意事項・設計上のポイント

- ルックアヘッドバイアス回避:
  - AI モジュールや ETL は内部で date.today()/datetime.today() に安易に依存しないよう設計されています（target_date を明示して実行）。
- 冪等性:
  - DB 保存は基本的に ON CONFLICT DO UPDATE / INSERT ... DO UPDATE（重複対策）で実施。
- API 呼び出し:
  - J-Quants クライアントはレート制御（120 req/min）とリトライ（バックオフ）を実装。
  - OpenAI 呼び出しもリトライやパース失敗フェイルセーフ（多くのケースで無害なゼロスコアにフォールバック）を実装。
- セキュリティ:
  - RSS 収集は SSRF 対策、最大受信サイズ制限、defusedxml による XML パース等の防御を実装。
- テスト:
  - 内部 API 呼び出し関数はテストから patch しやすいように分離（例: _call_openai_api をモック可能）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py (re-export)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*（factor/feature utilities）
- その他: strategy / execution / monitoring （パッケージ公開設定ありが仮定）

（上記は本 README に含まれる主要ファイルの一覧です。詳細はソースコードを参照してください。）

---

## 依存関係（主要）
- duckdb
- openai（LLM 呼び出し用）
- defusedxml（RSS パースの安全化）
- 標準ライブラリ：urllib, json, logging, datetime, dataclasses など

具体的な requirements.txt はリポジトリに合わせて用意してください。

---

## よくある運用フロー（例）
1. 環境変数 / .env を準備（J-Quants トークン、OPENAI_API_KEY 等）
2. DuckDB を初期化し、run_daily_etl を毎朝（夜間バッチ）実行して最新データを取り込む
3. 毎朝ニューススコア（score_news）を実行し ai_scores を更新
4. regime_detector.score_regime を実行して market_regime を更新（運用判断に利用）
5. 戦略は ai_scores / market_regime / ファクターを参照してシグナル生成 → 監査ログ / 発注フローへ

---

必要であれば、README に CLI サンプルスクリプト、docker-compose / systemd ユニット例、より詳しい .env.example や DB スキーマ図などを追記できます。どの追加情報が欲しいか教えてください。