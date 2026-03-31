# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。  
J-Quants / RSS / OpenAI を組み合わせてデータ収集（ETL）、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ（ファクター計算）や監査ログ管理までをカバーします。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で datetime.today()/date.today() を不用意に使わない）
- DuckDB を中心に SQL + Python で効率的に処理
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- DB 書き込みは冪等性（ON CONFLICT 等）を重視

---

## 機能一覧

- データ収集・ETL
  - J-Quants から株価（OHLCV）、財務、上場情報、JPX カレンダーを差分取得・保存
  - ETL の結果を ETLResult で集約
- データ品質チェック（quality）
  - 欠損、重複、スパイク、日付不整合の検出
- ニュース収集（news_collector）
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去・raw_news 保存用ユーティリティ
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントをバッチ評価し ai_scores に保存
  - トークン肥大対策・バッチ処理・JSON Mode 検証・リトライ実装
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して 'bull'/'neutral'/'bear' を判定
  - OpenAI 呼び出しは冪等・リトライ処理を含む
- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 監査ログ（data.audit）
  - signal → order_request → execution のトレーサビリティ用スキーマと初期化ユーティリティ
- J-Quants クライアント（data.jquants_client）
  - レート制御、トークン自動リフレッシュ、ページネーション、DuckDB への冪等保存

---

## 必要条件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （標準ライブラリの urllib 等を使用）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。

---

## セットアップ手順

1. リポジトリを取得
2. 仮想環境作成・有効化
3. 依存ライブラリをインストール（上記参照）
4. 環境変数の設定（下記「環境変数」参照）
5. DuckDB データベースファイルのパス（デフォルト: data/kabusys.duckdb）を準備
6. 監査ログ専用 DB を初期化（必要に応じて）

自動で .env をロードする挙動：
- プロジェクトルート（.git または pyproject.toml の存在）を探索して、`.env` と `.env.local` を自動読み込みします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主要）

必須（実行する機能に応じて必要）：
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（data.jquants_client.get_id_token 等で使用）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注機能等）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI 呼び出しで使用（ai モジュール内で参照）

オプション：
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作モード: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

設定例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易例）

Python API を直接呼ぶケースの代表例を示します。詳細は各モジュールのドキュメント文字列を参照してください。

- DuckDB 接続準備:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None で今日
print(result.to_dict())
```

- ニュースの NLP スコアリング（target_date の前日 15:00 ～ 当日 08:30 JST のウィンドウを対象）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
```

- RSS フィード取得（ニュース収集ユーティリティ）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

- 監査 DB の初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は自動で呼ばれます
```

注意:
- OpenAI を使う関数（news_nlp, regime_detector 等）は API キーが必要です。関数引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants 呼び出しはレート制御およびトークン自動更新が実装されていますが、J-Quants の使用制約や課金ポリシーに注意してください。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要モジュール構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン / run_daily_etl 等
    - etl.py                        — ETLResult の公開
    - news_collector.py             — RSS 収集・前処理
    - calendar_management.py        — JPX カレンダー管理・営業日判定
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査スキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility 等
    - feature_exploration.py        — forward returns / IC / summary
  - (その他: strategy, execution, monitoring のパッケージを想定)

---

## 運用上の注意・設計ノート（抜粋）

- ルックアヘッドバイアス防止:
  - 全ての ETL / スコア処理は対象日以前のデータのみを参照する設計。バックテストでの公平性を考慮しています。
- 冪等性:
  - J-Quants からの保存は ON CONFLICT DO UPDATE を用いて冪等に実行します。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）失敗時は適切にフォールバック（例: macro_sentiment=0.0）し、処理継続可能な設計です。
- セキュリティ:
  - news_collector は SSRF 対策や XML の安全パース（defusedxml）を実施しています。
- レート制御:
  - J-Quants は 120 req/min を想定し、内部で固定間隔スロットリングしているため過剰な呼び出しに注意。

---

## 開発 / テストのヒント

- .env の自動読み込みを無効化してテストしたい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- OpenAI 呼び出し部分は内部で関数を分離しており、テスト時に unittest.mock.patch で置き換えやすい設計です（例: kabusys.ai.news_nlp._call_openai_api）。
- DuckDB を ":memory:" で使えば単体テストが容易です。

---

README に記載した内容はコードの現状に基づくサマリです。各関数・モジュールの詳細な使い方はソースの docstring を参照してください。必要であれば実際の利用シナリオ（ETL 定期実行、戦略→発注フロー例など）を追加で作成します。