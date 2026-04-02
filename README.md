# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリセットです。  
株価・財務・ニュースの ETL、ニュースセンチメント（LLM）解析、ファクター計算、監査ログスキーマ、JPX カレンダー管理など、取引システムとバックテストに必要な共通基盤機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易例）
- 環境変数（主要）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は、J-Quants 等の外部データソースからデータを取得・保存し、品質チェック・特徴量（ファクター）算出、ニュースの NLP スコアリング（OpenAI）や市場レジーム判定などを行う Python パッケージ群です。  
DuckDB をローカル DB として用い、ETL は差分更新とバックフィルを行い、監査ログ（発注 → 約定の追跡）用スキーマを提供します。ニュース収集時には SSRF 等の安全対策やサイズ制限も備えています。

設計方針の要点:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB を使った SQL + Python の実装
- 冪等性（DB 保存は ON CONFLICT / upsert を採用）
- 外部 API 呼び出しは堅牢なリトライ・レート制御を実装
- 安全性（RSS の SSRF 対策、XML の defusedxml 利用 等）

---

## 機能一覧

主要機能（モジュール別）
- kabusys.config
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境設定のラッパー（settings オブジェクト）
- kabusys.data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、レート制御）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS 収集、正規化、SSRF 対策、前処理）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: ニュースをバッチで LLM に投げて銘柄別センチメントを ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 とニュースセンチメントを合成し市場レジームを判定・保存
  - OpenAI API 呼び出しは gpt-4o-mini を想定（JSON mode を利用）
- kabusys.research
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク関数

（strategy / execution / monitoring といった上位モジュールはパッケージの公開 API に含まれる想定ですが、本リポジトリの一部モジュールで基盤機能を提供します）

---

## セットアップ手順

前提
- Python 3.9+（タイプヒントに union | を利用しているため、3.10 以上が望ましい）
- ネットワークアクセス（J-Quants / OpenAI）

推奨インストール（仮想環境を推奨）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   追加で開発用:
   - pip install pytest

※ requirements.txt / pyproject.toml があればそちらを使ってください。

環境変数の準備
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env / .env.local を読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 主要な環境変数は下記「環境変数（主要）」参照。

---

## 使い方（簡易例）

以下は最小限のサンプルコード例です。用途に応じてロギングや例外処理を追加してください。

1) settings を使う（環境変数参照）
```python
from kabusys.config import settings

print(settings.kabu_api_base_url)
if settings.is_live:
    print("本番モード")
```

2) DuckDB 接続を作って ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # Path は settings.duckdb_path を使っても良い
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのセンチメントを取得して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")  # api_key 省略時は OPENAI_API_KEY 環境変数を参照
print(f"書き込んだ銘柄数: {n}")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
```

5) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring.duckdb")  # テーブル群を作成して DuckDB 接続を返す
```

6) RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

---

## 環境変数（主要）

必須（稼働に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（発注系で使用想定）
- SLACK_BOT_TOKEN: Slack 通知用トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

OpenAI 関連
- OPENAI_API_KEY: OpenAI API 呼び出しに使用（news_nlp/regime_detector）

DB / パス関連（省略時デフォルトあり）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH: 実行監視用 PID ファイルパス（デフォルト data/execution.pid）

実行環境制御
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

.env ファイル例（プロジェクトルートに置く）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- .env.local は .env の上書きとして読み込まれます（OS 環境変数は保護されます）。
- settings は必須変数が未設定だと ValueError を投げます。

---

## ディレクトリ構成

主要ソースツリー（抜粋）
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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他 ETL 補助モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター / 統計ユーティリティ）
  - (strategy/, execution/, monitoring/ 等はパッケージ公開 API に含める想定)

説明:
- data/: データの取得（J-Quants）、保存、品質チェック、カレンダー管理、ニュース収集、監査ログ DB 初期化など
- ai/: ニュース NLP（OpenAI）や市場レジーム判定
- research/: ファクター計算、IC/統計解析

---

## 運用上の注意 / ヒント

- LLM（OpenAI）呼び出しはレート制限やエラーに対するリトライを内包していますが、API キーや料金に注意してください。
- ETL の実行は通常バッチ（夜間）で行い、calendar_update_job 等を先に実行して営業日情報を確保すると良いです。
- news_collector は外部 RSS を取得するため SSRF 対策や最大受信バイト数等の安全機構を設けています。RSS 取得失敗時の挙動はログを確認してください。
- DuckDB に保存されるテーブルは ON CONFLICT を使って冪等に更新されます。ETL 部分は途中失敗でもデータの整合性に配慮した実装になっています。
- テスト環境等で自動 .env ロードを無効化したいときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

---

必要に応じて README のサンプルコード（より詳しい使い方や CLI、systemd タスク例、CI 設定）を追加できます。特定の利用シナリオ（ETL のスケジュール化、発注ワークフロー、バックテスト連携）について追記希望があれば教えてください。