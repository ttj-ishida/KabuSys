# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、LLM を使った市場レジーム判定、監査ログ（発注／約定トレース）など、トレーディングシステムのデータ基盤と研究ワークフローを提供します。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・ページネーション対応、ID トークン自動更新、レートリミット順守、リトライロジック
- データ品質チェック
  - 欠損値・主キー重複・スパイク（急変動）・日付整合性チェック
- ニュース収集・前処理
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去）と前処理
- ニュース NLP（LLM）
  - 銘柄ごとにニュースをバッチで LLM（gpt-4o-mini を想定）に投げ、センチメント（ai_score）を ai_scores テーブルへ書き込み
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム（bull/neutral/bear）判定
- 監査ログ（オーディット）
  - signal_events / order_requests / executions テーブルでシグナル〜発注〜約定のトレーサビリティを保持
- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）、将来リターン計算、IC（スピアマン）計算、Zスコア正規化

---

## 前提

- Python 3.9+
- 必要な主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

※ 実行には各外部サービスの API キー（J-Quants、OpenAI、Slack 等）が必要です。

---

## インストール（例）

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

3. パッケージをプロジェクトに組み込む場合はソースを配置するか、パッケージ化して pip install してください。

---

## 環境変数 (.env)

本ライブラリはプロジェクトルートの `.env` / `.env.local` を自動でロードします（OS 環境変数が優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しで使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視設定

例（.env.example）
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

---

## セットアップ手順（簡易）

1. 必要な環境変数を `.env` に設定
2. DuckDB 用ディレクトリを作成（必要なら）
   - mkdir -p data
3. 監査用 DB の初期化（必要に応じて）
   - Python で以下を実行：
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
     - conn.close()
   - あるいは既存の DuckDB 接続に対して init_audit_schema を呼ぶことも可能
4. J-Quants 用の id_token はライブラリ側で自動取得します（JQUANTS_REFRESH_TOKEN 必須）

---

## 使い方（主要な例）

以下のコードは Python スクリプトや REPL から呼び出す例です。

- DuckDB 接続（例）
```
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
```
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別 ai_scores 生成）
```
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査テーブルを持つ独立 DB を作る）
```
from kabusys.data.audit import init_audit_db
db_conn = init_audit_db("data/audit.duckdb")
# db_conn を使って監査処理を行う
db_conn.close()
```

- RSS 取得（ニュース収集の一部）
```
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点：
- LLM 呼び出し系（score_news, score_regime）は環境変数 `OPENAI_API_KEY` または引数の api_key が必要です。未設定の場合は ValueError を送出します。
- ETL / API 呼び出しはネットワーク依存であり、リトライ・フォールバックのロジックが組み込まれていますが、API キーやネットワーク設定を事前に確認してください。

---

## ディレクトリ構成（主要ファイル）

(src 以下はパッケージ内部の主要モジュール）

- src/kabusys/
  - __init__.py — パッケージ定義（version 0.1.0）
  - config.py — 環境変数 / .env 自動ロード、設定アクセス（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（LLM で ai_scores を生成）
    - regime_detector.py — 市場レジーム判定（MA + LLM 合成）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理（営業日判定、next/prev 等）
    - etl.py — ETL 主要 API の再エクスポート
    - pipeline.py — 日次 ETL パイプライン（run_daily_etl 他）
    - stats.py — zscore 正規化ユーティリティ
    - quality.py — データ品質チェック群（欠損・スパイク・重複・日付整合性）
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py — J-Quants API クライアント（取得・保存関数含む）
    - news_collector.py — RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/*.py, research/*.py などは研究・分析用のユーティリティを含む

---

## 動作設計上のポイント / 注意事項

- ルックアヘッドバイアス回避:
  - 多くの関数は date / target_date を明示的に受け取り、内部で date.today() を直接参照しない設計です（バックテストや再現性のため）。
- 冪等性:
  - ETL 保存は ON CONFLICT（アップサート）や個別 DELETE → INSERT ロジックで冪等性を考慮しています。
- 外部 API 呼び出し:
  - J-Quants: レートリミット順守（120 req/min）、トークンの自動リフレッシュ、指数バックオフを実装
  - OpenAI: リトライ / エラーハンドリングを含むが API キーはユーザが提供する必要あり
- セキュリティ:
  - RSS 取得では SSRF 対策、トラッキングパラメータ除去、受信サイズ制限などを実施

---

## ライセンス / 貢献

（このリポジトリではライセンス表記はコード内に含まれていません。実プロジェクトでは LICENSE を追加してください。）

貢献や不具合報告は PR / Issue を通じてお願いします。

---

README は以上です。必要であれば、セットアップ用の具体的な .env.example ファイルや簡易スクリプト（ETL を定期実行する cron/airflow 等）サンプルを付け加えますので教えてください。