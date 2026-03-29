# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリ（KabuSys）。  
ETL（J-Quants からのデータ取得）・ニュース収集・AI（LLM）によるニュースセンチメント判定・市場レジーム判定・リサーチ向けユーティリティ・監査ログ（オーダー追跡）などを提供します。

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得し DuckDB に保存（冪等）。
  - 差分・バックフィルロジック、ページネーション、トークン自動リフレッシュ、レート制御、リトライ実装。
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合の検出（QualityIssue 機構）。
- ニュース収集
  - RSS フィード収集（SSRF 対策、gzip 上限、URL 正規化、トラッキング除去）→ raw_news / news_symbols へ冪等保存する想定。
- AI (LLM) 連携
  - ニュースセンチメント分析（gpt-4o-mini を想定）: 銘柄単位の ai_score を ai_scores テーブルへ保存する `score_news`。
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM センチメントの加重合成）: `score_regime`。
  - OpenAI 呼び出しはリトライとフェイルセーフ（失敗時は中立スコア）を備える。
- 研究（Research）ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）、将来リターン計算、IC（Information Coefficient）や統計サマリー、Zスコア正規化。
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等テーブルを初期化する `init_audit_schema` / `init_audit_db`。
  - オーダー発行〜約定までの一意追跡 (UUID ベース) を想定。
- 設定管理
  - .env / .env.local / 環境変数を自動ロード（プロジェクトルートを .git または pyproject.toml で探索）。自動ロード無効化フラグあり。

---

## 必要条件 / 依存ライブラリ（例）

（プロジェクトに合わせて pyproject.toml / requirements.txt を用意してください。以下は主要依存の例）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

例（requirements.txt）:
```
duckdb
openai
defusedxml
```

---

## 環境変数 / .env

config モジュールは .env（および .env.local）または OS 環境変数から読み込みます。自動ロードはプロジェクトルートを .git / pyproject.toml から探して行われます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須は用途により異なります）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須: J-Quants を使う場合）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携を行う場合）
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視系 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")（デフォルト: INFO）

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール
   - pip install -r requirements.txt
   - もしくは pyproject.toml / poetry / pip install -e .
4. .env をプロジェクトルートに作成し必要な環境変数を設定
5. DuckDB 用ディレクトリを作る（必要に応じて）
   - mkdir -p data

---

## 使い方（主な例）

以下はライブラリ API の利用例です。すべての呼び出しは Look-ahead バイアスに注意し、明示的な target_date を渡すことが推奨されています。

- DuckDB 接続の作成（例）:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（銘柄別）スコア化:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーが環境変数 OPENAI_API_KEY に設定されている前提
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

# api_key を明示することも可能
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンがセットされます
```

- RSS の取得（ニュース収集の一部）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意:
- AI 関連機能（score_news, score_regime）は OpenAI API キーを必要とします（env: OPENAI_API_KEY または api_key 引数）。
- J-Quants 関連機能（ETL 等）は JQUANTS_REFRESH_TOKEN を必要とします。

---

## よく使う関数 / エントリポイント（抜粋）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, id_token=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult クラス（結果と品質チェック情報を含む）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector
  - fetch_rss, preprocess_text, _make_article_id など（公開 API は fetch_rss）
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_duplicates, check_spike, check_date_consistency
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成（概要）

（src 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数と設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント: score_news
    - regime_detector.py            — 市場レジーム判定: score_regime
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py        — マーケットカレンダー管理・営業日判定
    - audit.py                      — 監査ログ（signal/order/execution）スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン, IC, summary, rank
  - monitoring/ (想定の監視系モジュール等)
  - strategy/, execution/ (戦略・実行モジュールは __all__ に含まれる想定)

---

## 実装上の注意 / 設計方針の要点

- Look-ahead bias を避けるため、内部で date.today() を不用意に参照しない設計が各モジュールで徹底されています。バックテストや再現性のために target_date を明示してください。
- DuckDB を主要な永続化ストアとして利用。ETL は冪等（ON CONFLICT）で保存。
- OpenAI 呼び出しは JSON mode を利用しレスポンスを厳密にパース、失敗時は中立にフォールバックするフェイルセーフを持ちます。
- ニュース収集では SSRF 対策・gzip 上限・トラッキング除去などセキュリティ対策を実装。
- ETL・API 呼び出しでのリトライ・レート制御を実装（J-Quants のレート制限等を尊重）。

---

## 追加メモ / 今後の拡張案

- kabuステーション等のブローカー連携モジュール（発注・約定処理）を strategy / execution 層で実装可能。
- Slack 通知や監視ダッシュボード（monitoring）との連携。
- バックテスト用のインターフェース（データスナップショット / 日次差分の再現など）。

---

README に記載した使い方はライブラリの公開 API を簡単に示したものです。詳細な引数仕様や内部挙動は各モジュール（src/kabusys/**）の docstring とログ出力を参照してください。必要なら README に追記・サンプルスクリプトや docker-compose のセットアップ手順も作成できます。ご希望があれば追加で作成します。