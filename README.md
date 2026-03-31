# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL、ニュースNLP（LLM を用いたセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログなどを備え、バックテスト／運用のデータ基盤と戦略研究を支援します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存関係
- セットアップ手順
- 環境変数 (.env) と設定
- 使い方（簡単な実行例）
- ディレクトリ構成（主要ファイル一覧）
- 注意事項 / 設計方針のポイント

---

## プロジェクト概要

KabuSys は日本株向けデータプラットフォームとリサーチ / 自動売買に必要な共通機能を提供する Python パッケージです。主な機能は以下の通りです。

- J-Quants からの差分 ETL（株価日足、財務、JPX カレンダー）
- raw_news の RSS 収集・前処理と LLM を用いたニュースセンチメント（銘柄単位）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution をトレースする監査テーブル）
- DuckDB を中心としたローカルデータベースへの保存・操作

設計上の重要点：
- ルックアヘッドバイアス回避（内部で date.today() 等の直接参照を避け、外部から target_date を注入する形）
- API 呼び出しはリトライやレート制御を組み込み、フェイルセーフ動作（失敗時はスキップして継続）が基本
- 冪等性を意識した DB 保存（ON CONFLICT、明示的な DELETE → INSERT など）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / 認証自動更新 / レート制御）
  - カレンダー管理（営業日判定、次営業日/前営業日取得）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルに書き込み
  - regime_detector.score_regime: ETF 1321 の MA とマクロセンチメントを合成して market_regime テーブルへ書き込み
- research/
  - factor 計算（calc_momentum, calc_value, calc_volatility）
  - feature_exploration（forward returns, IC, summary, rank）
- config.py
  - 環境変数の自動読み込み（.env / .env.local）と Settings API

---

## 前提・依存関係

- Python 3.10 以上（コード内で X | None 型注釈等を使用）
- 必要な主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで動く部分も多いですが、上記は実動作に必要）
- ネットワークアクセス（J-Quants API、RSS、OpenAI API）

requirements.txt がない場合は次のように最低限をインストールしてください（例）:

pip install duckdb openai defusedxml

（プロジェクトで提供する packaging があれば pip install -e . を推奨します）

---

## セットアップ手順

1. リポジトリをクローン / ソースを用意
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - 追加で必要なパッケージがあれば適宜インストールしてください
4. 環境変数を設定（.env をプロジェクトルートに置くことが可能）
   - 必須項目は下記参照（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）
   - 自動ロードは config.py によりプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local が読み込まれます
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. DuckDB の初期化（監査ログ用 DB を作る例）
   - Python REPL またはスクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 環境変数 (.env) — 主要項目

config.Settings から読み込むキー例（必須／デフォルトあり）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、デフォルト: development)
  - 有効値: development / paper_trading / live
- LOG_LEVEL (任意、デフォルト: INFO)
  - 有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY (LLM 呼び出し用。score_news / regime_detectorで使用可能)

.env の簡易例 (.env.example)
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

注意:
- config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込みします。
- テスト時などで自動読み込みを抑えたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（サンプル）

下記は基本的な利用例です。各関数は引数で target_date や API キーを注入でき、ルックアヘッドバイアスを防ぐ設計になっています。

1) DuckDB 接続を作成して日次 ETL を実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 19))
print(result.to_dict())
```

2) ニュース NLP（銘柄ごとのニュースセンチメントを ai_scores に保存）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 19), api_key=None)  # api_key None → OPENAI_API_KEY を使用
print("written:", n_written)
```

3) 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 19), api_key=None)
```

4) 研究系ファクター算出
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 19))
vol = calc_volatility(conn, target_date=date(2026, 3, 19))
val = calc_value(conn, target_date=date(2026, 3, 19))
```

5) 監査DBの初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

---

## ディレクトリ構成（主要ファイル）

以下はパッケージの主要モジュール一覧（src/kabusys 配下）：

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
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult export)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/（公開API）
  - calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank

各モジュールは docstring に詳細な設計意図と注意点が書かれています。実装を読むことで、データの前提（UTC/naive datetime、raw_news の保存フォーマット等）と操作方法が把握できます。

---

## 注意事項 / 設計方針のポイント

- ルックアヘッドバイアス防止:
  - 多くの関数は内部で現在時刻を参照せず、必ず target_date を外部から渡す設計です。バックテスト等では必ず意図した日時を渡してください。
- LLM（OpenAI）呼び出し:
  - score_news / regime_detector は OpenAI の Chat Completions（gpt-4o-mini を想定）を使用します。API キーは OPENAI_API_KEY または関数引数で指定してください。レスポンスのパースや API エラーに対してはフェイルセーフ（0.0 でフォールバック等）処理が組み込まれています。
- DB スキーマ:
  - save_* 関数は冪等になるよう ON CONFLICT 指定等を行っていますが、運用時はスキーマの初期化や監査DBの作成（init_audit_db / init_audit_schema）を忘れないでください。
- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ制限、XML の安全パース（defusedxml）等の実装があります。RSS フィード追加時は信頼できるソースを選んでください。
- 環境別設定:
  - KABUSYS_ENV により開発/ペーパー/ライブの振る舞いを切り替えられます。is_live / is_paper / is_dev プロパティでプログラム内判定が可能です。

---

必要であれば README に「CLI の使い方」「systemd / cron によるジョブ登録例」「詳細な .env.example ファイル」などのセクションを追加できます。どの情報をより詳細に追加したいか教えてください。