# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（モジュール群）。  
ETL（J-Quants からのデータ取得）、ニュース収集と LLM によるセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）、データ品質チェックなどを提供します。

## 概要
KabuSys は以下を主な目的とする Python パッケージです。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL と DuckDB への保存（冪等）
- RSS ベースのニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini 等）を使ったニュース NLP（銘柄別センチメント）および市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリューなど）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（信号 → 発注 → 約定のトレーサビリティ）を DuckDB に初期化・管理

設計上の重要点:
- ルックアヘッドバイアスを避ける（関数は内部で date.today() を直接参照しない等）
- API 呼び出しに対する堅牢なリトライとレート制御
- DuckDB に対する冪等保存（ON CONFLICT など）
- テストしやすいよう API キーやコールを引数で注入可能

---

## 機能一覧
- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 日足、財務、カレンダー、listed info）
  - market_calendar（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - news_collector（RSS 取得、前処理、SSRF 対策）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査ログスキーマ初期化 / init_audit_db）
  - stats（zscore_normalize 等）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込み
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュース LLM 評価を合成して market_regime に書き込み
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings: 環境変数読み込み（.env 自動ロード機能）、主要設定を一元化

---

## セットアップ手順

前提
- Python 3.10+
- ネットワークアクセス（J-Quants / OpenAI / RSS 取得）
- 必要なパッケージ（下記参照）

推奨手順（ローカル開発）
1. リポジトリをクローン
   git clone <repo-url>
2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール
   pip install duckdb openai defusedxml
   ※プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を利用してください。
4. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます）
   必須および推奨変数は下記参照
5. DuckDB のデータベースファイルやディレクトリが必要なら作成（設定に従う）

自動 .env の読み込みについて
- パッケージはプロジェクトルート（.git または pyproject.toml を含むディレクトリ）から `.env` を自動読み込みします。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必要な（主要な）環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用（必須とされる箇所で使用）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視用 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/…（デフォルト INFO）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な操作例）

以下はパッケージ API を直接呼ぶ例です。スクリプト化して Cron / Airflow 等で定期実行することを想定しています。

1) DuckDB に接続する（ファイル DB）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 監査ログ DB の初期化（監査テーブルを作成）
```python
from kabusys.data.audit import init_audit_db

# ファイルパスまたは ":memory:" を指定
audit_conn = init_audit_db(settings.duckdb_path)  # 既存 DB に監査テーブルを追加
```

3) 日次 ETL を実行（市場カレンダー更新、日足、財務データ、品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None で今日
print(result.to_dict())
```

4) ニュースのセンチメント生成（ai_scores への書き込み）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY 環境変数を利用
print("書き込み銘柄数:", n_written)
```

5) 市場レジーム判定（market_regime への書き込み）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

ret = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

6) ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

7) データ品質チェック
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity)
```

8) RSS 取得（ニュースコレクタの単体利用）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

注意点
- OpenAI 呼び出しや J-Quants 呼び出しは外部 API を必要とし、API キー・トークンが必要です。
- DuckDB に書き込む前にスキーマが期待通り作成されていることを確認してください（ETL 側にスキーマ初期化ロジックがある場合はそれを使ってください）。
- 実運用（live）では KABUSYS_ENV を "live" に設定し、ログレベルや監視を適切に構成してください。

---

## ディレクトリ構成（抜粋）
プロジェクトの主要ディレクトリとファイルを簡易的に示します（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュースセンチメント評価（score_news）
    - regime_detector.py           -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（fetch / save）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - etl.py                       -- ETL 結果クラス公開
    - calendar_management.py       -- 市場カレンダー管理 / 営業日判定
    - news_collector.py            -- RSS 取得・前処理・保存補助
    - quality.py                   -- データ品質チェック
    - audit.py                     -- 監査ログスキーマの初期化 / init_audit_db
    - stats.py                     -- zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py           -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py       -- 将来リターン、IC、統計サマリー
  - ai/, data/, research/ のテストや上位の execution/monitoring/strategy モジュールはプロジェクトの目的に応じて拡張される想定

---

## 運用上のヒント
- 環境分離: KABUSYS_ENV を利用して development / paper_trading / live を使い分ける
- API レート: J-Quants のレート制限（120 req/min）に注意。jquants_client は内部でスロットリングを行います。
- LLM 呼び出し: OpenAI のコストやレート制限に注意。バッチ化（news_nlp の chunking）が組み込まれています。
- ロギング: Settings.log_level を設定して適切なログ出力を得てください。
- テスト: 外部 API 呼び出しをモックしてユニットテストを作成してください（コード内にモックしやすい設計がされています）。

---

この README はコード内のドキュメントと設計コメントに基づいて作成しています。実際の運用前に、DB スキーマの初期化、適切なアクセスキーの設定、監視・バックアップ方針の整備を行ってください。必要があれば、具体的なスクリプト例（systemd / cron / Airflow など）や Docker 化手順、CI 設定のテンプレートも作成します。必要なら依頼してください。