# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys のリポジトリ用 README（日本語）

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 簡単な使い方（コード例）
  - ETL（日次データパイプライン）
  - ニュースの NLP スコアリング
  - 市場レジーム判定
  - 研究用ファクター計算
  - 監査テーブル初期化
- 環境変数（主要）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータプラットフォーム向けの Python パッケージ群です。  
主に次を目的としています：

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- ETL パイプライン（差分取得・保存・品質チェック）
- ニュース収集・NLP（OpenAI を用いた銘柄ごとのセンチメントスコアリング）
- 市場レジーム判定（ETF の MA とマクロニュースの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算 など）
- 監査ログ（signal → order → execution のトレーサビリティ用スキーマ）
- DuckDB を中心としたデータ保存と分析

設計上、ルックアヘッドバイアスを避けるため「現在時刻」を安易に参照しないように実装されており、ETL やスコアリングは明示的な target_date を受け取ることで過去データのみを参照できます。

---

## 主な機能

- data:
  - J-Quants クライアント（認証・ページネーション・再試行・レート制限対応）
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - カレンダー管理（営業日判定・next/prev_trading_day 等）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - ニュース収集（RSS -> raw_news 用ユーティリティ）
  - 監査ログ初期化（監査用テーブル群の作成）
  - 統計ユーティリティ（Zスコア正規化）
- ai:
  - ニュース NLP: 銘柄別ニュースから ai_scores を生成（OpenAI）
  - レジーム判定: ETF（1321）MA とマクロニュースによる市場レジーム判定
- research:
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクターサマリー
- config:
  - 環境変数の自動読み込み（プロジェクトルートの `.env`, `.env.local`）
  - 設定ラッパ（settings）

---

## セットアップ手順

※ この README はパッケージ内の実装から推測した一般的なセットアップ手順を示します。実際のプロジェクトに合わせて要調整してください。

1. Python 環境
   - 推奨: Python 3.10+（Typing の union 型や型注釈を使用）
   - 仮想環境を作成して有効化してください（venv / conda 等）

2. 依存パッケージのインストール（例）
   - 必要な主なライブラリ:
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     ```
     pip install duckdb openai defusedxml
     ```
   - （プロジェクトで requirements.txt / pyproject.toml がある場合はそちらを利用してください）

3. パッケージのインストール（開発時）
   - リポジトリルートで:
     ```
     pip install -e .
     ```
     あるいはプロジェクトのインストール手順に従ってください。

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須（基本的に）:
     - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
     - OPENAI_API_KEY（OpenAI を利用する場合）
     - KABU_API_PASSWORD（kabu ステーション API を使う場合）
   - その他（省略時にはデフォルトが使われる／任意）:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）

5. データディレクトリの作成
   - デフォルトでデータファイルは `data/` 配下に作られます。必要に応じてディレクトリを作成してください:
     ```
     mkdir -p data
     ```

---

## 使い方（よく使う処理の例）

下記コードはパッケージをインポートして機能を呼び出す簡単な例です。実運用ではログ設定や例外処理、スケジューラなどを組み合わせてください。

- 事前: DuckDB 接続を作る（デフォルト path は settings.duckdb_path）

```python
from pathlib import Path
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
db_path = settings.duckdb_path
db_path.parent.mkdir(parents=True, exist_ok=True)
conn = duckdb.connect(str(db_path))
```

### 日次 ETL を実行する

run_daily_etl は ETL のエントリポイントです。target_date を与えなければ今日の ETL を行います（内部は営業日調整あり）。

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

### ニュースをスコアリングして ai_scores に保存する（OpenAI 必須）

OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定します。

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date に対して前日15:00 JST ～ 当日08:30 JST の記事を評価
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote scores for {n_written} codes")
```

### 市場レジーム判定（ETF 1321 の MA とマクロニュースを統合）

```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

### 研究用ファクター計算の呼び出し例

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize
from datetime import date

target = date(2026, 3, 20)
momentum = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
value = calc_value(conn, target)

# z-score 正規化（例）
normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

### 監査（audit）テーブルの初期化

監査用の DuckDB を初期化してテーブル群を作成します。トランザクションを使って一括で初期化されます。

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査ログを保存できます
```

### RSS フィードを取得する（ニュース収集ユーティリティ）

news_collector.fetch_rss を使って記事一覧（NewsArticle）を取得できます。取得した記事の保存ロジックは実装環境に合わせて設計してください。

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:3]:
    print(a["datetime"], a["title"])
```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client.get_id_token で ID トークンを取得するために使用します。

- OPENAI_API_KEY (必要に応じて)  
  OpenAI を利用する機能（news_nlp, regime_detector）を使う場合に必要。

- KABU_API_PASSWORD (必要に応じて)  
  kabu ステーション API を使う場合のパスワード。

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト "http://localhost:18080/kabusapi"）。

- DUCKDB_PATH (任意)  
  DuckDB のデフォルトファイルパス（デフォルト "data/kabusys.duckdb"）。

- LOG_LEVEL (任意)  
  ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)。デフォルト INFO。

- KABUSYS_ENV (任意)  
  環境識別: development / paper_trading / live（デフォルト development）。settings.is_live / is_paper で利用。

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを抑止できます（テスト等で便利）。

.env ファイルのパースはかなり柔軟です（export 形式、クォート、コメント処理などをサポート）。

---

## 注意事項 / 補足

- DuckDB のバージョン差異や executemany の仕様によりコード内で互換性対策が入っています（例: 空リストの executemany は回避）。
- J-Quants API 呼び出しはレート制限・リトライ・401 リフレッシュ等のロジックが実装されていますが、実デプロイではトークン管理や監視が必要です。
- OpenAI 呼び出しは JSON Mode（厳密な JSON 出力）を期待しており、リトライ・パース失敗時はフェイルセーフとして 0.0 を返す実装が多いです。
- news_collector は SSRF 保護や XML の安全パース（defusedxml）等セキュリティ対策を施しています。

---

## ディレクトリ構成（抜粋）

以下はパッケージ内の主なモジュールとファイルの一覧（presented tree の要約）:

- src/kabusys/
  - __init__.py
  - config.py                 ← 環境変数読み込み・settings
  - ai/
    - __init__.py
    - news_nlp.py             ← ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      ← 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       ← J-Quants API クライアント（取得＋保存）
    - pipeline.py             ← ETL パイプライン（run_daily_etl 等）
    - etl.py                  ← ETLResult の再エクスポート
    - calendar_management.py  ← マーケットカレンダー管理
    - news_collector.py       ← RSS 収集・前処理
    - quality.py              ← データ品質チェック
    - stats.py                ← 統計ユーティリティ（zscore_normalize）
    - audit.py                ← 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py      ← モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py  ← 将来リターン / IC / ファクター統計
  - monitoring/                ← （README に出てくるが省略・監視関連想定）
  - strategy/                  ← （戦略層: シグナル生成等、リポジトリに応じて実装）

（上記はリポジトリの一部モジュールを抜粋したものです。実際のファイルはプロジェクトルートを参照してください）

---

必要であれば、README に以下の追加情報も作成できます：
- requirements.txt / pyproject.toml の推奨内容
- 具体的な DB スキーマ定義（raw_prices, raw_financials, raw_news, ai_scores 等）
- CI / デプロイ手順（ETL のスケジューリング、監視、ログの収集）
- 開発時のユニットテスト方針やモック方法（OpenAI / J-Quants の外部呼び出しのモック）

ほかに README に入れたい具体的な内容（例: サンプル .env.example、起動用 CLI、SQL スキーマの抜粋など）があれば指示してください。