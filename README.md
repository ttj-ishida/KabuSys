# KabuSys — 日本株自動売買基盤（README）

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買基盤のコアライブラリです。  
主に以下を提供します。

- J-Quants API からの株価/財務/カレンダーの ETL パイプライン（差分取得・冪等保存）
- ニュース収集・NLP（LLM）による銘柄別センチメントスコア生成
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコアを合成）
- ファクター計算・特徴量分析（モメンタム / バリュー / ボラティリティ 等）
- マーケットカレンダー管理・品質チェック・監査ログ（トレーサビリティ）
- J-Quants / OpenAI など外部 API の統制された呼び出しとリトライ処理

特徴
----
主な機能一覧（抜粋）:

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（ページネーション・レート制限・トークン自動リフレッシュ）
  - ニュース収集（RSS、SSRF対策、前処理、冪等保存）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day など）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal / order_request / executions テーブルの初期化ユーティリティ）
  - 統計ユーティリティ（zscore 正規化）
- ai
  - news_nlp.score_news: ニュースを LLM に送り銘柄別スコアを ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュース LLM を合成して market_regime を作成
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（forward returns / IC / summary / ranking）

設計方針（要点）
- ルックアヘッドバイアス（バックテストでの情報漏洩）を防ぐ設計
- DuckDB を中核に、ETL は冪等に保存（ON CONFLICT で更新）
- API 呼び出しはレート制御・リトライを実装
- LLM 呼び出しのフェイルセーフ：失敗時はスコアを 0.0 にフォールバックして継続

セットアップ手順
----------------

1. 必要な Python バージョン
   - Python 3.10+（typing の union 型などを利用）

2. 依存パッケージ（代表例）
   - duckdb
   - openai
   - defusedxml
   - （その他プロジェクトで管理する requirements を参照してください）

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. リポジトリをチェックアウトしてインストール
   - 開発環境であれば editable install:
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

4. 環境変数 / .env
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（必要に応じて）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を使う場合
     - OPENAI_API_KEY — LLM（OpenAI）を使う場合（score_news / score_regime）
   - データベースパス（任意、デフォルト値あり）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
   - 実行環境:
     - KABUSYS_ENV: one of "development", "paper_trading", "live"（デフォルト "development"）
     - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト "INFO"）
   - 自動 .env ロード:
     - パッケージはプロジェクトルート（.git または pyproject.toml）を探して .env を自動読み込みします（.env.local は .env を上書き）。
     - 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

使い方（簡易ガイド）
-------------------

※ 例では Python スクリプトから直接呼び出す方法を示します。運用時は適切なジョブスケジューラ（cron / Airflow 等）で日次バッチを実行してください。

1) DuckDB 接続を開く
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニューススコアリング（LLM）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されていれば api_key=None で可
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {written} codes")
```

4) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は自動で実行され、必要なテーブル・インデックスを作成します
```

6) RSS ニュース取得（テスト的に）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

source = "yahoo_finance"
url = DEFAULT_RSS_SOURCES[source]
articles = fetch_rss(url, source)
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

重要な実装上の注意
- AI モジュール（news_nlp / regime_detector）は OpenAI の JSON mode を利用する想定です。API のレスポンスは厳密にバリデーションされ、失敗時はフェイルセーフ（スコア = 0）で継続します。
- 多くの関数は datetime.today() / date.today() を直接参照しない設計（引数で target_date を受け取る）になっており、バックテストや再現性を意識しています。
- ETL の保存は基本的に冪等に実装されています（ON CONFLICT DO UPDATE / DO NOTHING を活用）。

ディレクトリ構成（主要ファイル）
------------------------------

プロジェクトの主要なモジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NPL / LLM スコアリング
    - regime_detector.py     — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py      — RSS ニュース収集（SSRF 対策・前処理）
    - calendar_management.py — マーケットカレンダー管理 / 営業日判定
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - audit.py               — 監査ログテーブルの初期化 / 管理
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — forward returns / IC / factor summary / rank

（各モジュールの詳細な docstring に実装方針・処理フロー・注意点が記載されています）

運用上のヒント
----------------
- OpenAI 呼び出しはコストとレート制限に注意してバッチ化・間引きしてください（news_nlp は最大バッチサイズ等の制御あり）。
- J-Quants の API レート制限（120 req/min）を守るためモジュールに内部 RateLimiter が組み込まれています。スケジューリングの際は過度な並列化を避けてください。
- ETL は部分失敗時に既存データを保護する設計（書き込み対象コードの絞り込み等）になっていますが、運用ログ・監査ログを確認して問題を検知してください。

貢献 / 開発
-------------
- 新しい機能を追加する場合は既存の設計原則（冪等性・ルックアヘッドバイアス回避・SQL パラメータバインド）を順守してください。
- LLM の呼び出し箇所はテストの差し替え（unittest.mock.patch）を想定した実装になっています。ユニットテスト作成時は外部呼び出しのモックを推奨します。

免責
----
この README はコードベースの概要と利用方法を示すものであり、実際の運用では更なる監査・保守・テストが必要です。実運用での発注・マネー管理は慎重に取り扱ってください。

---

必要に応じて README に追記したい具体的な項目（例えば CI / テスト手順、requirements.txt の中身、デプロイ手順など）があれば教えてください。