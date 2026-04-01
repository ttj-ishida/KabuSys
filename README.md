# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ。  
J-Quants / JPX からのデータ取得（ETL）、データ品質チェック、ニュースの収集とAIを用いたニュース評価、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注→約定追跡）などのユーティリティをまとめたコードベースです。

---

## 概要

KabuSys は以下の領域をカバーします。

- J-Quants API を用いた株価（OHLCV）・財務データ・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- RSS からのニュース収集と前処理、ニュース・銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（銘柄別）およびマクロニュースを用いた市場レジーム判定
- 研究用ファクター計算・前方リターン・IC（Information Coefficient）計算など
- 監査ログテーブル（signal → order_request → execution）の初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動読み込み）

設計方針として「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API エラーを逐次スキップ）」を重視しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得 / 保存 / 認証 / レート制御 / リトライ）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - ニュース収集（RSS -> raw_news, SSRF対策、前処理）
  - データ品質チェック（missing data, spike, duplicates, date consistency）
  - 監査ログ（init_audit_schema / init_audit_db）
  - 汎用統計: zscore_normalize
- ai
  - news_nlp.score_news(conn, target_date, api_key=None)
    - 銘柄ごとのニュースをまとめて LLM に送りセンチメントを ai_scores テーブルに書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成し market_regime に保存
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数の読取・検証（settings オブジェクト）
  - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
- audit
  - 監査テーブルの DDL とインデックス定義、DB 初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10 以上（型アノテーションに Union 型等を使用）
- DuckDB を使用（Python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS 安全パース）
- ネットワーク接続（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   git clone <REPO_URL>
   cd <repo>

2. 仮想環境を作成・有効化（例）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを利用してください）
   開発インストール:
   pip install -e .

4. 環境変数 / .env の準備
   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` および任意で `.env.local` を配置すると自動で読み込まれます（テスト時など自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   主なキー（.env 例）:

   - JQUANTS_REFRESH_TOKEN (必須)  
     J-Quants のリフレッシュトークン（ETL 実行に必要）
   - OPENAI_API_KEY (必須 for AI functions)  
     OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD (必須)  
     kabuステーション API パスワード（外部発注統合時）
   - KABU_API_BASE_URL (任意)  
     kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須: Slack 通知を使う場合)
   - DUCKDB_PATH (任意) デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) 監視用 DB デフォルト: data/monitoring.db
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト: INFO

   .env のフォーマットは一般的な KEY=VALUE、シングル/ダブルクォートやコメントも一定程度サポートします。

---

## 使い方（主要な呼び出し例）

以下は Python REPL やスクリプトからの呼び出し例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

1) DuckDB 接続例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL の実行（市況データ / 財務 / カレンダーの差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントスコア（ai_scores に書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか、OPENAI_API_KEY 環境変数を設定しておく
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込み銘柄数: {n_written}")
```

4) 市場レジーム判定（market_regime に書き込む）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は必要なテーブル・インデックスを作成します
```

6) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意:
- 全ての「target_date」は内部で datetime.today() を参照しない設計です（ルックアヘッドバイアスを防止）。
- AI を呼ぶ関数は OpenAI のレスポンスやネットワーク障害に対してフェイルセーフに設計されています（失敗時はスコアを 0 に置き換える、もしくは対象銘柄をスキップ）。

---

## 設定（settings）について

kabusys.config.settings からアプリ設定にアクセスできます。例:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

自動 .env 読み込み:
- 優先順位: OS 環境変数 > .env.local > .env
- プロジェクトルートは .git または pyproject.toml を基準に検出
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数が未設定の場合、Settings のプロパティが ValueError を投げます（使用箇所で明示的に require されるため早期に検出できます）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         -- 環境変数 / .env ロード / Settings
  - ai/
    - __init__.py
    - news_nlp.py                      -- ニュースセンチメント + OpenAI 呼出し & バリデーション
    - regime_detector.py               -- ETF MA200 とマクロニュースの合成によるレジーム判定
  - data/
    - __init__.py
    - pipeline.py                      -- ETL パイプライン（run_daily_etl 等）
    - jquants_client.py                -- J-Quants API クライアント（取得/保存/認証/リトライ/RateLimiter）
    - calendar_management.py           -- 市場カレンダー管理（営業日判定 / calendar_update_job）
    - news_collector.py                -- RSS 収集（SSRF対策、正規化、raw_news へ保存）
    - quality.py                       -- データ品質チェック
    - stats.py                         -- zscore_normalize 等ユーティリティ
    - audit.py                         -- 監査ログテーブル DDL / init_audit_db
    - etl.py                           -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py               -- momentum/value/volatility 計算
    - feature_exploration.py           -- forward returns / IC / rank / factor_summary
  - ai/ , research/ の各モジュールは研究・運用で利用するために分離

---

## 運用・注意点

- OpenAI API（gpt-4o-mini）を使用するため、APIキー管理・コスト・レート制限に注意してください。AI 呼び出しはバッチ（最大 20 銘柄等）で行われ、エラー時は部分的に処理継続するよう設計されています。
- J-Quants API のレート制限（120 req/min）に従うよう RateLimiter を実装済みです。get_id_token は自動リフレッシュを行います。
- DuckDB への書き込みは可能な限り冪等に設計されています（ON CONFLICT DO UPDATE / INSERT … ON CONFLICT）。
- news_collector は SSRF と XML インジェクション対策（defusedxml、ホストチェック）を実装していますが、実運用では追加の監査と監視を推奨します。
- ETL / AI の実行は CI/ジョブスケジューラ（Cron / Airflow 等）でスケジュールすることを想定しています。
- 本リポジトリは発注（ブローカー連携）機能を含み得ますが、本番口座での稼働前に十分なテストと安全策（冪等キー / 発注制限 / ログ監査）を導入してください。

---

## さらに詳しく / 貢献

- 各モジュールの docstring に詳細な設計と注意点が記載されています。実装の理解や拡張はまず src/kabusys 以下のファイルを参照してください。
- バグ修正や機能改善を行う場合は、ユニットテスト（モックを多用する作りになっています）を追加してください。AI / ネットワークリソースはテストでモック可能です。

---

この README はコードベースの主要機能と使い方を簡潔にまとめたものです。必要に応じてサンプルスクリプトや運用手順（ジョブスケジューリング、監視アラート設定など）を追加して下さい。