# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータパイプライン、研究（ファクター計算）、ニュースの自然言語処理（LLM を用いたセンチメント評価）、市場レジーム判定、監査ログ（トレーサビリティ）等を含む自動売買プラットフォーム基盤です。  
本リポジトリには ETL、品質チェック、ニュース収集、AI スコアリング、ファクター計算、監査テーブル初期化などの主要機能が実装されています。

主な目的：
- J-Quants API からのデータ取得と DuckDB への保存（冪等）
- ニュースの収集・前処理・LLM による銘柄別センチメント付与
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 監査ログ（シグナル→発注→約定）のテーブル定義と初期化
- ファクター計算・特徴量探索（Research 用ユーティリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API とのやり取り（認証、ページネーション、レート制限、保存）
  - pipeline: ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策、トラッキング除去、gzip 対応）
  - calendar_management: JPX カレンダー管理・営業日判定（next/prev/get_trading_days 等）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 監査ログスキーマ定義と初期化（signal_events, order_requests, executions）
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp: ニュース記事を LLM（gpt-4o-mini）で銘柄ごとにセンチメント評価し ai_scores に書き込む（score_news）
  - regime_detector: ETF (1321) の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に書き込む（score_regime）
- research/
  - factor_research: momentum, value, volatility 等のファクター算出
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー等
- config.py: .env 自動ロード・環境変数管理（settings オブジェクト）
- package 初期化: kabusys.__version__ 等

---

## 前提 / 必要環境

- Python 3.10 以上（型文法・typing の利用に合わせる）
- 必須ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、外部 RSS、OpenAI API）

※ 実行環境に応じて追加パッケージ（slack 用、sqlite 等）が必要になる場合があります。

---

## セットアップ手順（例）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. 環境変数設定（必須・推奨）
   - 必須（core 機能を使う場合）:
     - JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（ETL 用）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（取引連携用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
   - AI 機能を使う場合:
     - OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime）
   - DB パス（オプション、デフォルトを使用する場合は不要）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. .env の自動ロードについて
   - kabusys.config はプロジェクトルート（.git または pyproject.toml を探索）を基に .env / .env.local を自動で読み込みます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（主にテスト用途）。

---

## 使い方（代表的な例）

以下は主要 API の簡単な使用例です。各関数は duckdb 接続オブジェクト（duckdb.connect() の返り値）を受け取ります。

1) DuckDB 接続と ETL の実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの AI スコアリング（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn: duckdb connection
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```
- api_key を None にすると環境変数 OPENAI_API_KEY が使用されます。
- LLM 呼び出しが失敗してもフェイルセーフで処理を継続する設計です。

3) 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルへアクセス可能
```

5) ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

---

## テスト / モックについて（ヒント）

- news_nlp._call_openai_api や regime_detector._call_openai_api は直接 OpenAI 呼び出しを行うため、ユニットテストでは unittest.mock.patch で差し替えてレスポンスを返すのが推奨です。
- 環境変数の自動ロードが干渉する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットして無効化してください。
- ETL や保存関数は冪等に設計されています。DuckDB の一部バージョン特性（executemany に空リストが不可等）に注意してテストデータを用意してください。

---

## 主要なディレクトリ構成

（src/kabusys 配下の要約）

- kabusys/
  - __init__.py
  - config.py                        — 環境変数 / settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP（score_news）
    - regime_detector.py              — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - pipeline.py                     — ETL パイプライン（run_daily_etl など）
    - news_collector.py               — RSS 収集・前処理
    - calendar_management.py          — 市場カレンダー管理（営業日判定）
    - quality.py                      — データ品質チェック
    - stats.py                        — 統計ユーティリティ（zscore）
    - audit.py                        — 監査ログテーブル定義・初期化
    - etl.py                          — ETLResult のエクスポート
  - research/
    - __init__.py
    - factor_research.py              — momentum/value/volatility 等
    - feature_exploration.py          — forward returns, IC, summary, rank

---

## 実装上の注意点 / 設計方針（抜粋）

- Look-ahead bias を避ける設計：多くの関数は date.today() を内部で参照せず、target_date を明示的に受け取る。
- 冪等性：J-Quants から保存する関数は ON CONFLICT DO UPDATE を使って重複を抑止。
- フェイルセーフ：外部 API（OpenAI、J-Quants、RSS）の部分は失敗しても例外を投げず適切にログを残して継続する設計が多い（ただし重大な DB 書き込み失敗は例外を伝播）。
- セキュリティ：news_collector では SSRF 対策、defusedxml を利用した XML パース対策、受信サイズ制限等の防御が組み込まれています。
- リトライとレート制御：J-Quants クライアントはレートリミッタと指数バックオフを実装。OpenAI 呼び出しもリトライの実装がある（news_nlp / regime_detector）。

---

もし README に追加したい具体的な手順（CI、ローカル開発ワークフロー、デプロイ、Slack 通知設定等）があれば教えてください。必要に応じてサンプル .env.example や簡易の requirements.txt、docker-compose 例も作成できます。