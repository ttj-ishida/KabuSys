# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
J-Quants / kabuステーション / OpenAI（LLM）等と連携し、データ取得（ETL）・品質チェック・ニュースNLP・市場レジーム判定・研究用ファクター計算・監査ログ基盤などを提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダーの差分取得／保存（ページネーション対応、冪等保存）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETLパイプライン
  - 日次ETL（calendar → prices → financials）と品質チェックの統合実行
  - ETL結果を表す ETLResult 型
- データ品質チェック
  - 欠損・スパイク・重複・日付整合性チェック（QualityIssue）
- ニュース収集（RSS）
  - URL正規化、SSRF対策、gzip/サイズチェック、記事→raw_news保存（冪等）
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（gpt-4o-mini / JSON mode）を ai_scores に保存
  - バッチ処理 / リトライ / レスポンス検証
- 市場レジーム判定（AI + テクニカル）
  - ETF(1321) の 200 日 MA 乖離とマクロニュース LLM センチメントを合成してレジーム（日次）を market_regime に保存
- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman rank）、統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを含む監査スキーマ初期化ユーティリティ
  - 監査DBの初期化関数（DuckDB）

---

## 必要条件

- Python >= 3.10（PEP 604 の union type `X | Y` を使用）
- 推奨パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

※ 実際の環境では `requirements.txt` / `pyproject.toml` を参照してください（本リポジトリに合わせて追加してください）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... （省略）

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて他の依存を追加）

4. パッケージをインストール / 開発モード
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動的に読み込まれます（CWD に依存せず、パッケージの場所からプロジェクトルートを探索）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必要な環境変数（必須は明記）:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack（通知等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス（任意、デフォルト値あり）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
- システム
  - KABUSYS_ENV (development | paper_trading | live) （デフォルト: development）
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) （デフォルト: INFO）
- OpenAI
  - OPENAI_API_KEY (score_news / score_regime 実行時に使用。関数にapi_key引数を渡すことも可)

> .env のパースはシェル風の `KEY=VALUE`、`export KEY=VALUE`、シンプルなクォートやコメントに対応しています。詳細は `kabusys.config` を参照してください。

---

## 使い方（サンプル）

以下は Python REPL / スクリプトでの簡単な呼び出し例です。事前に `.env` を整え、DuckDB の接続先ファイルを用意してください。

- DuckDB 接続例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI キーは環境変数 OPENAI_API_KEY で渡すか、api_key 引数に渡す）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, date(2026, 3, 20), api_key=None)
print(f"scored {count} symbols")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026, 3, 20), api_key=None)
```

- 監査DB 初期化（監査専用 DuckDB を作る例）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 以降 conn_audit を使って監査テーブルへ書き込み等を行う
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

テスト時のポイント:
- OpenAI 呼び出しは内部で `_call_openai_api` を呼んでいるため、単体テストでは該当関数をモックしてレスポンスを制御できます（例: `unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", ...)`）。

---

## 開発・デバッグのヒント

- 自動 .env 読み込みは、パッケージの実体ファイル位置からプロジェクトルート（.git / pyproject.toml）を探索して `.env` / `.env.local` を読み込みます。テストでこれを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB へはトランザクション制御（BEGIN / COMMIT / ROLLBACK）を行っている箇所が多くあります。ETL 実行やテーブル初期化時はトランザクションの状態に注意してください（特に `init_audit_schema(transactional=True)`）。
- J-Quants クライアントは内部で固定間隔の RateLimiter を使用しているため、短時間に大量のリクエストを投げる実装は避けてください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（実際のツリー）
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ ai/
   │  ├─ __init__.py
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ calendar_management.py
   │  ├─ pipeline.py
   │  ├─ etl.py
   │  ├─ stats.py
   │  ├─ quality.py
   │  ├─ audit.py
   │  ├─ jquants_client.py
   │  └─ news_collector.py
   └─ research/
      ├─ __init__.py
      ├─ factor_research.py
      └─ feature_exploration.py
```

---

## 補足 / 注意点

- Look-ahead bias 対策が各所に組み込まれています（target_date の扱い、DBクエリの排他条件、fetched_at の記録など）。バックテスト用途で使用する場合はデータ取得タイミングに注意してください。
- OpenAI / J-Quants 等の外部 API キーは秘密として取り扱ってください（.env を共有しない、CI に Secrets を設定する等）。
- 本リポジトリは多数の設計上の前提（テーブルスキーマ、DuckDB のバージョン差異など）に依存します。実運用前に小規模環境で十分な検証を行ってください。

---

もし README に追加したい具体的な情報（例: 実際の .env.example のサンプル、requirements.txt の内容、実行用スクリプトや CLI、テーブルスキーマドキュメント等）があれば教えてください。必要に応じて追記・整形します。