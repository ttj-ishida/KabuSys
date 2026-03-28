# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤のコアライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集／NLP（OpenAI を利用した記事センチメント）、ファクター計算、監査ログ（発注〜約定のトレース）、カレンダ管理などを含みます。

主な用途
- J-Quants API からの株価・財務・カレンダーの差分 ETL
- RSS ベースのニュース収集と LLM による銘柄センチメント算出
- 市場レジーム判定（MA200 とマクロニュースの合成）
- 研究用ファクター計算・特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution）の DB スキーマ初期化

---

## 機能一覧（抜粋）

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須キー未設定時のエラー報告
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: market_calendar / raw_prices / raw_financials の差分取得・保存・品質チェック
  - J-Quants クライアント（jquants_client）: レート制限・リトライ・トークン自動リフレッシュ対応
- ニュース収集（kabusys.data.news_collector）
  - RSS の取得、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存設計
- ニュース NLP（kabusys.ai.news_nlp）
  - gpt-4o-mini を用いた銘柄ごとのセンチメントスコア算出（JSON Mode）
  - バッチ・リトライ・バリデーション実装
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離 + マクロニュースセンチメントで 'bull'/'neutral'/'bear' を判定
- 研究用ユーティリティ（kabusys.research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化等
- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - Signal / OrderRequest / Execution の冪等・トレース可能なスキーマ定義と初期化ユーティリティ

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API / OpenAI / RSS フィード 等へ接続可能であること

（プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを優先してください）

---

## セットアップ手順

1. レポジトリをチェックアウト（通常はパッケージ配下は `src/kabusys`）  
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （開発向け）pip install -e . など
4. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）
   - 必須（例）
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...   ← news_nlp / regime_detector が参照
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
5. DuckDB の初期スキーマや監査スキーマを作成したい場合は、接続して init を呼ぶ（例は下に記載）

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（よく使う API / 実行例）

以下は基本的な使用例です。実際にはログ設定やエラーハンドリングを付与してください。

- DuckDB 接続を作成して ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア算出（日次）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n_written} codes")
```

- 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB 初期化（別ファイルに監査用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を運用に使用
```

- RSS フィード取得（単体ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点
- OpenAI クライアント呼び出しは API キー（OPENAI_API_KEY）を必要とします。score_news / score_regime は引数で api_key を渡すこともできます（テストでの差し替えが可能）。
- ETL・API 通信部分はリトライ・レート制限等を実装していますが、ネットワーク環境や API 制限に注意してください。
- すべての処理は「ルックアヘッドバイアス防止」を前提に設計されています（内部で date.today() を参照せず、target_date を明示して処理する等）。

---

## ディレクトリ構成（主要ファイル）

(パッケージルート: src/kabusys)

- kabusys/
  - __init__.py
  - config.py                       — .env / 環境変数管理（自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースの LLM スコアリング（銘柄別）
    - regime_detector.py             — 市場レジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult のエクスポート
    - news_collector.py              — RSS 取得・前処理・SSRF 対策
    - calendar_management.py         — 市場カレンダー管理 / 営業日判定
    - quality.py                     — データ品質チェック
    - stats.py                       — Zスコア等の統計ユーティリティ
    - audit.py                       — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py             — momentum/value/volatility 等
    - feature_exploration.py         — forward returns / IC / summary
  - ai/, data/, research/ などのテスト用モックを用意して単体テストを行う想定

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（実行環境依存）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須 if Slack 通知)
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)
- SQLITE_PATH (任意, default: data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live) — 実行環境
- LOG_LEVEL (DEBUG|INFO|...) — ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動ロードを無効化（テスト用）

config.py がプロジェクトルート（.git or pyproject.toml を含むディレクトリ）を自動検出して .env / .env.local を読み込みます。

---

## ログと監視

- 各モジュールは標準 logging を利用しており、LOG_LEVEL 環境変数で制御します。
- ETLResult / QualityIssue を使って品質チェック結果や ETL の概要を外部監査や通知に利用できます。

---

## 開発・テストのヒント

- OpenAI / ネットワーク呼び出し部分は内部でヘルパー関数を分離してあるため、unittest.mock.patch により簡単に差し替えてテスト可能です（例: kabusys.ai.news_nlp._call_openai_api のモック）。
- .env の自動読み込みがテストの邪魔になる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB をインメモリで使えばテストが容易です: duckdb.connect(":memory:")

---

疑問点や README に追加したい内容があれば教えてください。必要であればサンプルスクリプトや運用手順（cron / Airflow / systemd での実行例）を追記します。