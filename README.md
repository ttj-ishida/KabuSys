# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、ファクター計算、監査ログの管理、マーケットカレンダー管理などを含むモジュール群を提供します。

## 主要な特徴
- J-Quants API を用いた差分 ETL（株価・財務・市場カレンダー）
- DuckDB によるローカルデータ保存（冪等保存・ON CONFLICT 対応）
- ニュースの LLM ベースセンチメント（OpenAI / gpt-4o-mini）による銘柄ごとの ai_score 生成
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）
- 監査ログ（シグナル→発注→約定 のトレーサビリティ）用スキーマの初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- マーケットカレンダー管理（JPX カレンダーの差分取得・営業日判定）
- テスト容易性を考慮した環境変数自動ロード機能（.env / .env.local）

---

## 機能一覧（主要 API）
- ETL / パイプライン
  - data.pipeline.run_daily_etl(...)
  - data.pipeline.run_prices_etl(...)
  - data.pipeline.run_financials_etl(...)
  - data.pipeline.run_calendar_etl(...)
  - data.pipeline.ETLResult
- J-Quants クライアント
  - data.jquants_client.fetch_daily_quotes(...)
  - data.jquants_client.fetch_financial_statements(...)
  - data.jquants_client.fetch_market_calendar(...)
  - data.jquants_client.save_*(...)
  - data.jquants_client.get_id_token(...)
- ニュース / AI
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 研究用（ファクター等）
  - research.factor_research.calc_momentum(...)
  - research.factor_research.calc_volatility(...)
  - research.factor_research.calc_value(...)
  - research.feature_exploration.calc_forward_returns(...)
  - research.feature_exploration.calc_ic(...)
  - research.feature_exploration.factor_summary(...)
  - research.rank / data.stats.zscore_normalize(...)
- データ品質 / カレンダー / ニュース収集
  - data.quality.run_all_checks(...)
  - data.calendar_management.is_trading_day(...) / next_trading_day(...) / prev_trading_day(...)
  - data.news_collector.fetch_rss(...)
- 監査ログ（スキーマ初期化）
  - data.audit.init_audit_db(path) / init_audit_schema(conn)

---

## 動作環境・依存 (目安)
- Python >= 3.10（型注釈に `X | None` を使用）
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス：J-Quants API、OpenAI API、RSS フィード等

セットアップではプロジェクトの requirements.txt を用意している場合はそちらを利用してください。なければ下記のパッケージをインストールしてください。

例:
```
python -m pip install duckdb openai defusedxml
# または
python -m pip install -e .
```

---

## 環境変数 / 設定
パッケージは起動時にプロジェクトルートにある `.env` と `.env.local` を自動的に読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用（任意）
- LINE_USER_ID: LINE 通知先ユーザ ID（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）
1. Python 環境を準備（3.10+）
2. リポジトリをチェックアウト
3. 必要パッケージをインストール
   ```
   python -m pip install -r requirements.txt
   ```
   または個別に:
   ```
   python -m pip install duckdb openai defusedxml
   ```
4. プロジェクトルートに `.env` を作成し、上記の環境変数を設定
5. DuckDB ファイルの格納先ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```
6. （任意）監査用 DB 初期化:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（簡単な例）
以下は Python REPL またはスクリプト内での利用例です。DuckDB 接続は duckdb.connect(...) を使用します。

1) ETL（1日分の差分 ETL を実行）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

2) ニューススコアリング（OpenAI API キーを環境変数か引数で渡す）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print("書き込み銘柄数:", n_written)
conn.close()
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
conn.close()
```

4) 監査スキーマの初期化（専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等の操作が可能
conn.close()
```

5) ニュース RSS の取得（単体）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## 注意事項 / 設計上のポイント
- Look-ahead バイアス防止:
  - バックテスト等で使用するときは、データの取得日時（fetched_at）や ETL の対象日取り扱いに注意してください。多くの関数は内部で datetime.today() を参照せず、引数の target_date に従って処理します。
- OpenAI 呼び出し:
  - score_news / regime_detector は OpenAI API（gpt-4o-mini 等）を使用します。API レスポンスが不正な場合や API エラー時はフェイルセーフ（スコアゼロやスキップ）で継続します。
- J-Quants:
  - get_id_token() は settings.jquants_refresh_token を使用します。API のレート制限や 401 時の自動リフレッシュ、リトライロジックを内蔵しています。
- .env の読み込み:
  - .env と .env.local をプロジェクトルートから自動読み込みします。`.env.local` が `.env` を上書きします。自動読み込みを無効にする環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
- DuckDB の executemany 互換性:
  - DuckDB のバージョン差異に対応するため、空リストを executemany で渡さない等の注意点がコード側に組み込まれています。

---

## ディレクトリ構成（抜粋）
プロジェクトの主要ファイル構造（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
    - __init__.py
  - (その他: strategy, execution, monitoring パッケージは __all__ で公開予定)

主要モジュールの責務:
- config.py: 環境変数と設定の読み込み・検証
- data/jquants_client.py: J-Quants API との通信・DuckDB 保存ユーティリティ
- data/pipeline.py: 日次 ETL の統合エントリポイント
- data/news_collector.py: RSS 収集と前処理
- ai/news_nlp.py: 銘柄ごとのニュースセンチメント付与
- ai/regime_detector.py: マクロと ETF MA を使った市場レジーム判定
- research/*: ファクター計算・特徴量解析

---

## 開発・運用上のヒント
- ローカル開発では `KABUSYS_ENV=development`、本番では `live` を利用してください。コード上で is_live / is_paper / is_dev を確認できます。
- 長時間実行するジョブや CLI のラッパーは PID/KILL フラグや監視閾値（CPU/MEM/DISK）関連の設定を利用できます。
- DuckDB ファイルは単一ファイルで済むため CI に組み込みやすいですが、ファイルのバックアップやパーミッションに注意してください。
- テスト時は自動 .env 読み込みを無効化して環境を制御すると良いです。

---

## ライセンス / コントリビューション
（ここには適切なライセンス表記やコントリビュート手順を記載してください）

---

不明点があれば、実行したいユースケース（ETL の自動化、news スコアリングのバッチ化、監査 DB の使い方など）を教えてください。実行例やスクリプト例を追加で用意します。