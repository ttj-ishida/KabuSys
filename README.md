# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群です。ETL、ニュースNLP、ファクター計算、監査ログ、J-Quants クライアントなどを含み、バックテスト／研究／運用で共通して使えるユーティリティを提供します。

> 注意: このリポジトリには実際の売買注文送信ロジック（kabuステーション等のブローカー接続）は限定的にしか含まれていません。運用環境で実際に発注する際は十分なレビューと安全対策を行ってください。

## 主な機能（Feature一覧）

- データ取得・ETL
  - J-Quants API からの株価（OHLCV）、財務データ、JPXカレンダー取得（ページネーション、レート制御、リトライ対応）
  - 差分更新・バックフィルを行う日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェック（quality.run_all_checks）
- ニュース収集・NLP（LLM）
  - RSS 収集（SSRF対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別 ai_scores へ書き込み）
  - マクロニュースとETF（1321）MA乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
- 研究（Research）
  - モメンタム／バリュー／ボラティリティ等のファクター計算（prices_daily / raw_financials を前提）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリ、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化（冪等）
- 設定管理
  - .env / 環境変数読み込み、自動ロード（プロジェクトルート判定）と必須設定チェック

---

## 要件

- Python 3.10+
- DuckDB (python duckdb パッケージ)
- openai（OpenAI の新 SDK のための import を使用）
- defusedxml（RSS パースの安全化）
- （運用時）J-Quants / OpenAI API の認証情報

pip 等でインストールしてください（依存関係は setup.py/pyproject.toml を参照してください）。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 例: pip install -e .  または pip install duckdb openai defusedxml
4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成することで自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必須: JQUANTS_REFRESH_TOKEN（J-Quants の refresh token）
   - OpenAI を使う機能を使う場合は OPENAI_API_KEY を設定してください（score_news / regime など）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (score_news / regime 用)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN (通知用、任意)
     - LINE_USER_ID (通知用、任意)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=secret
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. データベースディレクトリ作成（必要に応じて）
   - settings.duckdb_path の親ディレクトリを作成してください（多くのユーティリティは自動で親ディレクトリを作成しますが、念のため）。

---

## 使い方（簡単なサンプル）

以下は Python スクリプト/REPL からの代表的な呼び出し例です。すべての呼び出しは Look-ahead bias を避ける設計になっており、target_date を明示的に渡すことを推奨します。

1) DuckDB 接続を用意する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると today が使われます
result = run_daily_etl(conn, target_date=None)
print(result.to_dict())
```

3) ニュースセンチメント（銘柄ごとの ai_scores）を生成する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API を環境変数 OPENAI_API_KEY に設定しておくか、
# api_key 引数で明示的に渡します。
n = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n)
```

4) 市場レジーム（bull/neutral/bear）を計算して market_regime テーブルに書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI APIキーは環境変数または api_key 引数
```

5) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

6) 監査ログ DB の初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を使って監査テーブルに書き込めます
```

7) RSS フィードの取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

---

## よくある運用上のポイント / 注意点

- OpenAI 呼び出しや外部 API 呼び出しはネットワーク障害・レートリミット等を考慮してリトライ設計が施されていますが、APIキーや課金に関する取り扱いは十分注意してください。
- 自動環境変数ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env / .env.local を読み込みます。テストで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany や一部 SQL は DuckDB のバージョン依存の挙動（空配列のバインドなど）に注意して実装されています。DuckDB の互換性についてはテストしてください。
- ニュース収集は SSRF 防止、XML Bomb 対策（defusedxml）などの防御ロジックを含みますが、外部 URL を扱う際は組織のセキュリティポリシーに沿って運用してください。
- 設計上、ルックアヘッドバイアスを避けるため、各機能は target_date を明示的に受け取り、内部で date.today() をむやみに参照しないようにしています。バックテストや再現性のある実験では明示的な日付指定を行ってください。

---

## ディレクトリ構成（主なファイル）

プロジェクトの top-level は src/kabusys 以下にコードがあります。主要なサブパッケージと代表的なファイル：

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（銘柄別 ai_scores）
    - regime_detector.py      — 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の公開
    - quality.py              — 品質チェック（missing/spike/duplicates/etc）
    - stats.py                — 共通統計ユーティリティ（zscore_normalize）
    - news_collector.py       — RSS 収集、前処理、保存ロジック
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - audit.py                — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py      — momentum/value/volatility ファクター算出
    - feature_exploration.py  — forward returns, IC, factor_summary, rank
  - ai/、data/、research/ はそれぞれの責務に沿った API を公開しています

---

## 開発・テストについて

- 自動 .env ロードを無効化したいユニットテストは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや外部 HTTP はテスト時にモック（unittest.mock.patch）する設計箇所が用意されています（例: kabusys.ai.news_nlp._call_openai_api を差し替え可能）。
- DuckDB を in-memory (":memory:") で初期化してテスト実行可能です（audit.init_audit_db 等は ":memory:" を許容します）。

---

以上がこのコードベースの概要と基本的な使い方です。詳細な API（各関数引数・戻り値、挙動）は各モジュールの docstring を参照してください。追加で README に追記したい使用例や運用手順、デプロイ手順があれば教えてください。