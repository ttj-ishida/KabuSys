# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
J-Quants / kabuステーション / RSS / OpenAI（LLM）などを組み合わせ、データ収集（ETL）・品質チェック・ファクター計算・ニュースセンチメント・市場レジーム判定・監査ログなどを提供します。

主な用途:
- 日次 ETL による株価・財務・カレンダーの自動取得・保存
- ニュースを LLM で解析して銘柄ごとの AI スコアを生成
- ETF とマクロニュースを合成した市場レジーム判定
- 研究用ファクター計算・特徴量探索ユーティリティ
- 発注フローを追跡可能にする監査ログスキーマ（DuckDB）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で設定値取得

- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェックの統合ワークフロー
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント（kabusys.data.jquants_client）
    - ページネーション・リトライ・レート制御・トークン自動リフレッシュ対応
    - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar 等）

- ニュース収集 / 前処理（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 対策・サイズ制限・トラッキング除去）
  - raw_news / news_symbols への冪等保存ロジック（設計方針に基づく）

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（急騰/急落）、日付不整合の検出
  - QualityIssue オブジェクトで問題を集約

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化関数
  - init_audit_schema / init_audit_db（DuckDB）

- 研究用ユーティリティ（kabusys.research）
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - forward returns、IC（Spearman）計算、ファクター統計サマリ、Zスコア正規化

- ニュース NLP / LLM（kabusys.ai）
  - score_news: 銘柄別ニュースを LLM（gpt-4o-mini）でスコア化して ai_scores に保存
  - score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成し market_regime に保存
  - OpenAI 呼び出しはリトライ・フェイルセーフあり（API失敗はゼロスコア等で継続）

---

## セットアップ手順

必要な主な Python パッケージ（例）
- duckdb
- openai
- defusedxml

（プロジェクトに requirements.txt があればそれを使ってください。ここは例示です）

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

3. リポジトリをインストール（開発モード）
   - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack 通知を使う場合
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI 呼び出しを行う場合（score_news/score_regime の api_key 引数で上書き可能）
   - 任意の変数（デフォルトあり）
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG|INFO|...)
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - KABU_API_BASE_URL

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要な例）

以下はライブラリ内の公開 API を簡単に利用するサンプルです。実行前に環境変数と DuckDB ファイルパス等を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアを計算して ai_scores に保存
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定を実行
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルへアクセスできます
```

- カレンダー・営業日ヘルパー
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- 設定値の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)
```

注意点:
- OpenAI を使う処理は API キーが必要。api_key 引数で明示的に渡すか OPENAI_API_KEY を設定してください。
- ETL / API 呼び出し系はネットワーク・外部 API に依存します。テスト時は各所で提供されているモックポイント（例: kabusys.ai.news_nlp._call_openai_api）を利用してください。

---

## 環境変数一覧（主なもの）

必須（使用する機能に応じて）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出し時）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携等）
- SLACK_BOT_TOKEN: Slack 通知トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack 送信先チャネル ID

任意 / デフォルトあり:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
- KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（監視設定）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml のある親）から .env を自動読み込みします。
- 読み込み順: OS 環境変数 > .env.local（override=True）> .env（override=False）
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM センチメント評価、ai_scores 書き込みロジック
  - regime_detector.py — ETF MA とマクロセンチメントを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー / 営業日判定
  - news_collector.py — RSS 収集・前処理
  - quality.py — データ品質チェック
  - audit.py — 監査ログの DDL と初期化
  - stats.py — 汎用統計関数（zscore_normalize など）
- research/
  - __init__.py
  - factor_research.py — momentum/value/volatility 等の計算
  - feature_exploration.py — forward returns / IC / factor summary / rank

（上記は主要モジュールの抜粋です。詳細は各ソースファイルの docstring を参照してください。）

---

## 開発・テストに関する補足

- LLM / ネットワーク呼び出しは外部 API に依存します。ユニットテストでは各モジュールが提供するモックポイント（例: news_nlp._call_openai_api）を patch して外部通信を避けてください。
- DuckDB を使ったテストは ":memory:" を用いることでインメモリ DB を利用できます（audit.init_audit_db 等は対応）。
- ETL の一部関数は部分的に失敗しても他処理を継続する設計（フェイルセーフ）。ログを確認して問題を把握してください。

---

README に含めるべき補足や使用例の追加、あるいは CI / デプロイ手順（systemd ユニットや cron ジョブの例）を希望される場合は教えてください。必要に応じて追記・整備します。