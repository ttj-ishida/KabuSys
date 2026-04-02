# KabuSys

KabuSys は日本株のデータパイプライン、機械学習/LLM ベースのニュース分析、リサーチ用ファクター計算、監査ログや ETL を統合した自動売買支援ライブラリです。DuckDB をデータレイヤに使用し、J-Quants API / RSS / OpenAI（Chat API）などと連携してデータ収集・品質チェック・特徴量生成・市場レジーム判定を行います。

## 主な特徴
- データ ETL
  - J-Quants API から株価（日足）、財務、マーケットカレンダーを差分取得して DuckDB に保存（冪等保存）
  - ETL の品質チェック（欠損、重複、スパイク、日付整合性）
- ニュース収集と NLP（LLM）
  - RSS から記事取得、前処理、raw_news/ news_symbols への保存
  - OpenAI (gpt-4o-mini) を用いた銘柄ごとのニュースセンチメント算出（ai_scores テーブルへ書き込み）
  - マクロニュースと ETF の MA 乖離を合成した市場レジーム判定（bull/neutral/bear）
- リサーチユーティリティ
  - モメンタム／バリュー／ボラティリティ等ファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Z スコア正規化
- 監査（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマを DuckDB に初期化
  - 発注フローを UUID 連鎖で追跡可能にする設計
- 安全性・耐障害設計
  - API リトライ・バックオフ、レート制御、SSRF 対策、XML パースの安全化（defusedxml）などを実装
  - ルックアヘッドバイアス対策（内部で date.today() を直接参照しない設計の箇所あり）

---

## 依存関係（代表例）
実行に必要な主要ライブラリ（バージョンはプロジェクト方針に合わせてください）。
- Python 3.10+
- duckdb
- openai
- defusedxml

（パッケージ化時は requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境の作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   ※プロジェクトに pyproject.toml / requirements.txt がある場合はそれを利用してください。

3. ソースをインストール（開発モード）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` および（必要なら）`.env.local` を配置すると自動で読み込まれます。
   - 自動読み込みを無効化する場合：
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例 `.env`（必須値の例）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI (API キーは必須: news_nlp / regime_detector で使用)
OPENAI_API_KEY=sk-...

# kabuステーション (実運用がある場合)
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB / 監視パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: `kabusys.config.Settings` はいくつかのプロパティに対して必須の環境変数を期待します（不足時は ValueError を発生させます）。主な必須キー：
- JQUANTS_REFRESH_TOKEN
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- （必要に応じ）OPENAI_API_KEY

---

## 使い方（代表的な API） — Python スニペット

以下は主要機能の利用例です。DuckDB 接続は duckdb.connect("path/to.db") を使います。

1) 日次 ETL 実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントスコア付与（ai_scores への書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

3) 市場レジーム判定（ETF 1321 とマクロニュースの合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) ニュース RSS 取得（単体テストや収集用）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"], a["url"])
```

5) 監査テーブル初期化（監査 DB を別ファイルで用意する例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

6) ファクター計算（Research）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

---

## 設計上の注意点 / 実運用での留意点
- 多くの処理は「ルックアヘッドバイアス」を避けるため内部で date.today() を直接参照しない設計になっています。ETL やスコア算出の基準日は引数で明示してください。
- OpenAI 呼び出しはリトライやフォールバック（失敗時は中立スコア）を組み込んでいますが、API 使用量と課金に注意してください。
- J-Quants API にはレート制限があるため、jquants_client はレート制御とリトライを行います。ただし大量の同時実行は避けてください。
- news_collector は SSRF・大容量レスポンス対策・XML 安全化などに配慮して実装されています。独自の RSS ソースを追加する場合は URL の正規化やホストの妥当性に注意してください。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py  — 環境変数・設定管理（.env 自動読み込みロジック等）
- ai/
  - __init__.py
  - news_nlp.py         — ニュース NLP / OpenAI 呼び出し / ai_scores 書き込み
  - regime_detector.py  — マクロ + ETF MA200 で市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETLResult の再エクスポート
  - jquants_client.py     — J-Quants API 呼び出し + DuckDB 保存
  - news_collector.py     — RSS 取得・前処理・raw_news 保存
  - quality.py            — 品質チェック（欠損・重複・スパイク・日付整合）
  - stats.py              — 統計ユーティリティ（zscore_normalize）
  - audit.py              — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py    — Momentum / Value / Volatility 計算
  - feature_exploration.py— forward returns, IC, factor_summary, rank

（上記は主要なモジュールで、実際のリポジトリにはさらに補助モジュールやテストが含まれることがあります。）

---

## テスト / ローカル開発ヒント
- 自動 .env 読み込みはデフォルトで有効です。ユニットテスト等で環境を固定したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部やネットワーク I/O はモックしやすい設計（_call_openai_api ／ _urlopen の差し替えが可能）になっています。テストでは unittest.mock.patch を利用して外部通信を遮断してください。

---

必要に応じて具体的なユースケース（例えばバッチ化した daily ETL を cron / scheduler で回す例や、Slack 通知の統合方法）を README に追記できます。追記したい運用フローやサンプルを教えてください。