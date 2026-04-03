# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤のライブラリ（モジュール群）。  
ETL（J-Quants）・ニュース収集・AI ベースのニュースセンチメント/市場レジーム判定・ファクター計算・データ品質チェック・監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買システムやリサーチ基盤を構築するための内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得（ETL）
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別）およびマクロセンチメントを組み合わせた市場レジーム判定
- ファクター（モメンタム・ボラティリティ・バリュー等）の算出と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）のためのスキーマ初期化ユーティリティ

設計上の特徴：
- Look-ahead bias 回避のため、内部処理は明示的な target_date を利用（date.today() を直接参照しない設計が多く採用されています）
- DuckDB を用いたローカルデータ保存と SQL ベースの高速処理
- 冪等性を考慮した保存ロジック（ON CONFLICT / DELETE→INSERT パターン）
- API 呼び出しに対するリトライ／バックオフとレート制御

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants からのデータ取得（株価・財務・カレンダー）と DuckDB へ保存
  - pipeline: 日次 ETL のエントリ（run_daily_etl）と個別 ETL ジョブ
  - news_collector: RSS 取得、前処理、raw_news への保存（SSRF 対策、サイズ制限、トラッキング除去等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダーの管理と営業日判定ユーティリティ
  - audit: 監査ログテーブルのスキーマ初期化（冪等）
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメント算出 → ai_scores へ保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュース LLM スコアの合成による市場レジーム判定 → market_regime へ保存
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility 等
  - feature_exploration: 将来リターン計算、IC、統計サマリー等

---

## セットアップ手順（ローカル開発）

前提
- Python 3.9+（コードは型注釈で Python 3.10 以降の機能を使う部分があるため、3.10+ 推奨）
- DuckDB が動作する環境

1. リポジトリをクローンしてプロジェクトルートへ移動
   - （本 README は `src/kabusys` 配下のモジュールを前提としています）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクトで requirements.txt があればそれを利用してください）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - KABU_API_BASE_URL: (任意) kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: （任意）通知用
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, 他システム設定
   - サンプル .env 行例:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb

5. （オプション）プロジェクトを editable install
   - pip install -e .

---

## 使い方（主要な関数と簡単なコード例）

※ いずれも DuckDB 接続には `duckdb.connect(settings.duckdb_path)` 等を利用します。

1) 日次 ETL の実行（pipeline.run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントの生成（AI）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数または api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 必要に応じてこの conn をアプリケーションの監査用接続として利用
```

5) ファクター計算（Research）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect(str(settings.duckdb_path))
results = calc_momentum(conn, target_date=date(2026, 3, 20))
# results は各銘柄ごとの dict リスト
```

6) データ品質チェック
```python
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect(str(settings.duckdb_path))
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for issue in issues:
    print(issue)
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu ステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う際に必要）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
- その他: PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT 等（監視設定）

.env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。

---

## ディレクトリ構成（主要ファイルの説明）

（以下は `src/kabusys` 配下の主要モジュール）

- __init__.py
  - パッケージエントリ（__version__ 等の公開）

- config.py
  - 環境変数読み込み・Settings クラス（設定プロパティ）を提供
  - .env 自動ロードロジックと必須値チェック

- ai/
  - news_nlp.py
    - 銘柄別ニュースを集約し OpenAI（gpt-4o-mini）で評価、ai_scores テーブルへ書込
    - calc_news_window, score_news 等
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime へ書込

- data/
  - jquants_client.py
    - J-Quants への HTTP クライアント（認証・ページネーション・リトライ・レート制御）
    - fetch/保存関数（fetch_daily_quotes / save_daily_quotes / fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar / fetch_listed_info）
  - pipeline.py
    - run_daily_etl を含む ETL パイプラインと個別 ETL ジョブ
    - ETLResult 型
  - news_collector.py
    - RSS から記事を取得・前処理して raw_news に保存（SSRF/サイズ対策等）
  - quality.py
    - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - calendar_management.py
    - market_calendar 管理と営業日判定ユーティリティ
  - audit.py
    - 監査ログ用スキーマ定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - etl.py
    - ETLResult の再エクスポート（API 的便宜）

- research/
  - factor_research.py
    - calc_momentum / calc_value / calc_volatility（prices_daily / raw_financials ベース）
  - feature_exploration.py
    - calc_forward_returns / calc_ic / rank / factor_summary
  - __init__.py
    - 研究用 API の再エクスポート

- ai/__init__.py, research/__init__.py, data/__init__.py
  - サブパッケージのエクスポート設定

---

## 注意事項 / 運用上のポイント

- OpenAI 呼び出しや外部 API（J-Quants）を使う機能は API キーやトークンを必ず設定してください。コード内では api_key 引数で明示的に渡すことも可能です（テストの容易化のため）。
- ETL と AI スコアリングは Look-ahead bias 回避のため target_date を明示して実行することを推奨します。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョン依存の挙動があるため、モジュール内で保護処理が入っています。運用環境の DuckDB バージョンによる差異に注意してください。
- news_collector は RSS の取得で SSRF 対策・応答サイズ制限・XML 脆弱性対策（defusedxml）等の安全対策を組み込んでいますが、外部ソースの扱いには注意してください。
- 自動ロードされる .env はプロジェクトルート基準です。テストや CI での切り替えは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効にできます。

---

## 貢献 / 開発

- バグ修正、機能追加は PR ベースで受け付けてください。
- 大きな設計変更は事前に issue で相談してください（Look-ahead bias / 冪等性 / トレーサビリティ方針に影響します）。

---

以上がこのコードベースの概要と主要な使い方です。必要に応じて README にサンプル .env.example、requirements.txt、実行スクリプト（CLI）などを追加できます。追加をご希望でしたら教えてください。