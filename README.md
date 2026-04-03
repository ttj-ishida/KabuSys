# KabuSys

日本株向け自動売買 / データ基盤ライブラリ（KabuSys）。  
ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどのユーティリティを提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要なユースケース/コード例）
- ディレクトリ構成（主要ファイルと説明）
- 環境変数一覧（必須／任意）
- 補足

---

## プロジェクト概要

KabuSys は日本株の自動売買システムや研究プラットフォームを構築するためのモジュール群です。  
主に以下を目的としています：

- J-Quants API からのデータ取得（株価、財務、JPX カレンダー）
- DuckDB を用いたデータ保存・ETL
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメント（銘柄別）スコアリング
- 市場レジーム判定（ETF + LLM センチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化

設計上、バックテストでのルックアヘッドバイアスを避けるために日時参照やクエリには注意が払われています（target_date を引数で明示する設計など）。

---

## 機能一覧

主な機能（モジュール）：
- kabusys.config: 環境変数の読み込み・設定管理（.env 自動ロード、必須変数チェック）
- kabusys.data:
  - jquants_client: J-Quants API との通信（レート制御、リトライ、トークン管理）、DuckDB への保存ユーティリティ
  - pipeline / etl: 日次 ETL パイプラインと個別 ETL ジョブ（prices / financials / calendar）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF対策、トラッキングパラメータ除去）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - stats: 汎用統計（Zスコア正規化等）
  - audit: 監査ログ用のDDL / 初期化ユーティリティ（init_audit_schema / init_audit_db）
- kabusys.ai:
  - news_nlp.score_news: ニュースを銘柄別に集約して OpenAI でセンチメントを評価し ai_scores に保存
  - regime_detector.score_regime: ETF(1321)のMA乖離とニュースマクロセンチメントを合成して market_regime に保存
- kabusys.research:
  - factor_research: calc_momentum / calc_value / calc_volatility 等
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank 等

---

## セットアップ手順

前提:
- Python 3.9+（プロジェクトでのバージョン指定があればそれに合わせてください）
- DuckDB（Python パッケージで利用）
- OpenAI SDK（gpt- 系を利用する場合）
- defusedxml（RSS 安全パース）

例：最小インストール手順（プロジェクトルートで）
1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトを editable インストールする場合）
   - pip install -e .

3. 環境変数 / .env 準備
   - プロジェクトルートに `.env` と `.env.local` を置けます。
     読み込み優先順位は: OS環境変数 > .env.local > .env
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主要な環境変数は README 下部の「環境変数一覧」を参照してください。

4. データディレクトリ作成（例）
   - mkdir -p data

5. 監査 DB 初期化（任意）
   - Python REPL 等で:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主要な例）

※ すべての関数は明示的に DuckDB の接続や target_date を受け取る設計になっており、ルックアヘッドバイアスを防ぎます。

1) 設定の参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

2) DuckDB 接続を開く
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

3) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定しなければ今日が対象
res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
```

4) ニュースセンチメント（銘柄別）スコア算出
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で渡す
n = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"scored {n} codes")
```

5) 市場レジーム判定（ETF 1321 + LLM）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
# market_regime テーブルに結果が書き込まれます
```

6) 監査 DB 初期化（ファイル）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

7) 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

results_mom = calc_momentum(conn, target_date=date(2026,3,20))
results_val = calc_value(conn, target_date=date(2026,3,20))
```

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイルと役割（src/kabusys 以下）:

- __init__.py
  - パッケージメタ情報（__version__）と公開サブパッケージ指定
- config.py
  - .env 自動読み込み、Settings クラス（環境変数アクセス）
- ai/
  - __init__.py
  - news_nlp.py : ニュースを銘柄ごとに集約して OpenAI でスコアリングし ai_scores に書き込む
  - regime_detector.py : ETF(1321)のMA乖離とマクロニュースを合成して market_regime に書き込む
- data/
  - __init__.py
  - jquants_client.py : J-Quants API 呼び出し、保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）および ETLResult データクラス
  - etl.py : ETLResult の再エクスポートインターフェース
  - quality.py : データ品質チェック（欠損、スパイク、重複、日付不整合）
  - news_collector.py : RSS フィード取得と raw_news 保存（SSRF対策など）
  - calendar_management.py : JPX カレンダー管理・営業日判定
  - stats.py : zscore_normalize 等の統計ユーティリティ
  - audit.py : 監査ログ用 DDL／初期化関数（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py : モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py : 将来リターン / IC / 統計サマリー 等

（全文は src/kabusys 以下に実装ファイルがあります）

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
  - 説明: J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。

任意だが推奨・使用される:
- KABU_API_PASSWORD
  - kabuステーション API 用パスワード
- KABU_API_BASE_URL
  - デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY
  - OpenAI 呼び出し時に使用。score_news / score_regime は api_key 引数でも指定可。
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - LINE 通知のための設定（任意）
- DUCKDB_PATH
  - デフォルト: data/kabusys.duckdb
- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - 監視/プロセスマネジメント用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - 監視しきい値
- KABUSYS_ENV
  - 有効値: development / paper_trading / live（デフォルト development）
- LOG_LEVEL
  - 有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

.env 自動読み込み:
- 起動時にプロジェクトルート（.git または pyproject.toml を持つディレクトリ）を探索し、
  OS環境変数 > .env.local > .env の順でロードします。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 補足 / 注意点

- OpenAI の呼び出しは gpt-4o-mini を想定した JSON mode を用いており、API の成功・失敗に対するフェイルセーフ（失敗時はゼロやスキップ）を基本方針としています。
- J-Quants API との通信はレート制限（120 req/min）とリトライロジックを組み込んでいます。403/401 や 5xx に対するハンドリングもあります（401 はトークン自動リフレッシュ）。
- DuckDB の executemany は空パラメータで失敗するバージョンがあるため、コード内で空リストを渡さないよう対策があります。
- 監査ログスキーマは冪等に作成可能。init_audit_db はファイルの親ディレクトリを自動作成します。
- RSS 取得は SSRF/内部アドレス対策や XML 安全パーサ（defusedxml）を使用しています。

---

もし README に追加したいデプロイ手順や CI、テストの実行例や、より詳細な API ドキュメント（各 DB テーブルスキーマや SQL の説明）が必要であれば、その内容に合わせてセクションを追加します。どの情報を優先して追記しますか？