# KabuSys

KabuSys は日本株のデータパイプライン、リサーチ、ニュース NLP、監査ログ、ならびに自動売買のための共通ユーティリティ群を集めたライブラリ／フレームワークです。  
主に以下を目的としています：J-Quants API によるデータ取得と ETL、ニュースを用いた AI ベースのセンチメント計算、市場レジーム判定、監査・トレーサビリティ、研究用ファクター計算など。

バージョン: 0.1.0

---

## 主要な特徴

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - 差分取得・ページネーション・トークン自動リフレッシュ・レート制御・リトライ
  - DuckDB を使った冪等保存（ON CONFLICT / DO UPDATE）

- データ品質管理
  - 欠損・スパイク（急変）・重複・日付不整合のチェック
  - 品質チェックをまとめて実行するユーティリティ

- ニュース収集と NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄レベルのニュースセンチメント算出（ai_scores）
  - マクロニュースと ETF（1321）の MA 乖離を組み合わせた市場レジーム判定（bull/neutral/bear）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ
  - クロスセクション Z-score 正規化ユーティリティ

- 監査ログ（Audit）
  - signal → order_request → execution のトレーサビリティを保存する監査テーブル群
  - 初期化ユーティリティ（DuckDB 接続の初期スキーマ作成）

- カレンダー管理
  - market_calendar テーブルに基づく営業日判定／前後の営業日の取得
  - J-Quants からのカレンダー差分取得ジョブ

---

## 必要条件（概略）

- Python 3.10+
- ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）
- J-Quants のリフレッシュトークン、OpenAI API キー、kabuステーション等の認証情報

適切な仮想環境を作成してからインストールしてください。

例（最低限）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# プロジェクトを editable install する場合（pyproject.toml 等がある想定）
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそれを参照してください）

---

## 環境変数 / 設定

kabusys は .env（および .env.local）と環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テストなどで自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に必要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime 呼び出し時に省略可能だが設定が必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 開発環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

例 .env（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabus_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

.env ファイルは `.env` → `.env.local` の順で読み込まれ、既存の OS 環境変数は保護されます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール（above）
4. プロジェクトルートに .env を作成して必要なキーを設定
5. 初期 DB 構造や監査 DB の初期化（必要に応じて）

監査 DB 初期化の一例（Python）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使ってアプリ処理へ
```

ETL 実行のために DuckDB 接続を用意しておきます:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

---

## 使い方（主要な API と実行例）

以下は主要なユーティリティ関数の利用例です。各関数は DuckDB 接続オブジェクトや日付を引数に取ります。

- 日次 ETL 実行（カレンダー / 株価 / 財務 / 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア取得（ai_scores へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定
print(f"scored {count} codes")
```

- 市場レジーム判定（market_regime へ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査スキーマ初期化（既存接続に対して）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- ファクター計算（研究）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- ニュース RSS の取得（ニュースコレクタのユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
```

注意: OpenAI の呼び出しや J-Quants API 呼び出しは外部 API を使用するため、API キーやトークンの設定、ネットワーク、レート制御を適切に考慮してください。

---

## セキュリティと運用上の注意点

- API キーは必ず安全に管理し、リポジトリに含めないでください。
- J-Quants のレート制限（120 req/min）に配慮した実装になっていますが、運用時は更に監視を行ってください。
- OpenAI へのリクエストはコストが発生するため、バッチサイズや実行頻度に注意してください。
- ニュース取得では SSRF 対策や XML Bomb 対策（defusedxml）を実装していますが、運用環境でも外部 URL の検証やホワイトリスト管理を検討してください。
- DuckDB ファイルは適切にバックアップしてください。監査ログは削除しない運用を想定しています。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主なモジュール構成（src/kabusys 以下）。各モジュールは DuckDB 接続や外部 API のラッパーを提供します。

- src/kabusys/__init__.py
  - パッケージのエクスポート（data, strategy, execution, monitoring）

- src/kabusys/config.py
  - 環境変数と設定の読み込み／検証（Settings）

- src/kabusys/ai/
  - __init__.py
  - news_nlp.py: 記事を集約して OpenAI で銘柄別センチメントを算出し ai_scores に書き込む
  - regime_detector.py: ETF(1321) の MA とマクロニュースを使い市場レジームを判定して market_regime に書き込む

- src/kabusys/data/
  - __init__.py
  - calendar_management.py: 市場カレンダー管理と営業日ユーティリティ
  - etl.py: ETL インターフェース（ETLResult の再エクスポート）
  - pipeline.py: 日次 ETL 実装（prices / financials / calendar、品質チェック統合）
  - stats.py: Zスコア正規化など統計ユーティリティ
  - quality.py: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit.py: 監査ログテーブル定義と初期化ユーティリティ
  - jquants_client.py: J-Quants API クライアント（fetch / save 系関数）
  - news_collector.py: RSS 取得・前処理・保存用ユーティリティ

- src/kabusys/research/
  - __init__.py
  - factor_research.py: モメンタム / ボラティリティ / バリュー ファクター計算
  - feature_exploration.py: 将来リターン / IC / 統計サマリ / ランク変換

（strategy、execution、monitoring パッケージはエントリとして公開されているが、上記のコード一覧に含まれているモジュールが主な実体です。実際の発注ロジックや戦略モデルは別途実装される想定です。）

---

## 開発・テストに関するヒント

- 環境変数の自動ロードは .env / .env.local をプロジェクトルートから読み込みます。ユニットテスト時に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI や外部 API 呼び出し部分は内部で関数化されているため、テスト時は該当関数（例: kabusys.ai.news_nlp._call_openai_api）を patch/mock して置き換えることで外部呼び出しを回避できます。
- DuckDB を用いた単体テストは `:memory:` を渡してメモリ DB を使うと簡便です（例: duckdb.connect(":memory:")）。

---

必要であれば、具体的なセットアップスクリプト、requirements.txt、また実運用向けのデプロイ手順（Dockerfile / systemd ユニット / cron / Airflow など）サンプルも作成します。どの部分を優先して README に追加しますか？