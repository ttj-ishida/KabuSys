# KabuSys

日本株向けのデータ/リサーチ/自動売買補助ライブラリ。  
DuckDB をデータレイヤーに使い、J-Quants（株価・財務・マーケットカレンダー）や RSS / OpenAI（ニュースNLP）を組み合わせて、ETL、データ品質チェック、ニュースセンチメント、マーケットレジーム判定、ファクター算出、監査ログ構築などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得・ETL
  - J-Quants API からの株価（OHLCV）・財務データ・JPXカレンダーの差分取得と DuckDB への冪等保存
  - ETL の総合エントリ（run_daily_etl）と個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質管理
  - 欠損、重複、スパイク、日付整合性チェック（quality モジュール）
- ニュース収集・NLP
  - RSS 取得／正規化／raw_news 保存（news_collector）
  - OpenAI を用いたニュース銘柄別センチメントスコア（news_nlp.score_news）
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（ai.regime_detector.score_regime）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（data.audit）
- 研究用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value）や将来リターン計算、IC 計算、Zスコア正規化（research モジュール）
- セキュリティ・堅牢性
  - RSS の SSRF 対策、XML パースの安全化（defusedxml）、HTTP リトライ・レート制御、Look-ahead バイアス回避設計

---

## 要件（推奨）

- Python 3.10+
- 主な依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

実環境ではさらに requests 等を使う場合や Slack 連携のための slack-sdk 等が必要になる場合があります。プロジェクトの pyproject.toml / requirements.txt を使ってインストールしてください。

---

## セットアップ手順（例）

1. リポジトリをクローン／プロジェクトルートへ移動

2. 仮想環境を作成・有効化
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （もしプロジェクトに pyproject.toml があれば）pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env`（開発用）と `.env.local`（ローカル上書き用）を置くと、自動で読み込まれます（自動読み込みはデフォルト有効）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必要な環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合
   - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 'development'|'paper_trading'|'live'（デフォルト: development）
   - LOG_LEVEL: 'DEBUG'|'INFO'|'WARNING'|'ERROR'|'CRITICAL'

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下はライブラリ関数を使った簡単な実行例コードです。実行には DuckDB と必要な環境変数が設定されていることを前提とします。

- 日次 ETL を実行する（Python スクリプト内）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（ファイルは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))

# 当日分の ETL を実行（target_date を明示することも推奨）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
print(f"written: {n_written}")
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済み DuckDB 接続
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

注意点:
- OpenAI 呼び出しや J-Quants 呼び出しはネットワーク／課金が発生します。テスト時は各モジュールで API 呼び出しをモックしてください（ソース中にモックしやすい設計あり）。
- 関数はルックアヘッドバイアスを避ける設計になっています。target_date は明示的に与えることを推奨します。

---

## よく使う関数一覧（抜粋）

- kabusys.data.pipeline.run_daily_etl(...) : 日次 ETL（カレンダ・株価・財務・品質チェック）
- kabusys.data.pipeline.run_prices_etl(...) : 株価差分 ETL
- kabusys.data.pipeline.run_financials_etl(...) : 財務差分 ETL
- kabusys.data.pipeline.run_calendar_etl(...) : カレンダー差分 ETL
- kabusys.data.quality.run_all_checks(...) : 品質チェック一括実行
- kabusys.data.jquants_client.* : J-Quants API 取得 / 保存ユーティリティ
- kabusys.data.news_collector.fetch_rss(...) : RSS 取得ユーティリティ
- kabusys.ai.news_nlp.score_news(...) : ニュースセンチメントスコア取得 & ai_scores へ保存
- kabusys.ai.regime_detector.score_regime(...) : 市場レジーム判定 & market_regime へ保存
- kabusys.data.audit.init_audit_db(...) : 監査ログ DB 初期化
- kabusys.research.* : ファクター計算・解析ユーティリティ

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理 (.env 自動読み込み)
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント（AI）
    - regime_detector.py            — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult のエクスポート
    - news_collector.py             — RSS 取得・前処理・保存
    - calendar_management.py        — 市場カレンダー管理（営業日判定等）
    - quality.py                    — データ品質チェック
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value 等
    - feature_exploration.py        — 将来リターン・IC・統計サマリー
  - ai/__init__.py
  - …（他モジュール）

各モジュールは docstring に設計方針・処理フローを詳述しているため実装を辿りやすく設計されています。

---

## 補足・運用上の注意

- 自動 .env 読み込みは、プロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- J-Quants の API はレート制限（120 req/min）に従うよう内部で制御がありますが、実運用ではさらに外部制御や監視を行ってください。
- OpenAI 呼び出しは課金が発生します。テストはモックで代替することを推奨します（ソース内にモックポイントあり）。
- DuckDB のバージョンや SQL の違いに注意してください（ソース内にも互換考慮コメントあり）。
- 監査ログ（audit）や ai_scores / market_regime 等はバックテストや本番での再現性を意識して設計されています。バックテストの際はデータの取り扱い（取得日時／fetched_at の扱い）に注意してください。

---

もし README に追加したい内容（例: CI・テストの実行方法、より詳細な設定例、外部サービス連携の手順など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example のテンプレートも作成します。