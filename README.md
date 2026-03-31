# KabuSys

日本株向けのデータプラットフォーム／自動売買補助ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ（発注トレース）などのユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は以下を主要機能として持つモジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と前処理／銘柄紐付け（raw_news / news_symbols）
- OpenAI（gpt-4o-mini）を使ったニュースのセンチメント解析（銘柄ごとの ai_score、マクロセンチメント → 市場レジーム判定）
- 研究（research）用ユーティリティ：モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン、IC計算、統計サマリ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution の履歴保存）用スキーマ初期化ユーティリティ
- 環境設定管理（.env 自動読み込み、Settings オブジェクト）

設計上の注意点（主要な設計方針）
- Look-ahead bias を防ぐため、内部で datetime.today() を直接参照しない（関数に target_date を渡す設計）
- API 呼び出しは retry / exponential backoff / rate limiting を実装
- DuckDB へは冪等（ON CONFLICT）で保存する設計
- テストしやすさを考慮して外部呼び出し部分は差し替え可能

---

## 機能一覧（概要）

- config
  - .env 自動ロード（プロジェクトルート検出）/ Settings で必須環境変数取得
- data.jquants_client
  - fetch / save: daily_quotes, financial_statements, market_calendar, listed_info
  - rate limiter / token refresh / retry ロジック実装
- data.pipeline
  - run_daily_etl: カレンダー→価格→財務→品質チェックまでの一連 ETL
  - 個別 ETL ヘルパー: run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult を返す
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- data.calendar_management
  - 営業日判定・next/prev_trading_day・get_trading_days・calendar_update_job
- data.news_collector
  - RSS フィード取得・前処理・SSRF 対策・記事ID 正規化・保存用ユーティリティ
- data.audit
  - 監査（signal_events / order_requests / executions）テーブルとインデックスの初期化
  - init_audit_db で専用 DB の初期化
- ai.news_nlp
  - calc_news_window, score_news: 銘柄ごとのニュース統合センチメントを計算して ai_scores に書込み
- ai.regime_detector
  - score_regime: ETF(1321) の MA200 乖離とマクロセンチメントを合成して market_regime テーブルへ書込
- research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / zscore_normalize

---

## セットアップ手順

※以下は基本的な手順例です。実環境では仮想環境を利用してください。

1. Python 環境（推奨: 3.10+）を用意
2. 必要なパッケージをインストール
   - 主な依存:
     - duckdb
     - openai (OpenAI Python SDK)
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. プロジェクトの .env を準備（自動ロードあり）
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動的に読み込まれます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...
   - (オプション) DUCKDB_PATH=data/kabusys.duckdb
   - (オプション) SQLITE_PATH=data/monitoring.db
   - (オプション) KABUSYS_ENV=development|paper_trading|live
   - (オプション) LOG_LEVEL=INFO|DEBUG|...

5. DuckDB 用のディレクトリを作る
   - 例: mkdir -p data

備考:
- config.Settings は必須の環境変数が未設定だと ValueError を送出します。
- .env のパースはシェル風の形式をサポートしています（export プレフィックス、クォート、コメント等）。

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトからの利用例です。target_date は Look-ahead bias を避けるため呼び出し側で明示します。

1) DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを計算して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を指定しなければ環境変数 OPENAI_API_KEY を使用
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

3) 市場レジーム（MA200 + マクロセンチメント）をスコアリングする
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
```

4) 監査用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_kabusys.duckdb")
# テーブルが作成されます
```

5) 研究用ファクター計算例
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
vol = calc_volatility(conn, date0)
val = calc_value(conn, date0)
```

テスト／開発ヒント:
- OpenAI の API 部分はユニットテストで差し替え可能（module 内の _call_openai_api を patch する設計）。
- 自動 .env 読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの top-level から見た主要ファイル・モジュール構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数と Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント計算（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - quality.py             — データ品質チェック
    - calendar_management.py — マーケットカレンダー操作 / calendar_update_job
    - news_collector.py      — RSS フィード収集・前処理
    - audit.py               — 監査ログテーブルの初期化
    - stats.py               — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
  - monitoring/ (※コードベース上に監視関連モジュールがあればここに配置)

（上記は現時点の実装ファイルに基づく抜粋です）

---

## 重要な設計・運用ノート（要確認）

- Look-ahead bias 防止:
  - 解析/ETL/AI スコアリングの全関数は target_date を明示的に受け取り、内部で現在時刻を直接参照しない設計を採用しています。バックテスト等では target_date を厳密に制御してください。
- 冪等性:
  - DuckDB への保存は ON CONFLICT（または INSERT ... ON CONFLICT DO UPDATE / executemany の個別 DELETE→INSERT）で実装されています。ETL を何度実行しても整合性が保たれる設計です。
- API 安全策:
  - J-Quants クライアントはレートリミッタ・リトライ・401 の自動リフレッシュに対応。
  - RSS 取得は SSRF 対策（プライベートアドレスブロック、リダイレクト検査）・受信サイズ制限・defusedxml を使用。
- OpenAI 呼び出し:
  - レスポンスのパース不備や API エラーはフェイルセーフで扱い（スコアを 0 にフォールバックしたり、当該チャンクをスキップする）、ETL 全体を壊さないようにしています。
- 環境管理:
  - Settings クラスで KABUSYS_ENV（development, paper_trading, live）や LOG_LEVEL を検証します。運用時はこれらを適切に設定してください。

---

## よくある質問（FAQ）

Q: OpenAI を使わずにテストしたい場合は？
A: score_news / score_regime の内部で OpenAI 呼び出しを行う private 関数（_call_openai_api）を unittest.mock.patch 等で差し替えることでテスト可能です。

Q: .env の自動ロードを止めたい
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: DuckDB のスキーマはどこで定義される？
A: ETL / save_* 関数は既存テーブルに書き込む前提です。初期スキーマ作成ユーティリティ（もしあれば data.schema.init_schema 等）を用意してください（このコードベースでは監査ログ用 init_audit_schema を提供しています）。

---

以上が README の内容（概要・セットアップ・使い方・構成）です。追加で「実行スクリプト」「CI 設定」「requirements.txt」など具体的ファイルをまとめたい場合は、それらに合わせて README を拡張します。必要であればサンプル .env.example を作成しますか？