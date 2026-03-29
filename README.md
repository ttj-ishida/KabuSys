# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、リサーチ用ファクター計算、監査ログ（トレーサビリティ）、カレンダー管理、品質チェックなどを提供します。

主に DuckDB をデータレイヤに使い、J-Quants / kabuステーション / OpenAI 等の外部サービスと連携する設計です。

---

## 主要な機能一覧

- data
  - ETL パイプライン（prices / financials / calendar）の差分取得と保存（J-Quants）
  - market_calendar の管理（営業日判定、next/prev_trading_day 等）
  - raw_prices / raw_financials / raw_news 等の保存ユーティリティ
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）の初期化・管理
  - ニュース収集（RSS）と前処理（SSRF 対策、トラッキング除去、gzip 対応）
  - J-Quants クライアント（rate-limit / retry / token refresh 対応）
- ai
  - ニュースのセンチメントスコアリング（gpt-4o-mini を JSON mode で利用）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 特徴量探索（将来リターン計算、IC、統計サマリー、ランク）
- utils
  - 統計ユーティリティ（Zスコア正規化等）
- config
  - 環境変数管理（.env 自動読み込み、必須チェック、settings オブジェクト）

設計上の特徴
- ルックアヘッドバイアス防止（内部処理で date.today()/datetime.today() を直接参照しない等）
- フェイルセーフ：外部 API が失敗してもゼロやスキップで継続する箇所がある
- DuckDB を想定した SQL ベースの高速計算
- 冪等性（DB への保存は ON CONFLICT で上書き等）

---

## 必要条件 / 推奨環境

- Python 3.10+（型注釈や | None 型を使用しているため）
- 依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ（urllib 等）

（実際の requirements.txt / pyproject.toml に従ってください。プロジェクト配布時は pyproject.toml を確認してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - pyproject.toml / requirements.txt がある場合はそれに従ってください。
   - 例（手動インストール）:
     ```
     pip install duckdb openai defusedxml
     ```
4. 開発インストール（パッケージが setuptools/poetry 等で構成されている場合）
   ```
   pip install -e .
   ```

5. 環境変数設定（.env）
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が起動時に検出して読み込み）。
   - 自動読み込みを無効にしたい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

例: `.env`（必要なキー）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション（必要に応じて）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# OpenAI
OPENAI_API_KEY=sk-...

# DBパス（省略時はデフォルト）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 動作環境
KABUSYS_ENV=development  # 値: development | paper_trading | live
LOG_LEVEL=INFO
```

必須の環境変数は Settings プロパティでチェックされ、未設定だと ValueError が発生します（config.settings を通して取得）。

---

## 基本的な使い方（例）

以下は主要機能の呼び出し例です。すべて Python スクリプト／REPL から実行できます。

- DuckDB 接続を作る（デフォルトのファイルパスは settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントスコア生成（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 環境変数 OPENAI_API_KEY が設定されていれば api_key は省略可
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DuckDB を使う場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使って監査テーブルにアクセス
```

- 監査スキーマを既存の接続に追加
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意点
- OpenAI 呼び出しは rate / retry を組み込んでいますが、API キーに依存します。api_key を引数で直接渡すことも可能です。
- run_daily_etl 等は内部で ETL の各ステップを個別に try/except で保護しており、部分失敗でも他の処理は継続します。結果は ETLResult にまとめられます。

---

## よく使うモジュール（簡単説明）

- kabusys.config
  - settings: 環境変数ラッパー（必須項目の取得・検証、.env 自動読み込み）
- kabusys.data.jquants_client
  - J-Quants API 呼び出し、保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl、ETLResult
- kabusys.data.quality
  - run_all_checks（欠損・重複・スパイク・日付不整合の検査）
- kabusys.data.news_collector
  - RSS 取得と前処理（fetch_rss 等）
- kabusys.data.calendar_management
  - 営業日判定、next_trading_day / prev_trading_day / get_trading_days、calendar_update_job
- kabusys.data.audit
  - 監査テーブル初期化（init_audit_schema / init_audit_db）
- kabusys.ai.news_nlp
  - score_news（ニュース→銘柄別 ai_score 書き込み）
- kabusys.ai.regime_detector
  - score_regime（ETF + マクロニュースから市場レジーム判定）
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

---

## ディレクトリ構成

（主要ファイルを抜粋）
```
src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      news_collector.py
      calendar_management.py
      quality.py
      stats.py
      audit.py
      (その他データ関連ユーティリティ)
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/
      (ファクター・リサーチ系モジュール)
```

各モジュールは docstring に処理フロー・設計方針を詳述しているため、実装の読み取りが容易です。

---

## 開発 / テストのヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を親として探索）を起点に行われます。CI / テスト環境で明示的に環境変数を操作したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定してください。
- OpenAI 呼び出し部分は _call_openai_api をモックしてテスト可能です（news_nlp/regime_detector 内に注記あり）。
- DuckDB を使うことでテスト用に `:memory:` 接続を渡して動作確認が可能です（例: duckdb.connect(":memory:")）。
- ETL の差分ロジックは最終取得日を参照して動きます。初回は最小日付（_MIN_DATA_DATE）から取得されます。

---

もし README に追加したい具体的な使い方（例: CI のセットアップ、Docker Compose、Slack 通知の設定例、pyproject/requirements の抜粋など）があれば教えてください。必要に応じて .env.example のテンプレートも作成します。