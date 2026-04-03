# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリ群です。  
J-Quants / DuckDB を用いたデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ（ファクター計算）や監査ログ（発注→約定追跡）などを提供します。

---

## 概要

KabuSys は次の目的を持つモジュール群です。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL。
- RSS ニュース収集と OpenAI を用いたニュースセンチメント（銘柄ごと）スコアリング。
- ETF（1321）を用いた市場レジーム判定（MA200 乖離 + マクロ記事センチメント）。
- ファクター（モメンタム／バリュー／ボラティリティ等）計算、将来リターンや IC 計算などのリサーチ機能。
- データ品質チェック、監査ログテーブルの初期化ユーティリティ。
- J-Quants クライアント（レート制限・リトライ・トークン自動リフレッシュ付き）。
- 設定管理（.env 自動読み込み含む）。

パッケージ名: `kabusys`（ソースは `src/kabusys`）

---

## 主な機能一覧

- data
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - J-Quants クライアント（fetch/save）
  - 市場カレンダー管理（営業日判定、next/prev など）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（signal / order_request / executions テーブル）
  - 汎用統計ユーティリティ（Z-score 正規化）
- ai
  - ニュース NLP（銘柄ごとの ai_score を生成して `ai_scores` に書き込む）
  - レジーム判定（ETF 1321 の ma200 乖離 + マクロ記事の LLM センチメント）
- research
  - ファクター計算（momentum, value, volatility 等）
  - 将来リターン計算、IC / 統計サマリー、ランク関数
- config
  - .env / 環境変数の読み込み、自動ロード（プロジェクトルート検出）
  - 主要設定（J-Quants トークン、OpenAI、DB パス、監視閾値 等）

---

## 前提（Prerequisites）

- Python 3.10 以上（型注釈の union 文法等を使用）
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、プロジェクトルートへ移動します。
2. 仮想環境を作成・有効化します（例: venv）。
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストールします（例）:
   ```bash
   pip install duckdb openai defusedxml
   ```
4. パッケージを編集モードでインストール（任意）:
   ```bash
   pip install -e .
   ```
5. 環境変数を設定します。プロジェクトルートに `.env` として保存することが推奨されます。自動読み込みは OS 環境変数 > `.env.local` > `.env` の優先順位で行われます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

サンプル `.env`（最低限の必須キー）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須：J-Quants のリフレッシュトークン）
- OPENAI_API_KEY（AI 機能を使う場合に必須）
- KABU_API_PASSWORD（kabu ステーション API のパスワード）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロードを無効化）

---

## 使い方（主要な利用シーン例）

以下はいくつかの代表的な使い方例です。実行は Python REPL、スクリプト、ジョブスケジューラから可能です。

- DuckDB 接続の準備（settings に従ったパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI APIキーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用途）
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 監査ログ（audit）テーブル初期化（別 DB ファイルで運用可能）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等が作成される
```

- J-Quants から生データ取得（テストやカスタム取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

rows = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 自動設定読み込みの挙動

- パッケージ import 時（kabusys.config）にプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探索し、`.env` と `.env.local` を自動的に読み込みます。
- 読み込み優先順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト目的等）。

---

## ディレクトリ構成（主なファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義（公開モジュール一覧）
  - config.py — 環境変数・設定管理、.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py — ニュース集約・OpenAI を用いた銘柄別スコアリング（ai_scores への書き込み）
    - regime_detector.py — 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロ記事センチメント）
  - data/
    - __init__.py
    - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult 定義
    - etl.py — ETLResult の再エクスポート
    - jquants_client.py — J-Quants API 呼び出し / 保存ユーティリティ（rate limiting, retry, token refresh）
    - news_collector.py — RSS 取得・前処理・raw_news 保存（SSRF対策・XML防御）
    - calendar_management.py — market_calendar 管理、営業日判定・next/prev/get
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログスキーマの定義・初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC・rank・summary 等
  - monitoring / execution / strategy / その他（パッケージ API 表示のためトップレベル __all__ に含まれる想定モジュール）

（上記はコードベースから抽出した主要モジュールの一覧です。実際のリポジトリではさらに補助モジュールが存在する可能性があります。）

---

## 注意事項 / ベストプラクティス

- AI 機能（news_nlp / regime_detector）は OpenAI API を使用します。API キーと利用料金に注意してください。API 呼び出しはリトライ／フェイルセーフを備えていますが、コストとレイテンシを考慮してください。
- ETL は差分取得を前提としています。初回ロード時には `DUCKDB_PATH` 内に適切なスキーマ（raw_prices/raw_financials等）を用意してください。schema の初期化手順はプロジェクトのドキュメントに従ってください（schema 初期化用ユーティリティが別途ある想定）。
- ローカルテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと .env 自動読み込みを無効化できます。
- DuckDB の executemany に対する制約（空リストが渡せない等）や、J-Quants のレート制限（120 req/min）に合わせた実装上の考慮がコード内に反映されています。カスタム実行時はこれらを尊重してください。
- production 環境では `KABUSYS_ENV=live` を設定し、ログレベルや監視閾値 （CPU/MEM/DISK）を適切に構成してください。

---

もし README に追加したい具体的なインストール手順（pyproject/requirements）、スキーマ初期化方法、使用例スクリプト、あるいは .env.example のフルテンプレートがあれば、それに合わせたサンプルを追記します。どの情報を優先して詳述しますか？