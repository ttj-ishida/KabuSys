# KabuSys

日本株向けのデータプラットフォーム兼自動売買リサーチ/実行ライブラリ（KabuSys）。  
J-Quants / kabuステーション / OpenAI を組み合わせ、データ取得（ETL）、データ品質チェック、ニュース NLP、ファクター計算、監査ログなどを備えた設計になっています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を提供する Python パッケージです。

- J-Quants API を用いた株価・財務・マーケットカレンダーデータの差分取得（ETL）と DuckDB への保存
- RSS ベースのニュース収集と前処理・記事 → 銘柄紐付け
- OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメント分析（銘柄別）とマクロセンチメントによる市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ（将来リターン、IC、統計サマリー）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ用スキーマ）と初期化ユーティリティ
- kabuステーション発注や Slack 通知用の設定プレースホルダ（設定管理）

設計上のポイント:
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() に頼らない処理設計
- DuckDB を中心としたローカル DB ベースの処理（本番の発注は別モジュールを介する想定）
- 冪等性を意識した保存ロジック（ON CONFLICT / DELETE→INSERT 等）
- 外部 API 呼び出しはリトライやバックオフなどの堅牢化を実装

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（daily_quotes, financials, market_calendar, listed_info 等）
  - カレンダー管理（営業日判定、前後営業日の取得、calendar_update_job）
  - ニュース収集（RSS → raw_news + news_symbols）
  - データ品質チェック（missing_data, spike, duplicates, date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離 + マクロ NLP を合成して market_regime に保存
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数読み込み（.env / .env.local の自動読み込み、優先度制御）
  - settings オブジェクトによる集中設定参照

---

## セットアップ手順

前提
- Python 3.10 以上（| 型アノテーション、match 等を使っていないが union | を使用しているため 3.10+ 推奨）
- DuckDB、OpenAI SDK 等のインストール

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   例の requirements.txt（作成する場合の例）
   - duckdb
   - openai
   - defusedxml

   ※プロジェクトをパッケージ化している場合は:
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
   - SLACK_BOT_TOKEN: Slack 通知用（プロジェクト内の Slack モジュールで参照）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - オプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

   .env の例（.env.example を用意することを推奨）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=Cxxxx
   KABU_API_PASSWORD=your_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な呼び出し例）

以下は基本的な Python インタラクティブ / スクリプトの例です。各例は事前に環境変数と DuckDB パス等が設定されていることを前提とします。

1) DuckDB 接続準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコア算出（OpenAI を使って ai_scores に書き込む）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

4) マーケットレジーム判定（ETF 1321 の MA200 とマクロ NLP の合成）
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログスキーマの初期化（監査用 DB を別ファイルで初期化する例）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/kabusys_audit.duckdb"))
# audit_conn を使って監査ログへ書き込み／参照が可能
```

6) ファクター計算・研究ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

momentum = calc_momentum(conn, date(2026, 3, 20))
forward = calc_forward_returns(conn, date(2026, 3, 20))
ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")
```

注意:
- OpenAI 呼び出し部分は外部 API 呼び出しなのでレートや料金に注意してください。テストでは _call_openai_api をモック可能です。
- J-Quants API 呼び出しは rate limiter と retry を実装していますが、API キーや通信環境の確認を行ってください。

---

## 主要モジュールと API（抜粋）

- kabusys.config.settings: 設定値取得の central object
- kabusys.data.pipeline:
  - run_daily_etl(...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(...)
- kabusys.data.news_collector:
  - fetch_rss(...)
  - preprocess_text(...)
- kabusys.data.quality:
  - run_all_checks(...)
  - check_missing_data(...), check_spike(...), check_duplicates(...), check_date_consistency(...)
- kabusys.ai.news_nlp:
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector:
  - score_regime(conn, target_date, api_key=None)
- kabusys.research.*:
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary

---

## ディレクトリ構成

リポジトリの主要なファイル構成（src 配下を抜粋）:

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
      - (その他: schema/init など)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - (その他)
    - research/__init__.py
  - (パッケージメタ情報等)

この README は上記の主要モジュールの使い方と役割をまとめたものです。実際の運用では、ETL のスケジューリング（夜間バッチ）、OpenAI の利用料金管理、kabuステーションとの接続セキュリティ等を運用ポリシーに合わせて構築してください。

---

## 開発メモ / 注意点

- .env 自動読み込みは、プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います。テスト時に自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部はリトライ・バックオフを含みますが、API レートや費用の観点で本番では注意が必要です。テストでは _call_openai_api をモックすることを推奨します。
- DuckDB の executemany は空リストを受け取れないバージョンの挙動を考慮した実装が含まれています（挿入パラメータが空のときは呼ばない等）。
- 監査ログスキーマは冪等で作成されますが、DuckDB のトランザクション特性に留意して transactional 引数を利用してください。

---

もし README に追加したい利用例や CI のセットアップ、サンプル .env.example を望む場合は、その内容を教えてください。README を拡張して追加記載します。