# KabuSys

日本株向けのデータ基盤・研究・自動売買ユーティリティ群をまとめたパッケージです。  
J-Quants / RSS / OpenAI 等と連携してデータ収集（ETL）・品質チェック・特徴量算出・ニュース NLP（LLM評価）・市場レジーム判定・監査ログ管理などを行うことを目的としています。

---

## 主要な特徴（機能一覧）

- データ収集（ETL）
  - J-Quants API からの株価（日足）・財務データ・JPXカレンダー取得（差分取得、ページネーション対応、リトライ、レート制限管理）
  - ETL パイプライン（run_daily_etl）による一括更新と品質チェック
- データ品質管理
  - 欠損、スパイク、重複、日付不整合のチェック（quality モジュール）
- ニュース収集・前処理
  - RSS フィードの安全な取得（SSRF対策、gzip対応、受信サイズ制限）、raw_news / news_symbols への冪等保存（news_collector）
- ニュース NLP（LLM）
  - OpenAI（gpt-4o-mini）の JSON Mode を用いた銘柄別ニュースセンチメントスコア算出（news_nlp.score_news）
  - マクロニュース + ETF（1321）200日MA乖離を合成した市場レジーム判定（regime_detector.score_regime）
- リサーチユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）
- 汎用ユーティリティ
  - z-score 正規化などの統計関数（data.stats）

---

## 要件

- Python 3.10 以上（型ヒントの新しい構文 Path | None 等を使用）
- 必要な Python パッケージ（主なもの）
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

（実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## インストール（開発環境例）

1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. パッケージを編集可能インストール（プロジェクトルートが pyproject.toml / .git を含む構成の想定）
   - pip install -e .

---

## 環境変数 / .env

パッケージは起動時に自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（優先度: OS環境 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須）:

- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（ETLで使用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（注文系で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 等で使用）

任意・設定可能な環境変数（デフォルトあり）:

- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite（default: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視設定）

環境変数は `kabusys.config.settings` からプロパティで参照できます（例: `from kabusys.config import settings`）。

---

## セットアップ手順（DB 初期化等）

- DuckDB 接続作成例:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査ログ用 DB の初期化（別ファイルに監査専用 DB を作る場合）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db(settings.duckdb_path)  # ":memory:" でインメモリ DB
```

- 監査スキーマを既存接続に追加する場合:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## 使い方（代表的な例）

- 日次 ETL を実行（市場カレンダー / 株価 / 財務 / 品質チェック）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（LLM）で銘柄ごとのスコアを生成して ai_scores に保存

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
# conn は DuckDB 接続、OPENAI_API_KEY を環境変数で設定しておく
n_written = score_news(conn, date(2026,3,20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（ETF 1321 MA200 とマクロニュースの合成）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

# conn は DuckDB 接続、OPENAI_API_KEY を環境変数で設定
score_regime(conn, date(2026,3,20))
```

- RSS フィードを取得（ニュース収集の一部）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

source = "yahoo_finance"
url = DEFAULT_RSS_SOURCES[source]
articles = fetch_rss(url=url, source=source)
# 取得した articles を raw_news テーブルに保存する処理を実装する
```

- 研究向けファクター計算

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

res_mom = calc_momentum(conn, date(2026,3,20))
res_val = calc_value(conn, date(2026,3,20))
res_vol = calc_volatility(conn, date(2026,3,20))
```

---

## 主要 API 概要

- kabusys.config.settings
  - 環境変数／設定の参照経路（.env 自動読み込み）
- kabusys.data.pipeline.run_daily_etl(...)
  - 日次 ETL のエントリポイント。ETLResult を返す。
- kabusys.data.jquants_client
  - J-Quants との HTTP 単発取得・保存ユーティリティ（fetch_*, save_*）
- kabusys.data.news_collector.fetch_rss(...)
  - RSS フィード安全取得
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースセンチメントを ai_scores テーブルへ書き込む
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム（bull/neutral/bear）を market_regime テーブルへ書き込む
- kabusys.data.audit.init_audit_db / init_audit_schema
  - 監査テーブルの初期化

---

## 注意点 / 設計上の留意点

- Look-ahead バイアス防止
  - コードは date や target_date を明示して処理するよう設計されています。内部で datetime.today() を使わない関数が多く、バックテスト用途でも時間的な漏洩を避ける設計です。
- 冪等性
  - ETL / 保存処理は基本的に冪等（ON CONFLICT DO UPDATE / ON CONFLICT DO NOTHING）を意識しています。
- エラーハンドリング
  - 外部 API の失敗時にはフェイルセーフ（スコア=0 やスキップ）で継続する実装が多く、完全停止より「部分継続」を優先します。
- セキュリティ
  - NewsCollector は SSRF 対策（リダイレクト検査、プライベートIP拒否）や defusedxml を用いた XML パースの保護を行っています。

---

## ディレクトリ構成

以下は主要ファイルの構成（抜粋）です。実際はプロジェクトルートに pyproject.toml / setup.cfg 等が存在する想定です。

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
    - research/...
    - (strategy/, execution/, monitoring/ 等のパッケージ参照用エントリは __all__ に定義)

---

## 開発 / 貢献

- ローカルでの実行・単体テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して `.env` の自動読み込みを抑制できます。
- 外部 API（J-Quants / OpenAI）を多用するため、ユニットテストでは HTTP / OpenAI 呼び出しをモックして実行してください。
- セキュリティ／耐障害性に関する実装が多数存在するため、変更する場合はユースケースに対する回帰テストを推奨します。

---

README はここまでです。必要であれば次の内容も追加します：
- 例となる .env.example のテンプレート
- 具体的な requirements.txt / pyproject.toml の例
- 典型的なワークフロー（cron/airflow で ETL を定期実行する方法）
- 各テーブルのスキーマ（DDL抜粋）や ER 図

どれを追加しますか？