# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
ETL（J-Quants）→ データ品質チェック → ニュースNLP（OpenAI）→ ファクター計算 → 監査ログまでを含むモジュール群を提供します。

主に DuckDB をデータバックエンドとして想定し、発注／実行やモニタリングは別モジュール（kabuステーション等）と連携します。

---

## 概要

KabuSys は以下のような機能を持つ Python パッケージ群です。

- J-Quants API と連携したデータ取得（株価日足、財務、上場情報、JPX カレンダー）
- DuckDB へ冪等保存する ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）とニューステキストの前処理
- OpenAI を利用したニュースセンチメント（銘柄別）と市場レジーム判定
- ファクター（モメンタム／バリュー／ボラティリティ等）計算と研究ユーティリティ
- マーケットカレンダー管理（営業日判定や next/prev_trading_day 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用テーブル作成・初期化

設計上の注意点として、バックテスト時のルックアヘッドバイアスを避ける工夫（日時参照の限定や取得ウィンドウの明示）や、API 呼び出しのリトライ・レート制御、フェイルセーフの扱いが随所に組み込まれています。

---

## 機能一覧（主な公開 API）

- 環境設定
  - `kabusys.config.settings`：アプリ設定（環境変数経由で取得）
- データ ETL / クライアント（J-Quants）
  - `kabusys.data.jquants_client.fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`
  - `kabusys.data.jquants_client.save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
  - `kabusys.data.pipeline.run_daily_etl`, `run_prices_etl`, `run_financials_etl`, `run_calendar_etl`
  - `kabusys.data.pipeline.ETLResult`
- ニュース収集・NLP
  - `kabusys.data.news_collector.fetch_rss`, `preprocess_text`
  - `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`：銘柄別ニューススコアを ai_scores に書き込む
  - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`：日次の市場レジーム（bull/neutral/bear）判定
- 研究（Research）
  - `kabusys.research.calc_momentum`, `calc_value`, `calc_volatility`
  - `kabusys.research.calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`
  - `kabusys.data.stats.zscore_normalize`
- カレンダー管理
  - `kabusys.data.calendar_management.is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `calendar_update_job`
- データ品質チェック
  - `kabusys.data.quality.run_all_checks`（欠損・重複・スパイク・日付不整合チェック）
  - `kabusys.data.quality.QualityIssue`
- 監査ログ（Audit）
  - `kabusys.data.audit.init_audit_schema`, `init_audit_db`

---

## 前提・依存関係

- Python 3.10+
  - （パイプライン内で PEP 604 の型注釈 `X | Y` を使用しているため）
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- そのほか標準ライブラリを使用（urllib, json, datetime など）

インストール（例）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ配布用に `pip install -e .` を想定
```

（プロジェクトに requirements.txt があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン
2. Python 仮想環境を作成して依存関係をインストール（上記参照）
3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に `.env` を置くと自動読み込みされます。
   - 読み込み順は OS 環境変数 > .env.local > .env です（`.env.local` は .env を上書き）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（注文連携がある場合）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（Slack 連携がある場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI 呼び出し時に使う API キー（score_news / score_regime のデフォルト）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live。デフォルト: development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

※ 以下は基本的な操作例です。実運用ではログ管理・エラーハンドリング・スケジューラを組み合わせてください。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（OpenAI を使って ai_scores テーブルへ書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn: duckdb connection
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を None にすると OPENAI_API_KEY を参照
print(f"scored {count} codes")
```

- 市場レジーム判定（ma200 + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査用 DuckDB 接続（テーブル一式が作成される）
```

- 研究用ユーティリティ（ファクター計算）
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

---

## 自動 .env 読み込みの挙動

- 起点は本パッケージ内の `kabusys.config` で、`.git` または `pyproject.toml` を親ディレクトリで探索してプロジェクトルートを特定します（カレントワーキングディレクトリに依存しません）。
- 読み込み順:
  1. OS 環境変数
  2. .env（プロジェクトルート）
  3. .env.local（プロジェクトルート、.env を上書き）
- 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- .env パーサはシェル風の `KEY=val`（export も可）、クォート処理やコメント処理等に対応しています。

---

## ディレクトリ構成

以下は主要ファイル／ディレクトリの概観（src 配下）です：

- src/
  - kabusys/
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
      - audit.py (監査関連)
      - etl.py (ETL 結果の公開)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
      - ...（ファクター／IC／統計ユーティリティ）
    - (他: strategy / execution / monitoring などのトップレベルモジュールが __all__ に想定)

ファイル単位で主要機能は README 上部の「機能一覧」に記載した通りです。

---

## 運用上の注意 / ベストプラクティス

- OpenAI 呼び出しを行う `score_news` / `score_regime` は API 呼び出し回数とコストに注意してください。バッチ処理やレート制御を適切に行ってください。
- DuckDB は埋め込み DB です。ファイルロックや同時アクセスに注意し、複数プロセスからの同時書き込みは設計次第で問題になります。
- ETL 実行時はまず calendar ETL を行い、取得した市場カレンダーで営業日調整してから prices / financials ETL を実行する設計になっています（run_daily_etl がその順序を実装）。
- 監査ログは削除しない方針で設計されています。トレーサビリティを壊さないように扱ってください。
- 本ライブラリは Look-ahead バイアス回避を重視した実装方針です。バックテストで内部ループから J-Quants のリアルタイム API を直接呼ばないなどの注意を守ってください。

---

## 連絡先 / 貢献

README に記載のない改善点やバグレポートは Pull Request / Issue で受け付けてください。  
（このテンプレートはコードベースから自動生成したドキュメントのため、ローカルの実行環境や実運用に合わせて調整してください。）

---

README はここまでです。必要であれば、セットアップスクリプト例や CI 設定、より詳細な API 使用例（各関数の引数説明例）を追記できます。どの部分を詳しくしたいか教えてください。