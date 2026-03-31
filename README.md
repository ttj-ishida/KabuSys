# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ KabuSys の README（日本語）

概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量（ファクター）計算、ニュースの NLP スコアリング、ならびに市場レジーム判定や監査ログ用スキーマなどを提供するライブラリです。  
主に DuckDB を内部データストアとして使い、OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析や市場レジーム判定、J-Quants API を介した株価／財務／カレンダーの ETL を想定しています。設計はルックアヘッドバイアス回避、冪等性、フェイルセーフを重視しています。

---

## 主な機能

- データ取得（J-Quants API）および保存（DuckDB）
  - 日次株価（OHLCV）、財務データ、JPXマーケットカレンダー
  - ページネーション・トークンリフレッシュ・レートリミット対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 結果を ETLResult として返却
- ニュース収集・前処理
  - RSS からのニュース取得、トラッキングパラメータ除去、SSRF 対策
- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に送信し ai_scores に保存（score_news）
  - JSON mode（厳密な JSON レスポンス前提）を利用
- 市場レジーム判定
  - ETF（1321）200日 MA 乖離とマクロニュースセンチメントを合成して日次でレジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- 監査ログ（audit）スキーマ
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local / 環境変数の自動読み込み（プロジェクトルート検出）と Settings オブジェクト

---

## 前提・依存

- Python 3.9+（コード型注釈に依存）
- ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ以外の依存は pyproject / requirements に合わせてインストールしてください。

（実際のパッケージ化に合わせて pyproject.toml / requirements.txt を用意してください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   - 例（最低限）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用・その他はプロジェクトの requirements / pyproject を参照して下さい。

3. パッケージをインストール（編集可能インストール）
   ```
   pip install -e .
   ```

4. 環境変数 (.env) を準備
   - プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime でも引数で渡せる）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必要時）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知に使用する場合
   - その他（任意または既定値あり）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development|paper_trading|live)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 初期化（監査 DB など）

監査用の DuckDB を初期化するユーティリティがあります。

例（Python REPL / スクリプト）:
```python
import duckdb
from kabusys.data.audit import init_audit_db

# ファイル DB を作る例
conn = init_audit_db("data/audit.duckdb")
# またはメモリ:
# conn = init_audit_db(":memory:")
```

また既存接続に対してスキーマを追加したい場合:
```python
from kabusys.data.audit import init_audit_schema
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

---

## 主要な使い方（サンプル）

以下はよく使うユースケースの例です。

- 設定（Settings）の利用:
```python
from kabusys.config import settings

print(settings.duckdb_path)  # Path オブジェクト
print(settings.env)          # development | paper_trading | live
```

- 日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai_scores への書き込み）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
z_norm = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

- カレンダー関連ユーティリティ:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

- J-Quants 低レベル API 呼び出し:
```python
from kabusys.data import jquants_client as jq

token = jq.get_id_token()  # settings.jquants_refresh_token を使って取得
records = jq.fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

- RSS ニュース取得（ニュースコレクタ）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
```

---

## .env の自動読み込みについて

- プロジェクトルート（.git または pyproject.toml を基準）を自動検出し `.env` と `.env.local` を読み込みます。
- 読み込み順序: OS 環境 > .env.local > .env（.env.local は上書き）
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル形式（export KEY=val やクォート、 inline コメントの扱い等）に柔軟に対応しています。

---

## 運用上の注意

- OpenAI 呼び出しを使う機能（news_nlp, regime_detector）は API レスポンスの形式に依存します。JSON mode を期待する設計のため、応答が厳密な JSON でない場合はフォールバックやスコア無効化が行われます。
- J-Quants API はレート制限（120 req/min）を守る実装になっていますが、大量取得時は実行間隔に注意してください。
- 環境変数 `KABUSYS_ENV` によって動作モード（development / paper_trading / live）が変わります。live モードでは実口座接続・発注処理を行うコードを慎重に扱ってください（本リポジトリに実際の発注モジュールがある場合）。
- ETL / AI 呼び出しは外部サービスに依存するため、ジョブとして cron などで定期実行して監視を行う運用が推奨されます。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys）内の主要モジュールです。実際のリポジトリではプロジェクトルートに pyproject.toml / README.md / .env.example 等が存在する想定です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境設定 / .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - etl.py                        — ETL インターフェース再公開
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - stats.py                      — zscore_normalize 等
    - quality.py                    — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                      — 監査ログスキーマの定義 / init
    - jquants_client.py             — J-Quants API クライアント（fetch/save 系）
    - news_collector.py             — RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py            — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        — calc_forward_returns / calc_ic / factor_summary / rank

---

## 開発・拡張のヒント

- テスト時は外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックすることを推奨します。実装中に幾つかの内部ヘルパー（_call_openai_api, _urlopen 等）が差し替え可能な設計になっています。
- DuckDB の executemany 空リストに対する制約など実際のバージョン挙動に注意している箇所があります（pipeline/news_nlp 等）。
- ルックアヘッドバイアス対策として、内部関数は date.today() を無闇に参照しない設計です。バックテスト用途に流用する場合もこの方針を維持してください。

---

必要であれば README に以下を追加できます:
- pyproject.toml / requirements.txt の雛形
- CI / テスト実行手順
- デプロイ（systemd / Docker / Airflow 等）例
- 各テーブルのスキーマ一覧（DDL）

必要な追加情報があれば教えてください。