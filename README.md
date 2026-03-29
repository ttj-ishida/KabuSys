# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
OTC データ取得（J-Quants）、DuckDB を用いたデータ格納、ニュース収集・NLP（OpenAI）、ファクター計算・リサーチ、監査（オーディット）などのコンポーネントを含みます。

本 README はコードベース（src/kabusys）に基づく概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

注意: ここで示す手順・環境変数名はソース内の実装に基づいています。実運用前に .env.example を確認し、必要に応じて調整してください。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要ユースケースの例）
- 環境変数一覧（必須／推奨）
- ディレクトリ構成
- テスト／開発上の注意点

---

## プロジェクト概要

KabuSys は日本株向けに設計されたデータプラットフォーム兼リサーチ／自動売買支援ライブラリです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（取得・保存・品質チェック）
- RSS ベースのニュース収集と前処理、記事→銘柄の紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント分析（銘柄単位）およびマクロセンチメント合成による市場レジーム判定
- DuckDB を用いたローカルデータストア（raw_prices / raw_financials / market_calendar / raw_news / ai_scores / ...）
- 監査ログ（signal_events / order_requests / executions）用スキーマの自動初期化
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、正規化など）

設計上の特徴:
- ルックアヘッドバイアス防止（target_date を明示、datetime.today() を直接参照しない）
- ETL は差分取得・バックフィルをサポートし冪等保存（ON CONFLICT）
- API 呼び出しにはリトライとレート制御を実装
- 外部 API キーは環境変数または .env で管理（自動読み込み機能あり）

---

## 機能一覧

主要コンポーネントと機能（抜粋）:

- config: 環境変数・設定読み込み（.env / .env.local 自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- data:
  - jquants_client: J-Quants API クライアント（トークン管理、ページング、保存関数）
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL ジョブ（run_prices_etl 等）
  - news_collector: RSS 収集・前処理・SSRF 対策・抜粋保存ロジック
  - calendar_management: JPX カレンダーの管理、営業日判定ユーティリティ
  - quality: データ品質チェック（欠損、スパイク、重複、日付整合性）
  - audit: 監査ログスキーマ初期化・監査 DB 作成ユーティリティ
  - stats: z-score 正規化など統計ユーティリティ
- ai:
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF(1321)の MA 乖離とマクロ記事の LLM センチメントを合成して market_regime を更新
- research:
  - factor_research: momentum, value, volatility などのファクター計算
  - feature_exploration: 将来リターン算出、IC、統計サマリー、ランク関数等

---

## セットアップ手順

前提:
- Python 3.9+（ソースは型注釈: Python 3.10 以上を想定している箇所がありますが、3.9+ で問題ない場合があります）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン / ファイルを配置
   (プロジェクトルートが .git または pyproject.toml によって自動検出されます)

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   - 開発・追加機能によっては他パッケージ（slack-sdk など）が必要になる場合があります。

   プロジェクトを編集可能インストール:
   ```
   pip install -e .
   ```
   ※ pyproject / setup が用意されている場合は上記で依存関係も解決できます。

4. 環境変数 / .env の準備
   - プロジェクトルートに .env を作成することで設定が自動読込されます（.env.local があれば優先）。
   - 自動読込を無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

   代表的な環境変数（詳細は下の節「環境変数一覧」参照）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB 初期化（監査スキーマなど）
   - 監査ログ用 DB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   - または既存の DuckDB 接続を渡して init_audit_schema(conn) を呼ぶ。

---

## 使い方（主要ユースケースの例）

以下は代表的な API の利用例です。実行はプロジェクトルートから行ってください。

- 共通設定取り出し:
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB に接続して日次 ETL を実行:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメントを作成して ai_scores に書き込む:
```python
import os
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください
n = score_news(conn, target_date=date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))
print(f"scored {n} symbols")
```

- 市場レジーム（1321 + マクロニュース）を判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=os.environ.get("OPENAI_API_KEY"))
```

- 監査ログ（audit）スキーマ初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # 監査用 DB を作成・スキーマ適用して接続を返す
```

- RSS フィード取得（ニュースコレクタの低レベル関数）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a['id'], a['datetime'], a['title'])
```

- 研究ユーティリティ（ファクター算出等）例:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

---

## 環境変数（必須 / 推奨）

ソース内で参照されている主要な環境変数を列挙します。運用環境では必須のものがあります。

必須（機能を使う場合）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_tokenで使用）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注等に必要）
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: Slack チャネル ID

任意 / 推奨:
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development, paper_trading, live） デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL） デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（値が存在すれば無効）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要なモジュールとファイル（抜粋）です。実際のプロジェクトではさらにファイルが含まれる場合があります。

- src/kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                # ニュースセンチメント（score_news）
    - regime_detector.py         # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント、保存関数
    - pipeline.py                # ETL パイプライン（run_daily_etl 等）
    - news_collector.py          # RSS 収集・前処理
    - calendar_management.py     # 市場カレンダー管理・営業日判定
    - quality.py                 # データ品質チェック
    - audit.py                   # 監査ログスキーマの作成・初期化
    - stats.py                   # 汎用統計ユーティリティ（zscore_normalize）
    - etl.py                     # public re-export (ETLResult)
  - research/
    - __init__.py
    - factor_research.py         # Momentum / Value / Volatility ファクター
    - feature_exploration.py     # forward returns, IC, rank, summary
  - research/... (その他の研究用ユーティリティ)

---

## テスト／開発上の注意点

- 自動 .env 読み込み:
  - config._find_project_root() によりプロジェクトルートが特定されると、.env / .env.local が自動で読み込まれます。
  - テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして自動ロードを抑止できます。

- OpenAI 呼び出しのモック:
  - テスト時は kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch して差し替えることを想定しています（外部 API 呼び出しの差し替えが容易な実装になっています）。

- ルックアヘッドバイアス:
  - 多くの関数は target_date を明示的に受け取り、内部で datetime.today() を直接参照しない設計です。バックテスト時は target_date を明示してください。

- DuckDB executemany の注意:
  - DuckDB（特に v0.10 系）では executemany に空リストを渡すとエラーになる場合があるため、コード内で空判定を行ってから実行しています。直接使う場合も同様の配慮をしてください。

- API レート制御 / リトライ:
  - jquants_client は固定間隔スロットリング（120 req/min）と指数バックオフを実装しています。過度な同時実行は避けてください。

---

## 最後に

この README はソースコード（src/kabusys）から抽出した情報をまとめたものです。運用環境で使用する際は、各モジュールの詳細ドキュメント・ログ・例外処理フローをさらに確認し、必要に応じてテストと監査を行ってください。追加の README セクションや運用手順（cron ジョブ、コンテナ化、監視など）が必要であれば教えてください。