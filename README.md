# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
主にデータ取得（J-Quants）、データ品質チェック、特徴量計算、ニュースセンチメント（OpenAI）を通じた銘柄スコアリング、監査ログ（発注／約定トレース）の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API からの差分 ETL（株価日足、財務、カレンダー）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と LLM を用いたニュースセンチメント（銘柄単位）
- 市場レジーム判定（ETF MA 乖離 + マクロニュースセンチメント）
- リサーチ用のファクター計算・特徴量探索ユーティリティ
- 監査（audit）テーブルを用いたシグナル→発注→約定のトレーサビリティ
- DuckDB を利用したローカル DB を主データストアとする設計

設計上の特徴：
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を直接参照しない設計）
- API 呼び出しに対するリトライ・レート制御・フェイルセーフ（失敗時はスキップ／デフォルト値）
- DuckDB への冪等保存（ON CONFLICT DO UPDATE 等）を多用

---

## 機能一覧（モジュール別）

- kabusys.config
  - 環境変数読み込み（プロジェクトルートの .env / .env.local を自動ロード、無効化可）
  - settings オブジェクト経由で設定取得（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レートリミット・リトライ）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl 等）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - news_collector: RSS 収集と raw_news への保存（SSRF / XML 攻撃対策済み）
  - calendar_management: JPX カレンダー管理・営業日判定ヘルパ
  - audit: 監査ログスキーマの初期化（signal_events / order_requests / executions）
  - stats: zscore_normalize などの統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント算出 → ai_scores 書き込み（OpenAI）
  - regime_detector.score_regime: ma200 乖離 + マクロセンチメント合成による market_regime 書き込み
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

以下は開発／実行に必要な最小手順の例です。実際の依存パッケージはプロジェクトに合わせて調整してください。

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境作成 & 有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   > 実際は requirements.txt / pyproject.toml を参照してください。上記は主要依存の一例です。

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env`（およびテスト用に `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env に最低限必要な変数（.env.example を参考に作成）
- JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
- OPENAI_API_KEY=あなたのOpenAIキー
- KABU_API_PASSWORD=（kabuステーション連携時に必要）
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development

5. DuckDB 用ディレクトリ作成
   - mkdir -p data

---

## 必須/推奨環境変数

主要な設定は `kabusys.config.settings` 経由で取得します。主な環境変数:

必須（機能利用時）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY: OpenAI 呼び出しを使う場合に必要（news_nlp/regime_detector）

kabu（証券連携）:
- KABU_API_PASSWORD
- KABU_API_BASE_URL（任意、デフォルト http://localhost:18080/kabusapi）

通知（任意）:
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID

データベース / 監視:
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等

システム設定:
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

詳細は kabusys/config.py を参照してください。

---

## 使い方（代表的なスニペット）

以下はライブラリの代表的な使い方例です。実行前に .env 等で必要な設定を行ってください。

1) DuckDB 接続を作って ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使う例
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

# 今日の ETL（target_date を指定することで過去日にも対応）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み件数: {written}")
```

3) 市場レジームを判定して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログスキーマを初期化（監査用 DB を別に作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を保持して order_requests / executions 等を利用
```

5) カレンダージョブ（JPX カレンダーを更新）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print(f"保存件数: {saved}")
```

注意:
- OpenAI 呼び出しを行う関数は api_key を引数で注入可能（テスト用）。引数未指定なら環境変数 OPENAI_API_KEY を使用します。
- J-Quants 呼び出しは内部でリフレッシュトークンを使って id_token を取得します（settings.jquants_refresh_token）。

---

## ディレクトリ構成

主要ファイル／ディレクトリの一覧（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - quality.py
      - stats.py
      - news_collector.py
      - calendar_management.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/      (パッケージ一覧に含まれる想定、実装はここに)
    - strategy/        (戦略層はここに実装を置く想定)
    - execution/       (発注実行層はここに実装を置く想定)

各ファイルはそれぞれの責務（ETL、品質チェック、AI スコアリング、監査ログ）に分離されています。詳細な関数一覧やパラメータは該当ソース（上記 path）を参照してください。

---

## 開発上の注意点 / 設計メモ

- ルックアヘッドバイアスを防ぐため、関数の多くは target_date を明示的に受け取り、内部で現在日時を参照しない設計です。バックテストや再現性のため、必ず target_date を明示することを推奨します。
- OpenAI への問い合わせは JSON Mode を使いレスポンスのバリデーションを行っており、パース失敗時はフォールバック（スコア 0.0 やスキップ）を行います。
- J-Quants クライアントはレート制限（120 req/min）を尊重する RateLimiter と、401 の自動リフレッシュ、リトライロジックを含みます。
- news_collector は RSS の SSRF/大容量対策 / XML 攻撃対策（defusedxml）を行っています。

---

## 参考 / トラブルシューティング

- 環境変数が不足していると Settings が ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。.env.example を参考に .env を用意してください。
- 自動で .env を読ませたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
- DuckDB ファイルパスは settings.duckdb_path を使うのが簡便です（デフォルト data/kabusys.duckdb）。

---

必要があれば README に「インストールできる requirements.txt の候補」や、より詳細な API リファレンス（各関数の引数と戻り値）を追加します。どの部分を詳しく追記したいか教えてください。