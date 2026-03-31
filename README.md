# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に利用し、J-Quants API からの ETL、ニュース収集と LLM によるニュース・センチメント評価、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への冪等保存（ETL）
- RSS ニュースの収集・前処理と raw_news への保存
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント（銘柄単位）とマクロレジーム判定
- 研究用のファクター計算（モメンタム / バリュー / ボラティリティ）および特徴量解析ユーティリティ
- 監査ログ（signal / order_request / execution）のスキーマ作成と初期化ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計上の特徴：

- DuckDB 接続を直接受け取る関数設計で、テスト容易性とオフライン解析を重視
- Look-ahead バイアス回避に配慮（内部で datetime.today() を無闇に参照しない）
- 外部 API 呼び出しにはリトライやレート制御を実装
- LLM 呼び出しは JSON Mode（response_format）を用い、レスポンスのバリデーションを厳格に行う

---

## 機能一覧

- 環境設定管理: kabusys.config.Settings（.env 自動読み込み機構を含む）
- データ ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch_* / save_* 関数
- ニュース処理:
  - RSS フィード収集・前処理（kabusys.data.news_collector）
  - ニュース NLP（kabusys.ai.news_nlp.score_news）: 銘柄別 ai_score の生成（OpenAI）
- マクロレジーム判定:
  - kabusys.ai.regime_detector.score_regime（ETF 1321 の MA とマクロニュースの組合せ）
- 研究モジュール:
  - ファクター計算（kabusys.research.factor_research: calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（kabusys.research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank）
  - 統計ユーティリティ（kabusys.data.stats.zscore_normalize）
- データ品質チェック:
  - kabusys.data.quality.run_all_checks（欠損・スパイク・重複・日付整合性）
- 監査ログ:
  - init_audit_schema / init_audit_db（kabusys.data.audit）で監査用テーブルを初期化

---

## セットアップ手順

前提: Python 3.10+（型注釈で Union 用の | を使用）と pip が利用可能であること。

1. リポジトリをチェックアウト:
   - git clone ... またはソースを入手

2. 仮想環境の作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール:
   - 必要な主な依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install -r requirements.txt
     - または開発中に editable install:
       - pip install -e .

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数の設定:
   - プロジェクトルートの .env / .env.local を使用できます（自動ロード: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 必須の環境変数（最低限設定が必要）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知に使用（必須とされている設定）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   追加のオプション環境変数:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動ロードを無効化
   - KABUSYS_API_BASE_URL: kabu API ベース URL（config では KABU_API_BASE_URL、デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト data/monitoring.db）
   - OPENAI_API_KEY: OpenAI にアクセスする場合（score_news / score_regime の api_key 引数でも指定可）

---

## 使い方（代表的な例）

以下は基本的な Python からの呼び出し例です。実際は適切なエラーハンドリング・ログ設定を行ってください。

- DuckDB 接続を作って ETL を実行する（1日分の ETL）:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別 ai_score）の算出（OpenAI API キーが環境変数 OPENAI_API_KEY に設定されている想定）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written_count = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {written_count} scores")
```

- マクロレジーム判定（ETF 1321 の MA とマクロニュースを組み合わせる）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- 環境設定を参照する（プログラム内）:

```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
token = settings.jquants_refresh_token  # 未設定なら ValueError
```

- ニュース RSS を取得して raw_news に保存する処理は kabusys.data.news_collector 内のユーティリティを利用して実装できます（fetch_rss 等）。

注意:
- score_news / score_regime は OpenAI API を使用します。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API 呼び出しはレート制御・リトライを行いますが、ID トークンなどの設定は正しく行ってください（JQUANTS_REFRESH_TOKEN が必要）。

---

## ディレクトリ構成

主要なソース構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — マクロレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL インターフェース（ETLResult の再エクスポート）
    - news_collector.py      — RSS 収集・前処理
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - quality.py             — データ品質チェック（QualityIssue 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - audit.py               — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - monitoring/ (省略されているが __all__ に存在する可能性あり)
  - execution/ (発注系モジュール想定)
  - strategy/ (戦略層想定)

（実際のリポジトリでは他のファイル・サンプル・ドキュメントがある場合があります）

---

## 注意事項 / 実運用に向けたポイント

- セキュリティ:
  - RSS 収集で SSRF 対策や gzip サイズチェックなどが施されていますが、外部 URL 取り扱い時はネットワークのセキュリティを常に確認してください。
  - OpenAI API キーや J-Quants トークンは安全に管理してください（環境変数 / シークレットマネージャ推奨）。
- Look-ahead バイアス:
  - ライブラリはバックテスト等での誤用を避ける設計がされていますが、実装者側でも「いつの情報を使っているか」を明確にして運用してください。
- 冪等性:
  - ETL 保存関数は ON CONFLICT DO UPDATE 等で冪等に動作することを重視しています。
- リトライ / レート制御:
  - J-Quants API は 120 req/min の制限に合わせて RateLimiter が実装されています。大規模取得時はスループットに注意してください。
- テスト:
  - LLM 呼び出し関数やネットワーク依存部分はモック可能な設計（内部 _call_openai_api の差し替え等）です。ユニットテストを作成する際に活用できます。

---

以上が README.md の要約です。必要であれば、利用例（スクリプト化）、デプロイ手順、CI ワークフロー、.env.example のテンプレートなどを追加で作成します。どの情報を詳細化したいか教えてください。