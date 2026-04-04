# KabuSys

日本株向け自動売買/データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（DuckDB）などを一貫して提供します。

---

## 主な概要

KabuSys は以下を目的としたモジュール群を含むパッケージです。

- J-Quants API からのデータ取得と DuckDB への保存（株価・財務・マーケットカレンダー）
- 日次 ETL パイプライン（差分取得 / 品質チェック）
- ニュース収集（RSS）とニュースの NLP（OpenAI を使用）による銘柄別スコアリング
- 市場レジーム判定（MA とマクロニュースの合成評価）
- 監査ログ（signal → order_request → execution）のスキーマ初期化・管理
- 研究用ユーティリティ（ファクター計算 / 統計）

パッケージのバージョンは src/kabusys/__init__.py の `__version__` で管理しています（現行: 0.1.0）。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須値取得（未設定時は例外）
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - レート制限と自動トークンリフレッシュ、リトライ付き
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（kabusys.data.quality）
  - ETL 結果の dataclass (ETLResult)
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、前処理）と raw_news への保存ロジック
- NLP（kabusys.ai.news_nlp）
  - OpenAI を使った銘柄別ニュースセンチメント（score_news）
  - window 計算・バッチ処理・レスポンス検証・リトライ実装あり
- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離 + マクロニュース（LLM）を合成して market_regime に保存（score_regime）
- 研究ユーティリティ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（kabusys.data.stats）
- 監査ログ（kabusys.data.audit）
  - 監査用テーブル DDL と初期化関数 init_audit_db / init_audit_schema

---

## セットアップ手順

前提:
- Python 3.10+（typing|union の表記や型ヒントを多用）
- DuckDB を利用（内部の duckdb パッケージ）

推奨インストール手順（開発時）:

1. リポジトリをクローン:
   git clone <repository-url>
2. 仮想環境を作成・有効化（例: venv / pyenv / poetry 等）:
   python -m venv .venv
   source .venv/bin/activate
3. 依存パッケージをインストール:
   pip install duckdb openai defusedxml
   （必要に応じて他のパッケージを追加してください）

4. パッケージを editable インストール（任意）:
   pip install -e .

環境変数 / .env:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可）。
- 主要な環境変数（最低限必要なもの）:

  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、ETL や jquants_client で使用）
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
  - KABU_API_PASSWORD: kabu API 用パスワード（注文連携がある場合）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID / PID_FILE_PATH / KILL_FLAG_PATH / CPU_THRESHOLD_PCT 等

例（.env）:
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

注意:
- settings（kabusys.config.Settings）は未設定の必須環境変数を参照すると ValueError を送出します。

---

## 使い方（基本例）

以下はパッケージ内の主な機能を使うための簡単なコード例です。

1) DuckDB 接続を作って ETL を実行する:

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を省略すると today が使用されます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースをスコアリングする（OpenAI APIキーが必要）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"scored {n_written} symbols")
```

3) 市場レジームを判定して保存する:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を利用
```

4) 監査ログ DB を初期化する:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
```

5) RSS 取得（ニュース収集のユーティリティ）:

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## よくあるワークフロー

- バックグラウンド/スケジューラで daily ETL（run_daily_etl）を実行して DuckDB を更新
- ニューススコア（score_news）とレジーム判定（score_regime）を毎朝実行してモデル入力を準備
- 研究環境で kabusys.research のファクター計算を使って特徴量検証・IC 計算を行う
- オーダー関連は監査ログ（signal_events / order_requests / executions）でトレースし、実行中の監視は settings の閾値を用いる

---

## 環境設定の自動ロードについて

- .env/.env.local をプロジェクトルート（.git または pyproject.toml がある場所）から自動読み込みします。
- ロード順序: OS 環境 > .env.local（override）> .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利です）。

---

## ディレクトリ構成（概要）

以下は src/kabusys の主要ファイル・モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュース NLP / score_news
    - regime_detector.py           -- 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（fetch/save）
    - pipeline.py                  -- ETL パイプライン / run_daily_etl
    - etl.py                       -- ETLResult 再エクスポート
    - news_collector.py            -- RSS 収集ユーティリティ
    - calendar_management.py       -- マーケットカレンダー管理
    - quality.py                   -- データ品質チェック
    - stats.py                     -- zscore_normalize 等の統計ユーティリティ
    - audit.py                     -- 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py           -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py       -- calc_forward_returns / calc_ic / factor_summary / rank

この README に含まれていないヘルパーモジュールや細部の関数はソースを参照してください。各モジュールはドキュメンテーション文字列（docstring）で設計方針・前提・返値を詳細に説明しています。

---

## 注意事項 / ベストプラクティス

- OpenAI や J-Quants の API キーは秘匿情報です。共有リポジトリに含めないでください。
- バックテスト等で Look-ahead bias を避けるため、関数群は基本的に target_date を引数に取り、内部で現在時刻を参照しない設計となっています。必ず適切な target_date を渡してください。
- DuckDB の executemany に関するバージョン依存の挙動（空リスト不可など）に注意しています（コード内で対処済み）。
- 大量 API 呼び出し（J-Quants / OpenAI）に対してはレート制限およびリトライが実装されていますが、運用時は実際のレート制限に合わせて運用ポリシーを検討してください。

---

必要に応じて README に追加したい説明（例: 各テーブルのスキーマ、サンプル .env.example、CI / テストの実行方法など）があれば教えてください。