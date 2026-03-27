# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント分析）、ファクター計算、マーケットカレンダー管理、監査ログ（order/execution）のスキーマ管理などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームと自動売買パイプライン構築を想定した Python モジュール群です。主な目的は次のとおりです。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL
- RSS ベースのニュース収集と OpenAI を使った銘柄別 / マクロのセンチメント評価（gpt-4o-mini を想定）
- ファクター計算（Momentum / Value / Volatility 等）、特徴量解析ユーティリティ
- マーケットカレンダー（JPX）管理と営業日判定
- 監査ログ（signal → order_request → execution）のスキーマ定義・初期化
- データ品質チェック（欠損、スパイク、重複、日付整合性）

設計上の特徴として、ルックアヘッドバイアス防止、冪等性（DB 書き込み時の ON CONFLICT）、フェイルセーフな API リトライ処理、外部依存を最小化した実装方針が採られています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - market_calendar 管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - news_collector（RSS 取得・前処理・raw_news 保存）
  - quality（データ品質チェック）
  - audit（監査ログスキーマの初期化 / init_audit_schema, init_audit_db）
  - stats（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント生成（OpenAI）
  - regime_detector.score_regime: マクロ + ETF（1321）の MA を合成して市場レジームを判定
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 自動 .env ロード（プロジェクトルート検出）と Settings（環境変数アクセス）

---

## セットアップ手順

前提
- Python 3.10+（typing | Union 省略表記を含む実装を想定）
- duckdb パッケージ
- openai パッケージ（OpenAI API を利用する場合）
- defusedxml（RSS パース安全対策）
- ネットワーク接続（J-Quants / OpenAI / RSS ソース へアクセス可能）

1. リポジトリを取得・パッケージをインストール
   - 開発環境ではソースルートで:
     - pip install -e . など（setup があれば）
     - もしくは必要な依存を直接インストール:
       - pip install duckdb openai defusedxml

2. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml の所在）を基に自動で `.env` / `.env.local` を読み込みます（優先順位: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
   - 必須環境変数（Settings で参照されるもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - KABU_API_PASSWORD : kabu ステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN : Slack 通知を行う場合の Bot Token
     - SLACK_CHANNEL_ID : Slack 通知チャンネル ID
     - OPENAI_API_KEY : OpenAI 呼び出しに使用（score_news / score_regime に必要）
   - データベースパス（任意、デフォルトにフォールバック）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

   サンプル .env（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB 用ディレクトリの作成（必要に応じて）
   - デフォルトでは data/ 配下にファイルを作成します。必要であれば先に `mkdir -p data` を実行してください。多くの初期化関数は親ディレクトリを自動作成します。

---

## 使い方（代表的な例）

以下は、パッケージをインポートして機能を呼び出す簡単な例です。実運用ではログ設定やエラー処理を適切に行ってください。

1) 環境設定の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

2) DuckDB に接続して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントを生成（OpenAI API キーが必要）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を利用
print(f"書き込んだ銘柄数: {written}")
```

4) 市場レジーム判定（ETF 1321 の MA + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログスキーマ初期化（order/execution 用の DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

6) RSS 取得（ニュースコレクタの単体利用）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- OpenAI を使う関数は api_key 引数でキーを注入可能（テスト容易性のため）。None を渡すと環境変数 OPENAI_API_KEY を参照します。
- ETL / API 呼び出しはネットワーク・API 制限・トークン期限切れ等で例外が発生する可能性があります。呼び出し側で適切にハンドリングしてください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必要時) — OpenAI API キー
- KABU_API_PASSWORD (必要時) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
- KABUSYS_ENV — 環境（development, paper_trading, live）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

---

## ディレクトリ構成

（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数管理（.env 自動ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py            — 銘柄別ニュースセンチメント生成（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py      — J-Quants API クライアント + 保存（fetch/save）
    - news_collector.py      — RSS 取得・前処理・raw_news 挿入
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック（missing/spike/duplicates/date）
    - stats.py               — zscore_normalize 等
    - audit.py               — 監査ログスキーマ定義 / init_audit_db
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — forward returns, IC, summary, rank

---

## 開発・運用上の注意

- ルックアヘッドバイアス対策: モジュールの多くは内部で date.today()/datetime.today() を直接参照しない設計になっており、ETL/スコア計算は明示的な target_date を受け取ります。バックテスト用途でも意図しない未来情報参照を避けられます。
- 冪等性: ETL の保存関数は ON CONFLICT DO UPDATE/DO NOTHING を用いているため再実行に強い設計です。
- API リトライ・レート制限: J-Quants / OpenAI 呼び出しはレート・リトライ戦略を実装していますが、運用環境でのキー・レート制限に注意してください。
- セキュリティ: news_collector は SSRF 対策（プライベートホスト拒否、リダイレクト検査）や XML の defusedxml 使用、受信サイズ制限を導入しています。RSS ソース追加時も慎重に扱ってください。

---

## 貢献・拡張案

- バックテスト用のロジック（戦略エンジン）や実際の発注ブリッジ（kabu API との整合）を追加
- CI 用のユニットテスト（外部 API 呼び出しをモック）整備
- スキーママイグレーションツールの追加（DuckDB でのスキーマ変更サポート）
- メトリクスや監視（Prometheus exporter 等）の追加

---

README の内容・利用方法に関する質問や、サンプルの追加（例: .env.example、簡易スクリプト）をご希望であれば教えてください。必要に応じて README をさらに詳細化して提供します。