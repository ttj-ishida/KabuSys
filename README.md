# KabuSys

日本株向けの自動売買・データプラットフォームのコアライブラリです。  
ETL（J-Quants からのデータ取得）→ データ品質チェック → ニュース NLP / LLM スコアリング → 研究（ファクター計算）→ 監査ログ（発注トレーサビリティ）というワークフローを提供します。

主な設計方針：
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() に依存しない実装）
- DuckDB をデータレイクとして使用、冪等保存（ON CONFLICT）を重視
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライ・バックオフ・レート制限を実装
- セキュリティ考慮（RSS の SSRF 対策、defusedxml 等）

---

## 機能一覧

- data（ETL / データ品質 / カレンダー / ニュース収集）
  - J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - JPX マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 取得・正規化・raw_news への保存ロジック）
  - 監査ログ（signal_events / order_requests / executions のスキーマ初期化とユーティリティ）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai（ニュース NLP / 市場レジーム判定）
  - ニュースごとのセンチメントを OpenAI（gpt-4o-mini, JSON Mode）で評価して ai_scores に保存
  - 経済ニュース + ETF（1321）200日MA乖離から日次の market_regime を判定
  - API 呼び出しは堅牢なリトライを実装（429/タイムアウト/5xx 等）
- research（ファクター計算・特徴探索）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー等
- config
  - .env / 環境変数から設定を読み込み、アプリ設定（tokens / DB パス /しきい値）を提供
  - 自動 .env ロード（プロジェクトルートの .env / .env.local、無効化フラグあり）

---

## 動作要件（想定）

- Python 3.10+
- 必要な外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）

※プロジェクトに requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順（Quickstart）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 例（requirements.txt がない場合）:
     pip install duckdb openai defusedxml

3. パッケージをインストール（開発）
   - パッケージを editable インストール:
     pip install -e .

4. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（と必要に応じて `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の例:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456

# データベースパス（省略時は data/...）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境・ロギング
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

必須環境変数（コード上で _require() によって要求されるもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- （OpenAI を使う場合）OPENAI_API_KEY

設定は kabusys.config.settings で利用可能です。

---

## 使い方（例）

以下は Python REPL / スクリプトからの主要な呼び出し例です。

- DuckDB 接続を作成して ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ai: ニューススコアリング（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```

- ai: 市場レジームスコア（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
n = score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- data: カレンダー関連
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

is_trading = is_trading_day(conn, date(2026, 3, 20))
next_td = next_trading_day(conn, date(2026, 3, 20))
```

- data: 監査ログスキーマ初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- research: ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

注意点:
- OpenAI（news_nlp / regime_detector）は api_key（関数引数または環境変数 OPENAI_API_KEY）のいずれかが必須です。
- ETL・API 呼び出しはネットワーク依存のため、例外やリトライによる処理が発生します。

---

## 主要モジュールとディレクトリ構成

（root 側は src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード、settings オブジェクト提供
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM センチメント解析と ai_scores への書き込み
    - regime_detector.py  — ETF（1321）MA とマクロニュースから market_regime 判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch / save / rate limit / retry）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETL の公開型再エクスポート（ETLResult）
    - calendar_management.py — マーケットカレンダー管理（営業日判定 / 更新ジョブ）
    - news_collector.py   — RSS 収集・前処理・保存（SSRF 対策・トラッキング除去）
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付矛盾）
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - audit.py            — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value の計算
    - feature_exploration.py  — 将来リターン / IC / ファクター統計等
  - (その他) strategy/, execution/, monitoring/ など（パッケージ宣言に含まれる）

各ファイルは docstring に詳細な設計方針・処理フロー・注意点が書かれているため、参照してください。

---

## 開発・運用上の注意

- 自動 .env 読み込み
  - プロジェクトルートはこのモジュールファイルの親ディレクトリから `.git` または `pyproject.toml` を探して判定します。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- セキュリティ
  - news_collector では SSRF 対策、トラッキング除去、defusedxml による XML パースを採用しています。
  - J-Quants へはアクセストークン（JQUANTS_REFRESH_TOKEN）を使い id_token を取得してアクセスします。

- ログレベル / 環境
  - KABUSYS_ENV は development / paper_trading / live のいずれかを指定してください（settings.env）。
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL。

- Look-ahead Bias 防止
  - AI スコアリングや研究系の関数は内部で現在時刻を参照せず、target_date を明示的に受け取る実装になっています。バックテストでの利用時は target_date を適切に与えてください。

---

## 付録（参考）

- 監査ログ初期化:
  - init_audit_db(db_path) は親ディレクトリを自動作成し、UTC タイムゾーン設定でスキーマを整備します。
- ETLResult:
  - run_daily_etl は ETLResult を返します。結果の has_errors / has_quality_errors を確認して運用判断を行ってください。

---

README にない API や運用フローの詳細は、各モジュールの docstring と関数注釈（コメント）を参照してください。  
必要であれば、README にサンプルスクリプトや CI/CD / デプロイ手順の追加版も作成します。どの情報を追加したいか教えてください。