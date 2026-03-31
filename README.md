# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータパイプライン、研究用ファクター計算、ニュース NLP（LLM によるセンチメント評価）、市場レジーム判定および監査ログ基盤を提供するライブラリ群です。ETL → 品質チェック → 研究用特徴量計算 → 戦略/監査へと繋がる一連の機能を備え、Look‑ahead bias や冪等性、安全性（SSRF、XML 攻撃、レスポンスサイズ制限）を考慮して設計されています。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API 例）
- 環境変数（.env）
- ディレクトリ構成
- 補足・設計上の注意

---

## プロジェクト概要

主な目的は次の通りです。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）と DuckDB への保存（冪等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と記事→銘柄紐付け（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別）とマクロセンチメントを組み合わせた市場レジーム判定
- 研究用モジュール（ファクター計算・将来リターン・IC・統計サマリ）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用の DuckDB スキーマ初期化ユーティリティ
- J-Quants クライアント（レート制限・リトライ・トークン自動リフレッシュ）

設計方針の例:
- バックテストやモデル検証での Look‑ahead bias 回避（内部で date.today()/datetime.today() を参照しない関数群）
- API 呼び出し失敗時のフェイルセーフ（例: LLM 失敗はスコア 0.0 にフォールバック）
- DuckDB に対しては ON CONFLICT / executemany を利用した冪等保存

---

## 機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン管理、レートリミッタ）
  - calendar_management（営業日判定・next/prev_trading_day 等）
  - news_collector（RSS 収集、前処理、SSRF 対策）
  - quality（品質チェック群と QualityIssue 定義）
  - stats（zscore_normalize 等ユーティリティ）
  - audit（監査ログスキーマの初期化・監査 DB 作成）
- ai/
  - news_nlp.score_news（銘柄別ニュースセンチメントを ai_scores テーブルに書込）
  - regime_detector.score_regime（ETF 1321 の MA200 乖離 + マクロ LLM 評価で市場レジーム判定）
- research/
  - factor_research（モメンタム／ボラティリティ／バリュー等のファクター算出）
  - feature_exploration（将来リターン、IC、統計サマリ、ランク関数）
- config
  - 環境変数の自動ロード（.env / .env.local）・必須変数チェック（Settings クラス）
- utils（ライブラリ内部でのヘルパー群）

---

## セットアップ手順

前提
- Python 3.10+ を推奨
- duckdb / openai / defusedxml 等が必要

1. リポジトリを取得
   - 例: git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - 主要依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください）

4. パッケージをインストール（ローカル開発）
   - pip install -e .

5. 環境変数を設定
   - プロジェクトルートに .env を置くと自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必須環境変数は後述の「環境変数（.env）」参照。

6. DuckDB ファイルや監査 DB を初期化
   - 実行例を次節に記載します。

---

## 使い方（主要 API 例）

以下は基本的な使用例です。各関数は duckdb の接続（duckdb.connect(...)）を受け取ります。

- 設定取得
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
print(settings.env, settings.log_level)
```

- DuckDB 接続作成
```python
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（銘柄別）算出
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY で自動取得するか、api_key 引数を渡す
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム算出
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査 DB 初期化（監査専用 DB を作成してテーブルを作る）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/monitoring.duckdb")
# audit_conn を利用して監査ログ挿入などを行う
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

---

## 環境変数（.env の例）

config.Settings で参照される主な環境変数（必須は明示）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視/モニタリング用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト "development"）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動ロード:
- パッケージはプロジェクトルートにある .env / .env.local を自動でロードします（OS 環境変数優先）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルの説明）

概略（src/kabusys 以下）:

- __init__.py
  - パッケージメタ情報（__version__ = "0.1.0"）

- config.py
  - .env 自動ロード、Settings クラス（各種環境変数の取得・検証）

- ai/
  - __init__.py
  - news_nlp.py
    - 株式ニュースを銘柄ごとに集約し、OpenAI によるセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.py
    - ETF 1321 の MA200 乖離と LLM マクロセンチメントを合成して market_regime に書き込む

- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得 / 保存 / 認証トークン管理 / レート制御）
  - pipeline.py
    - 日次 ETL（run_daily_etl 等）および ETLResult
  - etl.py
    - ETLResult の再エクスポート
  - calendar_management.py
    - market_calendar の管理と営業日判定ロジック
  - news_collector.py
    - RSS 取得、前処理、SSRF 対策、raw_news 保存支援
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py
    - zscore_normalize など汎用統計ユーティリティ
  - audit.py
    - 監査ログスキーマ定義、初期化ユーティリティ（init_audit_schema / init_audit_db）

- research/
  - __init__.py
  - factor_research.py
    - モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py
    - 将来リターン / IC / 統計サマリ / ランク変換

（上記以外に strategy, execution, monitoring などの名前空間を __init__ で公開する意図がありますが、提供コードベースにより差異があります）

---

## 補足・設計上の注意

- Look‑ahead bias 対策
  - 多くの関数で内部的に date.today()/datetime.today() を参照しません。バックテスト時は明示的に target_date を渡してください。
- 冪等性
  - J-Quants からの保存関数は ON CONFLICT DO UPDATE を用いて冪等性を担保します。
- OpenAI 呼び出し
  - news_nlp / regime_detector は gpt-4o-mini を想定しています。レスポンスは JSON モードで期待される形に厳密に整形することを前提にしています。
  - テスト時はモジュール内の _call_openai_api をモックして外部呼び出しを差し替えられます。
- セキュリティ
  - news_collector は SSRF 対策、トラッキングパラメータ削除、XML 脆弱性対策（defusedxml）を備えています。
- ログ・環境
  - settings.log_level でログレベルを制御します。KABUSYS_ENV により動作モード（development/paper_trading/live）を区別できます（is_live 等のプロパティあり）。

---

必要に応じて README にサンプル .env.example、CI / テスト手順、データベーススキーマ（raw_prices, raw_financials, ai_scores, market_regime など）の DDL を追記できます。追加してほしい情報（例: 具体的な requirements.txt、起動スクリプト、データスキーマの完全な DDL 等）があれば教えてください。