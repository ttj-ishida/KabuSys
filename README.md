# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュースNLP・市場レジーム判定・監査ログ（発注／約定トレーサビリティ）・研究用ファクター計算などを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env）と設定
- 使い方（主要な呼び出し例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／データプラットフォーム用の内部ライブラリ群です。  
主な目的は以下です。

- J-Quants API を利用した株価・財務・カレンダーの差分 ETL（DuckDB に保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ニュース収集と銘柄ごとの NLP センチメント（OpenAI を利用）
- マーケットレジーム（bull / neutral / bear）の判定（ETF + LLM）
- 監査ログ（signal / order_request / execution）用のスキーマ初期化
- 研究用（ファクター計算・forward returns・IC 等）

設計上、バックテスト時のルックアヘッドバイアスを避けるために日付参照は明示的な引数ベースで行います（date.today() を無造作に参照しない方針）。

---

## 機能一覧

主なモジュールと機能（抜粋）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - settings オブジェクトから各種設定を参照

- kabusys.data
  - jquants_client
    - J-Quants API との通信（取得・保存・リトライ・レート制御）
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - save_daily_quotes / save_financial_statements / save_market_calendar
  - pipeline
    - run_daily_etl: 日次 ETL（calendar / prices / financials）＋品質チェック
    - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
    - ETLResult クラス
  - quality
    - check_missing_data, check_spike, check_duplicates, check_date_consistency
    - run_all_checks
  - news_collector
    - RSS フィード取得・前処理・raw_news 保存用ロジック
  - calendar_management
    - 営業日判定・next/prev/get_trading_days・calendar_update_job
  - audit
    - 監査ログ用 DDL 定義・init_audit_schema / init_audit_db

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを計算して ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF (1321) の MA200 乖離 + マクロニュースの LLM センチメントを合成し market_regime に書き込み

- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `X | Y` 構文を使用）
- 必要な外部パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

例: 仮想環境の作成とパッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発時はさらに linters 等を追加
```

（プロジェクト配布に requirements.txt / pyproject.toml があればそちらを使用してください）

.env（環境変数）ファイルをプロジェクトルートに置くと、自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。

---

## 環境変数（.env）

主要な環境変数（必須 / 任意）

必須（主に本番で必要）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client の get_id_token に使用）
- SLACK_BOT_TOKEN — Slack 通知で使用する場合
- SLACK_CHANNEL_ID — Slack 投稿先のチャンネル
- KABU_API_PASSWORD — kabuステーション API を利用する場合のパスワード

任意（デフォルト値あり）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" にすると自動 .env 読み込みを無効化
- KABUSYS_ENV により settings.is_live 等が決まります

DB パス（デフォルト）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（主要な呼び出し例）

以下はライブラリを直接インポートして使う想定です。CLI エントリはありませんので、スクリプトやジョブから呼び出してください。

1) 設定参照
```python
from kabusys.config import settings

print(settings.duckdb_path)        # Path オブジェクト
print(settings.is_live)            # True/False
```

2) DuckDB 接続取得（例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

3) 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を明示的に渡すことでルックアヘッドを防止
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

4) ニュース NLP スコアリング（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

5) 市場レジームスコア算出（ETF 1321 + マクロニュースの LLM 評価）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

6) 監査ログデータベースの初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_db_path = Path("data/audit.duckdb")
audit_conn = init_audit_db(audit_db_path)
# この接続は signal_events / order_requests / executions テーブルが作成済み
```

7) J-Quants のトークン取得（必要な場合）
```python
from kabusys.data.jquants_client import get_id_token

token = get_id_token()  # settings.jquants_refresh_token を利用
```

8) RSS フィード取得（news_collector）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点
- OpenAI の呼び出しはリトライ・フォールバックを含みますが、APIキーの管理は慎重に行ってください。
- ETL / NLP / レジーム判定は全て target_date を明示的に渡すことでバックテストに適した挙動になります（ルックアヘッド防止）。
- news_nlp と regime_detector は LLM に依存します（gpt-4o-mini を想定）。

---

## 開発／テストに関する補足

- 自動で .env を読み込む機能はプロジェクトルート（.git または pyproject.toml を探索）を基準にします。CI やユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して自動ロードを無効化できます。
- 外部 API 呼び出し（OpenAI / J-Quants / RSS fetch 等）はテスト時にモックする設計です。ソース中に差し替え用（unittest.mock.patch でのパッチ対象）説明があります。
- DuckDB に対する executemany の空リストはバージョン依存でエラーになる可能性を考慮した実装になっています。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys に配置されています）

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
    - quality.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - audit.py
    - (その他: e.g. clients / helpers)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（補助）
  - monitoring / execution / strategy / (パッケージ公開済み名あり) — パッケージ __all__ で公開するモジュール群

主なエントリ（API 関数）
- kabusys.data.pipeline.run_daily_etl
- kabusys.data.jquants_client.fetch_* / save_*
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.data.audit.init_audit_db / init_audit_schema
- kabusys.data.quality.run_all_checks
- kabusys.research.*（ファクター計算）

---

## ライセンス / 貢献

（このリポジトリにライセンスファイルがある場合はそちらを参照してください）  
貢献の際は issue / PR を通して設計思想（ルックアヘッド回避・冪等性・外部 API のリトライ方針等）を尊重してください。

---

以上がこのコードベースの README.md の内容です。必要であれば、具体的な CLI スクリプト例、Docker 化手順、CI 設定例 (.github/workflows) などを追記できます。どの部分を詳しく書きたいか教えてください。