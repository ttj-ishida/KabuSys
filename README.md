# KabuSys

KabuSys は日本株のデータ収集・品質チェック・リサーチ・AI ニューススコアリング・市場レジーム判定・監査ログ管理までを含む日本株自動売買プラットフォーム用のライブラリ群です。DuckDB を用いたローカルデータベースを中心に、J-Quants API や OpenAI（LLM）を利用した機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

- データ層（data）: J-Quants API からの株価・財務・カレンダー取得、RSS ニュース収集、ETL パイプライン、品質チェック、監査ログ（注文／約定）用スキーマなど。
- 研究層（research）: ファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターン・IC 計算、統計ユーティリティ。
- AI 層（ai）: ニュースのセンチメントスコアリング（OpenAI）と市場レジーム判定のロジック。
- 設定（config）: .env / 環境変数読み込み、必要設定の取得、ローカル自動ロードの仕組み。
- 監視・実行（execution / monitoring 等）に関するインターフェース（パッケージ外部から利用可能）。

設計方針の重要点:
- ルックアヘッドバイアスを避ける実装（target_date を明示し、datetime.today() を内部参照しない等）
- API 呼び出しに対する堅牢なリトライ・バックオフとフェイルセーフ（LLM や J-Quants）
- DuckDB に対して冪等にデータを保存（ON CONFLICT / DELETE→INSERT 等）
- テストしやすさのために外部呼び出し（OpenAI や HTTP）の差し替えポイントを用意

---

## 機能一覧（主な提供 API / モジュール）

- kabusys.config
  - .env/.env.local の自動ロード（プロジェクトルート検出）
  - Settings クラス（必要な環境変数の取得）

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存用関数）
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - get_id_token (リフレッシュトークン→IDトークン)
  - pipeline: ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースを LLM に投げて銘柄別スコアを ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF(1321) の MA とマクロニュースの LLM スコアを合成して market_regime に保存

- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize を活用した因子処理

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上（コード中で X | None 形式の型を使用）
- Git リポジトリルートに pyproject.toml または .git があること（config の自動 .env ロード用）

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone ... && cd your-repo

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - 他に必要なパッケージがあれば pyproject.toml / requirements.txt を参照して追加してください

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると、自動的に読み込まれます（優先順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須の環境変数（最低限、以下は必須としてコード内で参照されています）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token のため）
- KABU_API_PASSWORD: kabuステーション API パスワード（API 利用がある場合）
- SLACK_BOT_TOKEN: Slack 通知などを使う場合
- SLACK_CHANNEL_ID: Slack チャンネル ID

その他（オプション・デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live), LOG_LEVEL
- OPENAI_API_KEY: LLM を使う場合（news_nlp / regime_detector）

例: .env の最小例
- JQUANTS_REFRESH_TOKEN=xxxx
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C12345678

---

## 使い方（代表的な利用例）

以下は Python スクリプト / REPL からの呼び出し例です。DuckDB の接続は duckdb.connect("data/kabusys.duckdb") などで作成します。

1) ETL（日次ETL の実行）
- ETL が内部で J-Quants を呼んでデータを取得し、品質チェックまで行います。

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのスコアリング（LLM による銘柄別 ai_score 保存）
- OpenAI API キーは environment variable OPENAI_API_KEY または api_key 引数で渡せます。

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print(f"written {written} codes")
```

3) 市場レジームの判定（ETF 1321 の MA とマクロニュース合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

5) J-Quants からのデータ取得（直接利用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# get_id_token() は settings.jquants_refresh_token を参照
quotes = fetch_daily_quotes(date_from=..., date_to=...)
```

注意点:
- LLM コール（OpenAI）は外部 API なので、テスト時は内部の _call_openai_api を unittest.mock で差し替えてください（news_nlp/regime_detector の説明参照）。
- run_daily_etl 等はトランザクションやエラーハンドリングを持ちますが、ETL の継続/停止判断は戻り値の ETLResult を参照してください。

---

## テストに関するメモ

- 自動 env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットします（テストで環境を独立させる場合に便利）。
- OpenAI 呼び出しをモックするフック:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
- ネットワーク依存箇所（RSS フェッチ、J-Quants）も urllib のラッパーをモックして差し替え可能です（news_collector._urlopen、jquants_client._request など）。

---

## ディレクトリ構成（抜粋）

（プロジェクトの src/kabusys 以下を抜粋したツリー）

- src/kabusys/
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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (export wrapper)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - (その他: strategy, execution, monitoring パッケージが top-level __all__ に含まれていますが、ここに示されているファイル群が主な実装です)

各ファイルの役割は上記「機能一覧」を参照してください。

---

## 運用上の注意

- 環境（KABUSYS_ENV）が `live` の場合は実際の発注や通知処理に注意してください。`paper_trading` / `development` を用意し、安全な環境で充分に検証してから稼働してください。
- J-Quants のレート制限や OpenAI のコストに留意してください（モジュール内でレートリミッタ・リトライ実装あり）。
- DuckDB ファイルのバックアップ・スキーマ管理を運用ルールとして確立してください。
- 監査ログは削除しない方針で設計されています。データ取り扱いに応じてローテーション方針を用意してください。

---

README に書かれている以外の使い方や追加のセットアップ（CI/CD、Docker、Scheduler の導入など）が必要であれば、利用シナリオに合わせた手順やサンプルを作成します。必要な内容を教えてください。