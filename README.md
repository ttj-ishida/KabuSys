# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）など、トレーディングシステムの基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() 等を直接参照しない設計が多い）
- DuckDB を主要なローカル分析 DB として利用
- J-Quants API を用いた差分 ETL と冪等保存（ON CONFLICT / DO UPDATE）
- OpenAI（gpt-4o-mini 等）によるニュースセンチメント評価をサポート（JSON mode）
- セキュリティ配慮（RSS の SSRF 対策、XML の defusedxml 利用 等）

---

## 機能一覧

- データ収集・ETL
  - J-Quants クライアント（prices / financials / market calendar 等の取得、保存）
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
  - マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）
- ニュース収集・NLP
  - RSS フィード取得（SSRF/サイズ制限/トラッキング除去）
  - ニュースを銘柄ごとに集約し OpenAI に送ってセンチメントを ai_scores に保存（score_news）
- AI（OpenAI）を用いた上位機能
  - ニュース NLP（score_news）
  - 市場レジーム判定（score_regime）：ETF 1321 の MA200 乖離とマクロニュースで 'bull/neutral/bear' を判定
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクターサマリー、Zスコア正規化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）のスキーマ生成・初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env 自動読み込み（プロジェクトルートに基づく）
  - 必須環境変数チェック（settings オブジェクト）

---

## セットアップ手順

前提
- Python 3.10 以上
- Git (ソース管理)

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. パッケージのインストール（開発時は editable install）
   ```
   pip install -e .     # or: pip install -r requirements.txt
   ```
   主な依存パッケージ（抜粋）:
   - duckdb
   - openai
   - defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを参照してください）

3. 環境変数 / .env を用意する
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと、パッケージ読み込み時に自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先 Channel ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に未指定時は参照）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live。デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は代表的な操作のサンプルコードです。実行前に環境変数や DB パスの準備を行ってください。

- Settings の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

- DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを評価して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None → OPENAI_API_KEY を参照
print(f"wrote {num_written} ai_scores")
```

- 市場レジーム判定（regime）を算出して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # None → OPENAI_API_KEY を参照
```

- 監査ログ DB の初期化（監査用別DBを作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等が作成されます
```

- RSS フィードの取得（ニュースコレクタの一部機能）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注:
- OpenAI 呼び出しを行う関数（score_news, score_regime）は api_key を引数で注入できます。テスト時は関数内部の _call_openai_api をモックして動作を差し替えられるよう設計されています。
- ETL / 保存処理は冪等（重複時は更新）に設計されています。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (score_news/score_regime に使用)
- KABUSYS_ENV = development | paper_trading | live (デフォルト: development)
- LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 で .env 自動読み込みを無効化

---

## ディレクトリ構成

主要なモジュールとファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py       -- ニュース NLP（score_news）
    - regime_detector.py-- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py  -- マーケットカレンダー管理
    - etl.py / pipeline.py     -- ETL パイプラインと ETLResult
    - stats.py                 -- 統計ユーティリティ（zscore_normalize）
    - quality.py               -- データ品質チェック
    - audit.py                 -- 監査ログスキーマ初期化
    - jquants_client.py        -- J-Quants API クライアント（取得・保存）
    - news_collector.py        -- RSS 取得・前処理
    - (その他) ...
  - research/
    - __init__.py
    - factor_research.py       -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py   -- calc_forward_returns / calc_ic / factor_summary / rank
  - ai/*, research/*, data/* が主要な機能セット

（実際のリポジトリにはさらに細かいモジュール・テスト・ドキュメントが含まれる場合があります）

---

## 開発・テストに関するメモ

- 多くの外部 API 呼び出しはリトライやバックオフ、フェイルセーフを内包しています。ユニットテストでは外部呼び出し（OpenAI / J-Quants / ネットワーク）をモックすることを推奨します。
- news_nlp / regime_detector 等は内部の API 呼び出し箇所を差し替え可能に実装されています（unittest.mock.patch 等で _call_openai_api を置換）。
- DuckDB に関する executemany の空パラメータ問題など、バージョン依存の挙動に配慮した実装になっています（DuckDB 0.10 を想定した注意点がコメントにあります）。

---

もし README に含めたい追加の使用例（具体的な ETL スケジュール例、Slack 通知の設定例、kabu API の実行例など）があれば教えてください。README をそれに合わせて拡張します。