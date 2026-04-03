# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants などの外部データソースからの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレース）等を備え、バックテスト／運用パイプラインの基盤として利用できます。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API障害時に安全にフォールバック）」「DuckDB を用いたローカル DB 管理」です。

---

## 主な機能一覧

- 環境設定管理（.env 自動ロード / Settings クラス）
- J-Quants API クライアント（差分フェッチ、リトライ、レート制御、保存）
  - 株価日足（OHLCV）、財務データ、JPX カレンダー、上場銘柄情報取得
- ETL パイプライン（日次 ETL、差分取得、品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS → raw_news、SSRF対策、正規化）
- ニュース NLP（OpenAI を使った銘柄別センチメントスコアの作成）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの組合せ）
- 監査ログ（signal → order_request → execution をトレースするスキーマ定義・初期化）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー）
- DuckDB ベースのローカル DB 操作ユーティリティ

---

## 動作環境・依存

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib 等を使用（追加の HTTP ライブラリは必須ではありません）

（実際の requirements はプロジェクトの requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```

3. パッケージのインストール（開発モード）
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   pip install -e .
   ```
   ※requirements.txt / pyproject.toml があればそれを利用してください。

4. 環境変数 (.env) の準備
   - プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（CWD ではなくパッケージ位置からプロジェクトルートを探索）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   重要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabu API パスワード（発注連携等で使用）
   - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector を使う場合）
   - LOG_LEVEL             : ログレベル（例: INFO）
   - KABUSYS_ENV           : operating env（development / paper_trading / live）

   任意（デフォルトを持つ）:
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH など

---

## 使い方（簡単な例）

以下は典型的な利用例です。必要な環境変数を設定の上で実行してください。

- DuckDB 接続の作成と日次 ETL の実行
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP（OpenAI を用いて銘柄ごとのスコアを ai_scores テーブルへ書き込む）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境に設定されていることが必要
written = score_news(conn, target_date=date(2026, 3, 19))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が必要（または api_key 引数で渡す）
score_regime(conn, target_date=date(2026, 3, 19))
```

- 監査ログ DB の初期化（専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # または別ファイルパス
# audit_conn を使って監査テーブルが作成されています
```

- RSS フィードの取得（ニュースコレクタの低レベル呼び出し）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- AI を使う機能（news_nlp, regime_detector）は OpenAI API キーが必要です。
- ETL / 保存関数は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）を前提に動きます。初回はスキーマ初期化が必要な場合があります（プロジェクトの schema 初期化機能を使ってください）。

---

## 設定（Settings モジュール）

kabusys.config.Settings が設定値をラップしています。主なプロパティ:

- jquants_refresh_token
- kabu_api_password
- kabu_api_base_url
- line_channel_access_token, line_user_id
- duckdb_path, sqlite_path
- pid_file_path, kill_flag_path, kill_flag_clear_on_start
- cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
- env, log_level, is_live, is_paper, is_dev

.env の自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）から `.env` → `.env.local` の順で行われます。既存 OS 環境変数は保護されます。

---

## ディレクトリ構成（抜粋）

以下はこのリポジトリの主要なモジュールとファイルの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（銘柄別 AI スコア生成）
    - regime_detector.py            — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント / 保存ロジック
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL 公開インターフェース（ETLResult 再エクスポート）
    - calendar_management.py        — 市場カレンダー管理 / 営業日判定
    - news_collector.py             — RSS → raw_news 収集と保存（SSRF 対策等）
    - quality.py                    — データ品質チェック
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（Momentum / Value / Volatility 等）
    - feature_exploration.py        — 将来リターン / IC / 統計サマリー
  - (strategy/, execution/, monitoring/ 等のサブパッケージを含む設計。実装はモジュールによる)

各ファイルには詳細な docstring と設計方針が記載されています。処理の多くは DuckDB 接続を受け取り SQL と Python を組み合わせて実行します。

---

## 運用上の注意

- Look-ahead バイアス防止のため、本ライブラリの多くの関数は内部で datetime.today() / date.today() を直接参照しません。呼び出し側で target_date を明示して利用してください。
- AI（OpenAI）呼び出しはレートやエラーに対するリトライ・フェイルセーフ実装がありますが、コストとレイテンシに注意してください。
- J-Quants API にはレート制限があるため、fetch 周りは組み込みの RateLimiter によって制御されます。
- ETL 実行時、データ品質チェックの結果（QualityIssue）を基に運用上の判断（アラート、停止など）を行ってください。

---

## 貢献・開発

- コードスタイル、テスト、CI 等の規約に従ってプルリクエストを提出してください。
- `.env.example` を用意し、必須項目を明示してください（リポジトリに例ファイルがない場合は README を参考に追加してください）。
- テストを書く際は Settings の自動 .env ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると良いです。

---

以上。必要であれば README に含めるサンプル .env.example や、追加のコマンドラインツール（スクリプト）利用方法、テーブルスキーマ初期化手順などを追記します。どの項目を詳しく載せたいか教えてください。