# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、ファクター計算、監査ログ（注文→約定のトレーサビリティ）など、アルゴリズム取引・リサーチに必要な機能をモジュール化して提供します。

バージョン: 0.1.0

---

## 概要（Project Overview）

KabuSys は以下の機能を提供します。

- J-Quants API からのデータ取得（株価日足・財務・上場情報・マーケットカレンダー）
- DuckDB を利用した ETL パイプライン（差分取得、冪等保存、品質チェック）
- RSS ベースのニュース収集（安全対策付き）とニュース → 銘柄マッピング
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント＆市場レジーム判定（フェイルセーフ・リトライ実装）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ（Zスコア等）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の留意点：
- ルックアヘッドバイアスを防止する設計（内部で date.today()/datetime.today() を直接使わない等）
- API 呼び出しは冗長性（リトライ・バックオフ）とレート制御を備える
- DB 書き込みは冪等性（ON CONFLICT）を重視

---

## 機能一覧（Features）

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存関数、トークン自動リフレッシュ、レート制御）
  - ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去）
  - カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - 品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None)：ニュース文章を LLM に投げて銘柄別センチメントを ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None)：ETF（1321）200日MA乖離とマクロニュースで市場レジームを判定して market_regime に保存
- research/
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順（Setup）

前提
- Python 3.9+（ソースで型アノテーションと typing を使用）
- DuckDB（Python パッケージ duckdb）
- OpenAI Python ライブラリ（openai）
- defusedxml（RSS の安全パース）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

推奨手順（ローカル開発）:

1. リポジトリをクローン
   - git clone ...（既にパッケージソースをお持ちの場合はスキップ）

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 要件ファイルがある場合:
     - pip install -r requirements.txt
   - または開発インストール:
     - pip install -e .

   必要な主なパッケージ:
   - duckdb
   - openai
   - defusedxml

4. 環境変数の設定（.env をプロジェクトルートに置くか、OS 環境変数を利用）
   必須（主要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN: Slack 通知（必要な場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に引数で渡すことも可能）
   任意:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト INFO）

   自動 .env ロード:
   - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動読み込みします。
   - テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DuckDB データベース用ディレクトリを作成（自動で作られますが念のため）
   - mkdir -p data

---

## 使い方（Usage）

以下は主要 API の簡単な使用例です。各関数は DuckDB 接続（duckdb.connect(...) が返す接続）を受け取ります。

1) DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 監査ログ DB の初期化（監査用専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(settings.duckdb_path)  # :memory: を渡せばインメモリ
```

3) 日次 ETL を実行（市場カレンダー・株価・財務の差分取得＋品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を指定すればその日を対象
print(result.to_dict())
```

4) ニュースセンチメントを取得して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

5) 市場レジームスコアを計算して market_regime に書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

6) ファクター計算・研究ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
zrecords = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点 / 実運用での推奨:
- OpenAI 呼び出しは API コストとレート制限があるため、API キー・バッチサイズ・リトライ設定を考慮してください。
- score_news / score_regime は LLM 呼び出しの失敗やパース失敗をフェイルセーフで扱い、失敗があっても例外を上げずスキップする設計です（ログを確認してください）。
- run_daily_etl は各ステップで個別に例外処理を行い、片方の失敗で全体が止まらないようになっています。結果は ETLResult で確認できます。

---

## ディレクトリ構成（Directory structure）

以下はパッケージ内の主なモジュールと役割（抜粋）です。実際のファイルは src/kabusys 以下にあります。

- src/kabusys/
  - __init__.py — パッケージ初期化（__version__ 等）
  - config.py — 環境変数/設定の読み込み・検証（.env 自動ロード、settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントスコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得＋DuckDB 保存）
    - pipeline.py — ETL パイプラインのエントリ（run_daily_etl 等）と ETLResult
    - etl.py — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py — RSS 収集と前処理
    - calendar_management.py — 市場カレンダーの管理（営業日判定等）
    - quality.py — データ品質チェック（欠損 / スパイク / 重複 / 日付整合性）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ作成 & 初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー等

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY (必須 for AI): OpenAI API キー（score_news / score_regime を使う場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (任意): Slack 通知用
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite パス（モニタリング用、デフォルト data/monitoring.db）
- KABUSYS_ENV (任意): development | paper_trading | live（検証・制御フラグ）
- LOG_LEVEL (任意): ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読み込みを無効化

---

## テスト・デバッグに関する補足

- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しなどはモジュール内の _call_openai_api をテストでモックできるように設計されています。
- ネットワーク系（RSS、J-Quants、OpenAI）はリトライ・バックオフ・タイムアウトのロジックが入っていますが、テストではモック化を推奨します。

---

## 運用上の注意

- LIVE 環境での発注・実行ロジックは別モジュール（execution/strategy 等）で統合する前提です。本リポジトリのコードはデータ取得・解析・監査スキーマ周りが中心です。
- 実際に発注や資金管理を行う場合は、リスク管理・二重発注防止・冪等性の確認を慎重に行ってください。
- OpenAI の出力は常に検証（型・レンジ）されますが、LLM の誤応答リスクはゼロではありません。自動売買の意思決定に使う場合はヒューマンインザループや安全弁を設けてください。

---

README で足りない詳細（例: 追加のコマンドやスキーマ定義、実際の ETL スケジューリング例など）が必要であれば、用途に合わせてサンプルコマンドやワークフローを追記します。必要な情報を教えてください。