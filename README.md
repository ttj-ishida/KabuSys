# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリコレクションです。  
ETL（J-Quants からの市場データ取得）、ニュース収集・AI スコアリング、ファクター計算、監査ログ等を一貫して提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を提供する Python パッケージ群です。

- J-Quants API からの差分 ETL（株価日足・財務・市場カレンダー）
- DuckDB を用いたデータ保存・品質チェック
- ニュース収集（RSS）と LLM を使ったニュースセンチメント分析（OpenAI）
- 市場レジーム判定（MA とマクロニュースの組合せ）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、IC 解析 等）
- 監査ログ（signal → order_request → executions）のためのスキーマ初期化・ユーティリティ
- 各種ユーティリティ（カレンダー管理、統計正規化、データ品質チェック 等）

設計方針として、バックテストでのルックアヘッドバイアス排除を重視し、API 呼び出し失敗時はフェイルセーフで継続する実装になっています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API からの取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info）
  - DuckDB への冪等保存（save_*）
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- data.pipeline
  - 日次 ETL 実行エントリ（run_daily_etl）と個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果を ETLResult として返す
- data.news_collector
  - RSS 収集、前処理、raw_news への保存
  - SSRF / 大容量レスポンス等のセキュリティ対策実装
- ai.news_nlp / ai.regime_detector
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄ごと）と市場レジーム判定
  - レスポンス検証・リトライ・フェイルセーフ設計
- research.*
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary）
  - zscore_normalize（data.stats）
- data.quality
  - 欠損・スパイク・重複・将来日付・非営業日データ検出
- data.audit
  - 監査ログ用テーブル定義、初期化ユーティリティ（init_audit_schema / init_audit_db）
- config
  - .env または OS 環境変数を自動読み込み（プロジェクトルート検出）
  - settings オブジェクトから各種設定にアクセス可能

---

## 必要要件 / 依存パッケージ（代表的なもの）

- Python 3.9+
- duckdb
- openai (openai の新しい SDK を想定)
- defusedxml
- そのほか標準ライブラリ（urllib 等）

※ 実際の依存関係は setup/pyproject の定義に従ってください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate    # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストールします（例）:

   ```
   pip install -r requirements.txt
   ```

   （requirements.txt が無い場合は上記の代表パッケージを個別にインストールしてください）

3. 環境変数を設定します。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必要）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - LOG_LEVEL: ログレベル（例: INFO）
   - KABUSYS_ENV: development / paper_trading / live

   例 .env（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要なユースケース例）

以下は Python インタプリタやスクリプトから利用する例です。

1) 設定読み込み

```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.env)
```

2) DuckDB に接続して日次 ETL を実行（J-Quants トークンは settings から自動使用）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントを生成して ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で使う
print(f"書き込み銘柄数: {written}")
```

4) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ用 DuckDB を初期化して接続を取得

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
```

6) ファクター計算・研究用ユーティリティ

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意:
- ai モジュールは OpenAI API を呼ぶため、API キーの管理とリクエストコストに注意してください。
- テスト時は各モジュールで OpenAI 呼び出しをモックすることが想定されています（コード内に差し替えポイントあり）。

---

## .env 自動読み込みの挙動

- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` → `.env.local` の順で読み込みます。
- 既存の OS 環境変数は上書きされませんが、`.env.local` は `.env` の値を上書きします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py  (パッケージエクスポート)
  - config.py    (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py         (ニュースセンチメント解析、ai_scores 書き込み)
    - regime_detector.py  (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント、保存関数)
    - pipeline.py         (ETL パイプライン、run_daily_etl)
    - etl.py              (ETLResult 再エクスポート)
    - news_collector.py   (RSS 収集・前処理)
    - calendar_management.py (市場カレンダー管理)
    - stats.py            (zscore_normalize 等)
    - quality.py          (データ品質チェック)
    - audit.py            (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py  (モメンタム/バリュー/ボラティリティ)
    - feature_exploration.py (forward returns, IC, summary, rank)
  - ai/regime_detector.py, ai/news_nlp.py などは OpenAI 呼び出しや JSON パースの堅牢化、リトライ処理を含む

---

## 注意点 / 実運用上のポイント

- Look-ahead Bias の排除: 多くの関数は明示的に target_date を受け取り、datetime.today() に依存しないよう設計されています。バックテストで使用する際は利用開始日以前のデータが DB に存在することを確認してください。
- OpenAI 呼び出しや外部 API 呼び出しはコスト・レート制限の影響を受けます。ログやリトライ設定、バッチサイズは環境に応じて調整してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックが行われています。DuckDB バージョンと互換性に注意してください。
- ニュース収集での RSS フィード解析は外部 URL 取得を行うため、SSRF・大容量応答の防御が実装されています。追加のフィードを登録する際はソースの信頼性を確認してください。

---

## 貢献 / テスト

- 各 API 呼び出しやネットワーク関連はモックしやすい設計になっています（内部の _call_openai_api / _urlopen 等をパッチすることを想定）。
- ユニットテストでは環境変数の自動読み込みを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用すると安定します。

---

この README はコードベースの主要機能をまとめた簡易ドキュメントです。各モジュールの詳細はソースコードのドクストリングに記載された処理フロー・設計方針を参照してください。質問や補足があれば教えてください。