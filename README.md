# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants からのデータ取り込み（ETL）、ニュース収集、LLM を用いたニュースセンチメント評価、マーケットレジーム判定、監査ログ（オーダー追跡）などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を盲目的に参照しない）
- DuckDB を主要なデータストアとして使用し、ETL は冪等（idempotent）
- 外部 API 呼び出しはリトライやレート制御を備えフェイルセーフに設計
- テスト容易性のため API キーや呼び出し関数の注入をサポート

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF 対策、前処理）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ（signal_events / order_requests / executions テーブル、初期化ユーティリティ）
  - 統計ユーティリティ（zscore 正規化 等）
- ai
  - ニュースセンチメント評価（score_news: 銘柄ごとの ai_score を ai_scores に保存）
  - 市場レジーム判定（score_regime: 1321 の MA200 乖離 + マクロニュース LLM による判定）
- research
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- config
  - 環境変数・設定管理（Settings クラス）
  - .env 自動読み込み（プロジェクトルートの .env / .env.local を順に読み込む。無効化可能）

---

## セットアップ

必要な Python パッケージ（主要なものの例）
- Python 3.9+（あるいは型アノテーションをサポートするバージョン）
- duckdb
- openai
- defusedxml

例（pip）:
```bash
python -m pip install -r requirements.txt
# requirements.txt がない場合は最低限:
python -m pip install duckdb openai defusedxml
```

パッケージ開発形式でローカルインストール:
```bash
python -m pip install -e .
```

環境変数
- 必須（Settings クラスで参照される）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD      : kabuステーション API 用パスワード
  - SLACK_BOT_TOKEN        : Slack 通知に使用する Bot Token
  - SLACK_CHANNEL_ID       : Slack 通知対象チャンネル ID
- 任意（デフォルト値有り）
  - KABUSYS_ENV            : "development" | "paper_trading" | "live" （デフォルト "development"）
  - LOG_LEVEL              : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）
  - KABU_API_BASE_URL      : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH            : 監視用 SQLite パス（デフォルト data/monitoring.db）
- OpenAI
  - OPENAI_API_KEY         : AI 機能（score_news / score_regime）で使用（関数呼び出し時に api_key を直接渡すことも可能）

.env 自動読み込み
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` と `.env.local` を読み込む仕組みがあります。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主なユースケース）

以下はライブラリの主要機能を Python で呼び出す例です。実運用ではロガー設定や例外処理、スケジューラ（cron / Airflow 等）から実行してください。

1) DuckDB 接続の作成（監査 DB 初期化や ETL 実行に使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path オブジェクト
```

2) 日次 ETL の実行（市場カレンダー・株価・財務を取得し品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を指定しなければ今日が対象（内部で営業日に調整）
print(result.to_dict())
```

3) ニュースのセンチメントスコア（AI）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 必要なら api_key を直接渡す（省略時は env の OPENAI_API_KEY を参照）
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")
```

4) 市場レジーム判定（MA200 とマクロニュースの LLM 合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ（オーダー追跡）用 DB 初期化
```python
from kabusys.data.audit import init_audit_db, init_audit_schema

# 監査専用 DB をファイルで初期化
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

# 既存接続に対してスキーマだけ初期化する場合
init_audit_schema(conn, transactional=True)
```

6) ニュース収集（RSS 取得のサブ関数）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

--- 

## 注意点・運用メモ

- OpenAI / J-Quants API はクレデンシャルが必要です。テストではキーを短命のものにしたりモックを利用してください。
- AI 呼び出しは失敗時にフォールバックするロジック（0.0 スコア等）を実装していますが、API 使用料に注意してください。
- ETL は冪等化されていますが、DuckDB のバージョン差異による executemany の挙動に配慮しています（空パラメータでの executemany を避ける等）。
- ニュース収集では SSRF・XML Bomb 対策などセキュリティ対策を実装しています。外部フィードの取り扱いには注意してください。
- KABUSYS_ENV を "live" にした場合は実際の注文実行や Slack 通知などを運用環境として扱う想定があるため慎重に設定してください。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリ内の主要なモジュール構造（src/kabusys 配下）です。

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント評価（score_news）
    - regime_detector.py    — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - jquants_client.py     — J-Quants API クライアントと保存ロジック
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - news_collector.py     — RSS 取得と前処理
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - etl.py                — ETL インターフェース再エクスポート
    - audit.py              — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py    — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py— 将来リターン/IC/統計サマリー

---

## 開発・貢献

- コードはモジュール分割されており、ユニットテストでは外部 API 呼び出しや I/O をモックすることを推奨します（各所に unittest.mock.patch で差し替え可能な内部ヘルパーが存在します）。
- .env.example（このリポジトリに含める場合）を参考に環境変数を準備してください。
- 大きな変更（特に DB スキーマや API 呼び出しロジック）は後方互換性に注意してください。

---

ご不明点や README に追加したい具体的な使用例（たとえば CI/cron の実行例や監視・アラート設定）などがあれば教えてください。必要に応じて README に追記します。