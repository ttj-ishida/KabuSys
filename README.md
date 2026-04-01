# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
DuckDB をデータ層に利用し、J-Quants / OpenAI / RSS など外部データを取り込み、ファクター計算・ニュースNLP・市場レジーム判定・ETL を行うユーティリティ群を提供します。

バージョン: 0.1.0

---

## 主要な目的（概要）

- J-Quants API から株価・財務・カレンダー等を取得して DuckDB に保存する ETL パイプライン
- ニュースを収集・前処理して LLM によるセンチメント評価を行い銘柄ごとの AI スコアを生成
- ETF（1321）200日移動平均乖離とマクロニュースで市場レジーム（bull/neutral/bear）を判定
- ファクター（モメンタム/バリュー/ボラティリティ）計算と特徴量探索（IC 等）
- 監査ログ（signal → order_request → execution）のためのスキーマ初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

---

## 機能一覧

- データ取得・保存
  - J-Quants クライアント（fetch/save daily quotes, financials, market calendar, listed info）
  - RSS ニュース収集と前処理（SSRF対策・トラッキング削除・受信上限）
  - ETL パイプライン（run_daily_etl でカレンダー→株価→財務→品質チェック）
- AI（OpenAI）連携
  - ニュース NLU / センチメント（score_news）
  - 市場レジーム判定（score_regime）
  - 再試行 / JSON-mode を用いた堅牢な API 呼び出し設計
- リサーチ
  - モメンタム / ボラティリティ / バリューファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）
  - IC 計算、Zスコア正規化、統計サマリー
- データ品質
  - 欠損チェック、スパイク検出、重複チェック、日付整合性チェック（run_all_checks）
- 監査ログ
  - 監査用スキーマ作成（init_audit_schema / init_audit_db）

---

## 前提条件 / 推奨ライブラリ

主に以下のライブラリを利用します（実プロジェクトの requirements.txt に合わせてください）:

- Python 3.10+
- duckdb
- openai
- defusedxml
- そのほか標準ライブラリ（urllib, json, datetime, logging 等）

（実行環境によっては追加で slack-sdk などを使うコードが別モジュールに存在する可能性があります）

---

## セットアップ手順

1. レポジトリを取得し開発用環境を作成する
   - git clone ... 
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係をインストールする（仮の例）
   - pip install duckdb openai defusedxml

   実際はプロジェクトの requirements.txt / pyproject.toml に従ってください。

3. 環境変数（.env）を準備する
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（コード上で参照される代表例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等の別モジュールで使用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

その他設定（デフォルト値あり）
- KABUSYS_ENV: development | paper_trading | live（default: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（default: INFO）
- KABU_API_BASE_URL: kabu API の base URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

サンプル .env（例）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な API）

以下は Python REPL / スクリプトからの利用例です。DuckDB 接続には duckdb.connect() を利用します。

- ETL の日次実行（株価・財務・カレンダー取得＋品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア生成（OpenAI を使用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にある場合、api_key 引数は省略可能
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} ai_scores")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
# conn_audit を使って監査テーブルに書き込みできます
```

- J-Quants の ID トークン取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # JQUANTS_REFRESH_TOKEN を参照
```

---

## 自動環境変数読み込みについて

- モジュール起動時にパッケージのルート（.git または pyproject.toml を基準）を探索し、プロジェクトルートの `.env` / `.env.local` を読み込みます。
- 優先順位:
  - OS の環境変数
  - .env.local（上書き可）
  - .env（.env.local より低優先度）
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用など）。

.env パースはシェル風の `export KEY=val` やクォート、インラインコメント等に対応しています。

---

## 主要なモジュールと API 概要

- kabusys.config
  - Settings クラス（環境変数アクセスの集中管理: settings.jquants_refresh_token など）
- kabusys.data.jquants_client
  - fetch_* / save_* 関数（J-Quants とのやりとり）
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult クラス
- kabusys.data.news_collector
  - fetch_rss / 前処理ユーティリティ
- kabusys.ai.news_nlp
  - score_news（ニュースまとめ → OpenAI → ai_scores へ保存）
- kabusys.ai.regime_detector
  - score_regime（1321 MA200 とマクロセンチメントを合成して market_regime へ保存）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.quality
  - run_all_checks（データ品質チェック群）
- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査ログスキーマ初期化）

---

## ディレクトリ構成

大まかなパッケージ構成は以下の通りです:

- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py              # ニュースNLP・OpenAI連携
    - regime_detector.py       # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント + DB 保存
    - pipeline.py              # ETL パイプライン
    - etl.py                   # ETL 結果公開インターフェース
    - news_collector.py        # RSS 収集
    - calendar_management.py   # 市場カレンダー管理
    - stats.py                 # 統計ユーティリティ（Zスコア等）
    - quality.py               # 品質チェック
    - audit.py                 # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py       # ファクター計算
    - feature_exploration.py   # IC・統計サマリー等
  - monitoring/                 # 監視用コード（存在する場合）
  - strategy/                   # 戦略関連（存在する場合）
  - execution/                  # 約定 / 発注関連（存在する場合）

---

## 注意事項 / ベストプラクティス

- Look-ahead バイアス防止:
  - モジュール内部は可能な限り date 引数を受け取り、datetime.today()/date.today() への直接依存を避けています。バックテスト等では必ず過去時点のデータのみを用いてください。
- OpenAI API 呼び出し:
  - score_news / score_regime は API キーを引数で注入可能。テスト時は関数をモックしてください（内部で _call_openai_api を差し替えられる設計）。
- ETL の堅牢性:
  - ETL は個別ステップで例外を捕捉し続行するため、ログと ETLResult を確認して手動対応判断してください。
- セキュリティ:
  - news_collector は SSRF 対策・受信サイズ上限・XML 脆弱性対策（defusedxml）を導入しています。外部 URL の扱いには注意を払ってください。
- DuckDB バージョン依存:
  - コードは DuckDB の特性（executemany の空リスト制約や型バインドの挙動）を考慮しています。将来の DuckDB バージョンでの挙動変更に注意してください。

---

## 貢献 / 開発

- バグ報告・改善提案は issue を作成してください。
- 新しい機能や修正は PR で送ってください。テストとドキュメントの更新を同梱してください。

---

README は以上です。必要なら利用例や CI / テスト手順（pytest など）を追記しますので、追加したい項目を教えてください。