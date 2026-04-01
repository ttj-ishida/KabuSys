# KabuSys

日本株自動売買／データ基盤ライブラリ（KabuSys）の README（日本語）

このリポジトリは、日本株向けのデータ収集・ETL、特徴量（ファクター）計算、ニュース NLP（LLM によるセンチメント評価）、市場レジーム判定、監査ログ（トレーサビリティ）などを組み合わせた自動売買システムの基礎ライブラリ群を提供します。

主な目的：
- J-Quants API を中心とした株価・財務・カレンダー等のデータ ETL
- raw_news の収集と LLM によるニュースセンチメントのスコア化
- ファクター計算、特徴量探索、IC 計算等のリサーチユーティリティ
- 発注・約定までの監査ログスキーマ（DuckDB ベース）
- 市場レジーム判定（ETF + マクロニュースの組合せ）

---

## 機能一覧

主要モジュールと提供機能（抜粋）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 各種設定（J-Quants トークン、OpenAI、kabu API、Slack、DBパス、監視閾値 等）

- kabusys.data
  - jquants_client
    - J-Quants API との通信（認証、自動リフレッシュ、レート制御、リトライ）
    - fetch / save 関数群（daily_quotes, financials, market_calendar, listed_info）
  - pipeline / etl
    - 日次 ETL パイプライン（run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック）
    - 差分取得・バックフィル・品質チェック統合
  - news_collector
    - RSS 収集、前処理、SSRF 対策、記事 ID 正規化、raw_news への冪等保存
  - calendar_management
    - JPX カレンダー管理、営業日判定、next/prev_trading_day 等
  - quality
    - 欠損・重複・スパイク・日付不整合チェック（QualityIssue を返す）
  - stats
    - zscore_normalize 等の統計ユーティリティ
  - audit
    - signal / order_request / executions 等の監査テーブル DDL と初期化ユーティリティ

- kabusys.ai
  - news_nlp.score_news
    - raw_news を銘柄ごとに集約し LLM（gpt-4o-mini の JSON mode）でセンチメントを算出して ai_scores に保存
    - バッチ処理・リトライ・レスポンス検証・スコアクリップ実装
  - regime_detector.score_regime
    - ETF (1321) の 200 日 MA 乖離とマクロニュースセンチメントを組合せて市場レジーム（bull/neutral/bear）を判定して market_regime に保存

- kabusys.research
  - calc_momentum / calc_volatility / calc_value 等のファクター計算
  - calc_forward_returns, calc_ic, factor_summary, rank 等の特徴量解析ユーティリティ

その他：strategy / execution / monitoring のためのインターフェース（パッケージの __all__ に露出）

設計上の注意点：
- ルックアヘッドバイアス防止のため、内部ロジックは date.today() などで現在時刻を直接参照しない設計を心がけています（関数呼び出し時に target_date を与える）。
- 外部 API 呼び出しはリトライ・フォールバック動作を組み込んでいます（フェイルセーフ設計）。

---

## セットアップ手順

前提
- Python 3.10+（typing 機能や型注釈の使用を想定）
- DuckDB が必要（Python パッケージとしてインストール）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトが requirements.txt を提供している場合はそれを使用）

   必要に応じて他のパッケージを追加してください（例: psycopg2 などは本実装では不要）。

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（および .env.local）を置くと、自動で読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants 用リフレッシュトークン
     - OPENAI_API_KEY         — OpenAI API キー（news_nlp / regime_detector 用）
     - KABU_API_PASSWORD      — kabu ステーション API パスワード（発注等で必要）
     - SLACK_BOT_TOKEN        — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL (DEBUG, INFO, ...)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 sqlite、デフォルト data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   例（.env の一部）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB 初期化（監査 DB を使う場合）
   - Python REPL から:
     >>> import duckdb, kabusys.data.audit as audit
     >>> conn = duckdb.connect("data/kabusys.duckdb")
     >>> audit.init_audit_schema(conn, transactional=True)

   - あるいは、専用監査 DB を作成:
     >>> conn = audit.init_audit_db("data/audit.duckdb")

---

## 使い方（例）

以下は代表的な利用例です。実行は Python スクリプトまたはスケジューラから行います。

1) 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントをスコア化して ai_scores に保存する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")  # api_key を省略すると環境変数 OPENAI_API_KEY を参照
print(f"scored {count} codes")
```

3) 市場レジームを判定して market_regime に保存する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を利用
```

4) RSS フィードを収集して raw_news に保存（news_collector.fetch_rss を利用してから DB 保存処理を実装）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
# ※ 保存ロジックはプロジェクト側で用意してください（raw_news への INSERT 等）
```

5) 監査テーブルを初期化（別 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルとインデックスが作成されます
```

注意:
- OpenAI 呼び出しは API コストとレート制限を伴います。API キーの管理と費用・レートに注意してください。
- jquants_client は 120 req/min のレート制御を組み込んでいます。ID トークンの自動リフレッシュやリトライを実装しています。

---

## ディレクトリ構成

主要なファイル・モジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（LLM センチメント・ai_scores 書込）
    - regime_detector.py     — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集・前処理・SSRF 対策
    - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
    - quality.py             — データ品質チェック（欠損・スパイク・重複等）
    - stats.py               — 統計ユーティリティ（zscore 正規化等）
    - audit.py               — 監査ログスキーマと初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ等のファクター計算
    - feature_exploration.py — 将来リターン / IC / サマリー等
  - research/... (ユーティリティ)
  - monitoring, strategy, execution  — （インターフェース／将来的な機能）

プロジェクトルート:
- .env.example（存在する場合は .env のテンプレート）
- pyproject.toml / setup.cfg / requirements.txt（パッケージ化・依存定義がある場合）

---

## 運用上の注意・デザインポリシー

- ルックアヘッドバイアス対策
  - 多くのモジュールで target_date を引数に取り、内部で date.today() を直接参照しない実装方針です。バックテストや再現性ある処理のために重要です。
- フェイルセーフ設計
  - 外部 API（OpenAI / J-Quants / RSS）呼び出しはリトライやフォールバック（ゼロスコアなど）を行い、処理全体を停止させない設計です。
- 冪等性
  - DB への保存関数は基本的に冪等（ON CONFLICT DO UPDATE など）で設計されています。監査ログは削除しない前提です。
- セキュリティ
  - news_collector では SSRF 対策、defusedxml による XML パースの安全化、レスポンスサイズ制限などを行っています。

---

## 参考・追加情報

- 環境変数自動読み込み
  - config._find_project_root() により .git または pyproject.toml を基準にプロジェクトルートを探索し、.env / .env.local を自動ロードします。
  - 読み込み順: OS 環境 > .env.local > .env（.env.local は override=True）
  - 自動ロードを無効化するには環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- テスト
  - モジュールは外部呼び出し部分（OpenAI / ネットワーク / jquants）を関数やクラスで抽象化しており、ユニットテスト時にモック差替えが容易です（例: news_nlp._call_openai_api の patch）。

---

必要であれば以下も追加で用意可能です:
- .env.example のテンプレート
- requirements.txt / dev-requirements.txt
- 初期スキーマ作成用のスクリプト（raw_prices 等の CREATE TABLE 文）
- デプロイ手順（systemd / supervisor 用の実行例、PID ファイル配置方法）
- 追加の使用例（Slack 通知フロー、監視エンドツールとの統合）

ご要望があれば上記のうち必要な内容を追記して README を拡張します。