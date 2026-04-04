# KabuSys

日本株向け自動売買／データプラットフォームライブラリ KabuSys の README。  
このリポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、リサーチ用ファクター計算、監査ログ、LLM を使った市場レジーム判定などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤ライブラリです。  
主な目的は次の通りです。

- J-Quants API を用いた株価／財務／市場カレンダーの差分取得と DuckDB への保存（ETL）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- RSS ニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄別）およびマクロセンチメント評価
- 日次の市場レジーム判定（MA200 と マクロセンチメントの合成）
- 研究（ファクター計算、将来リターン、IC 計算、統計ユーティリティ）
- 監査ログ（signal → order_request → execution をトレースするテーブル群）

ライブラリは DuckDB を内部データストアに想定しており、OpenAI / J-Quants の API キーを環境変数で受け取ります。

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants クライアント（ページネーション、レート制御、トークン自動リフレッシュ）
  - 日次 ETL（market calendar, daily prices, financials）
- データ品質管理
  - 欠損、重複、スパイク、日付不整合チェック
- ニュース収集
  - RSS フィード取得、SSRF 防御、記事正規化、raw_news 保存
- NLP / LLM
  - 銘柄ごとのニュースセンチメント（ai_scores への保存）
  - マクロセンチメントを用いた市場レジーム判定（market_regime への保存）
- 研究用ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン、IC（Spearman）計算、Zスコア正規化
- 監査ログ
  - signal_events / order_requests / executions テーブルの初期化・管理

---

## 要求・依存関係

- Python 3.10 以上（型アノテーションに Union | を使用）
- 必須パッケージ（最小構成）
  - duckdb
  - openai
  - defusedxml
- 推奨：仮想環境（venv / virtualenv / pipx など）

（パッケージは requirements.txt がない場合、手動インストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境と依存関係のインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

3. 環境変数（.env）を用意する  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
   KABU_API_PASSWORD=あなたの_kabu_api_password
   OPENAI_API_KEY=あなたの_openai_api_key
   ```

   任意 / デフォルト:
   ```
   KABUSYS_ENV=development        # development / paper_trading / live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LINE_CHANNEL_ACCESS_TOKEN=    # 通知用（任意）
   LINE_USER_ID=                 # 通知用（任意）
   ```

4. DuckDB データベースの準備（任意）
   - パイプライン実行時に自動的に必要テーブルを作る処理が入っている箇所もありますが、監査ログ専用 DB を初期化するユーティリティがあります（後述）。

---

## 基本的な使い方（例）

以下は Python REPL / スクリプトから各主要処理を実行する例です。

- 設定読み込み（settings）
```python
from kabusys.config import settings
print(settings.duckdb_path)      # Path object
print(settings.env, settings.log_level)
```

- DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（pipeline.run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（銘柄別）を作る（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# 第一引数に DuckDB 接続、第二引数に target_date を渡す
count = score_news(conn, date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")  # api_key 引数は省略可（env 経由）
print(f"書き込んだ銘柄数: {count}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, date(2026, 3, 20), api_key="YOUR_OPENAI_API_KEY")
# market_regime テーブルへ書き込まれる
```

- 監査ログ DB の初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
audit_conn = init_audit_db(db_path)  # テーブルとインデックスを作成
```

- RSS フィード取得（ニュース収集の低レベルユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

---

## よく使うコマンド・ワークフロー

- 日次バッチ（cron）例
  - 仮定: Python スクリプト run_daily.py を作り run_daily_etl を呼ぶ
  - cron で毎朝実行してデータ更新 → ニューススコアリング → レジーム判定の順に実行する運用が一般的

- テスト時
  - 環境変数自動ロードを無効化したい場合:
    ```
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    ```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- OPENAI_API_KEY (必要な箇所で必須) — OpenAI API キー（score_news / score_regime 等）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（"1"）

---

## ディレクトリ構成（抜粋）

src/kabusys/ 以下の主なファイル・モジュール:

- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの LLM ベースのセンチメント算出と ai_scores 書き込み
  - regime_detector.py — ETF MA200 とマクロセンチメントを合成して market_regime に書き込み
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント / DuckDB への保存関数
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETLResult の再エクスポート
  - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
  - news_collector.py     — RSS 取得・記事前処理・SSRF 防御
  - quality.py            — データ品質チェック
  - stats.py              — zscore_normalize 等の統計ユーティリティ
  - audit.py              — 監査ログスキーマ初期化（signal_events / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py    — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py— forward returns, IC, factor_summary, rank

（上記は主要ファイルの抜粋です。実際のファイルはさらに細分化されています）

---

## 設計上の注意点 / 運用上の留意事項

- Look-ahead bias 回避: 多くの関数（ETL / NLP / リサーチ系）は内部で datetime.today() を直接参照せず、明示的な target_date を受け取る設計です。バックテストや再現性のため target_date を明示して使用してください。
- リトライ / フェイルセーフ: 外部 API 呼び出し（OpenAI / J-Quants）は指数バックオフやフォールバック（失敗時はスコア=0 等）の挙動を持つため、個別 API の失敗が全体を止めない設計です。ただしログや quality チェックで検出された問題は運用側で確認してください。
- DuckDB executemany の仕様（バージョン差）に注意してある程度互換性を保つ実装がされています。
- news_collector は SSRF / XML 脆弱性対策を実装していますが、RSS ソースは信頼できるもののみ登録することを推奨します。

---

## 参考（開発・デバッグヒント）

- ロギングレベルは環境変数 LOG_LEVEL で制御可能。
- settings からパスを参照すると、デフォルトパス（data/）が使われます。必要時に .env でパスを変更してください。
- テスト時は OpenAI 呼び出し部分をモックする設計になっています（内部的に _call_openai_api を差し替え可能）。

---

以上が README の概要です。必要であれば下記を追加作成できます：

- 実行スクリプト（例: run_daily.py）のサンプル
- CI / テスト手順（ユニットテストの書き方・モック方法）
- requirements.txt / packaging のサンプル（pyproject.toml, setup.cfg 等）

どの情報を優先して追記しましょうか？