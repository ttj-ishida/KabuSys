# KabuSys

KabuSys は日本株のデータプラットフォームおよび自動売買／リサーチ用ライブラリです。  
J-Quants や RSS/ニュース、OpenAI（LLM）を組み合わせてデータ収集・品質チェック・AI 評価・ファクター計算・監査ログの管理を行うことを目的としています。

バージョン: 0.1.0

---

## 主要機能

- データ取得（J-Quants API）
  - 日次株価（OHLCV）
  - 財務データ（四半期）
  - JPX マーケットカレンダー
  - 上場銘柄一覧
  - レート制限・トークン自動リフレッシュ・リトライ対応

- ETL パイプライン
  - 差分取得（バックフィル含む）
  - 冪等保存（DuckDB への ON CONFLICT 処理）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- ニュース収集 & NLP
  - RSS フィード取得（SSRF 対策、gzip 制限）
  - テキスト前処理
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメントのバッチスコアリング（ai_scores テーブル）

- 市場レジーム判定（regime_detector）
  - ETF (1321) の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジームを判定
  - レートリトライ / フェイルセーフ実装

- リサーチ用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility / Liquidity）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Z-score 正規化ユーティリティ

- 監査ログ（Audit）
  - シグナル → 発注 → 約定までトレース可能な監査テーブル定義と初期化ユーティリティ
  - DuckDB ベースでの冪等な初期化

- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルートを検出）
  - 必須設定の検証

---

## 必要条件（主要な依存）

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- その他：標準ライブラリ（urllib, json, datetime 等）

（プロジェクトに requirements.txt / pyproject を追加している場合はそちらを使ってください）

簡単なインストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要なパッケージを手動でインストール
pip install duckdb openai defusedxml
# パッケージを編集可能インストール（リポジトリルートで）
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動します。

2. 仮想環境を作成して依存をインストールします（上記参照）。

3. 環境変数（または .env ファイル）を用意します。最低限必要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード（該当機能を使う場合）
- SLACK_BOT_TOKEN: Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
- KABUSYS_ENV: development | paper_trading | live（省略時は development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（省略時 INFO）
- DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（省略時 data/monitoring.db）

例: `.env`（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

自動 .env ロードはデフォルトで有効です。無効にするには環境変数で:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（主要ユースケース）

下記は主要 API の簡単な利用例です。DuckDB 接続は `duckdb.connect(path)` を使用します。

- 日次 ETL 実行（株価・財務・カレンダーの差分 ETL と品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {n_written} codes")
```

- 市場レジームスコア算出（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- ファクター計算 / リサーチユーティリティ
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))

# Z-score 正規化
znormed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

- 監査ログスキーマの初期化 / 監査用 DB 作成
```python
from kabusys.data.audit import init_audit_db, init_audit_schema
conn = init_audit_db("data/audit.duckdb")
# あるいは既存の DuckDB 接続へ追加:
# init_audit_schema(existing_conn, transactional=True)
```

- RSS フィードの取得（ニュース収集の内部ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

---

## 設定のポイント / 注意事項

- OpenAI コールは API の失敗（5xx、タイムアウト、レート制限）に対してリトライ／フォールバックする実装があります。API キーが無い場合、多くの AI 機能は ValueError を投げます。
- ETL 系は DuckDB を想定しています。デフォルト DB パスは `data/kabusys.duckdb`。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行われます。CI やテストで自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API の利用はレート制限（120 req/min）に準拠します。内部で固定間隔の RateLimiter を使用しています。
- DuckDB の executemany に関する制約（空リストを渡せない等）に配慮した実装になっています。
- ニュース収集では SSRF / GzipBomb 対策（リダイレクト検証、プライベートアドレス検出、受信サイズ制限）を実装しています。

---

## ディレクトリ構成（主要ファイル）

以下は主要なモジュールとその責務の一覧です（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env の読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM スコアリング（ai_scores へ書き込み）
    - regime_detector.py  — 市場レジーム判定（ma200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch / save 等）
    - pipeline.py         — ETL パイプライン（run_daily_etl 他）
    - etl.py              — ETLResult の再エクスポート
    - news_collector.py   — RSS フィード収集、前処理
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - audit.py            — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank

（上記以外に strategy / execution / monitoring などのパッケージが想定されるが、このコードベースでは主に data / ai / research が実装されています）

---

## 開発・テストに関するヒント

- テスト時に外部 API 呼び出しを避けるため、各所で OpenAI や urllib の呼び出しをモックしやすい設計（関数分離）がされています。例:
  - kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替え
  - kabusys.data.news_collector._urlopen をモックしてネットワークを隔離

- 自動 .env ロードを無効化して明示的に設定を注入する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット。

---

## トラブルシューティング

- 環境変数が足りない / 必須キー未設定の場合、Settings のプロパティ（例: settings.jquants_refresh_token）が ValueError を投げます。README の「必要な環境変数」を確認してください。
- OpenAI レスポンスのパースに失敗したり API が利用不可の場合、ai モジュールはフェイルセーフで 0 や空辞書を返す設計です（例外を投げず継続する箇所が多い）。
- DuckDB の接続や SQL エラーはスタックトレースに出ます。スキーマが足りない場合は audit.init_audit_schema 等で初期化してください。

---

必要であれば、README にサンプル .env.example、requirements.txt、あるいは CI ワークフローの例（ETL を cron/airflow で定期実行する手順）を追加できます。どの内容を追加しますか？