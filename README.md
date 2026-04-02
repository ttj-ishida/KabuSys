KabuSys
=======

KabuSys は日本株のデータプラットフォームと自動売買に必要な共通コンポーネント群を提供する Python パッケージです。ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注・約定トレーサビリティ）などの機能を含みます。

バージョン: 0.1.0

主な目的
- J-Quants API や RSS からのデータ収集と DuckDB への保存（冪等処理）
- ニュースの NLP スコアリング（OpenAI を利用）
- 市場レジーム判定（ETF＋マクロニュースを統合）
- ファクター計算・研究ユーティリティ（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal → order_request → executions のトレーサビリティ）

機能一覧
- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、トークン管理、レートリミット、リトライ）
  - ニュース収集（RSS の安全な取得、SSRF 対策、前処理、raw_news への保存）
  - カレンダー管理（market_calendar を用いた営業日判定、next/prev_trading_day 等）
  - 品質チェック（missing_data, spike, duplicates, date_consistency, run_all_checks）
  - 監査ログスキーマ作成 / 初期化（init_audit_schema, init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを銘柄単位に集約して OpenAI に投げ、ai_scores に格納
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースの LLM スコアを合成して market_regime に書き込み
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config:
  - Settings クラスで環境変数を集約（自動 .env ロード機能あり）

セットアップ手順（開発環境）
1. 前提
   - Python 3.10 以上（型アノテーションに | 演算子を使用）
   - DuckDB、OpenAI SDK、defusedxml などのパッケージをインストール

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそちらを利用してください）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード（使用する場合）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - OPENAI_API_KEY — OpenAI API キー（ai モジュールを使う場合）
   - オプション・デフォルト値:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL — デフォルト INFO
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

   例 .env（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```

使い方（概要とサンプルコード）
- 基本的に DuckDB 接続を渡して関数を呼びます。

1) ETL を走らせる（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックの順で処理します。ETLResult オブジェクトを返します。

2) ニューススコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None の場合は OPENAI_API_KEY を参照
print("scored:", count)
```

3) 市場レジーム判定（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# または :memory: でインメモリ
```

5) 設定値の参照
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

注意点・設計上のポイント
- 多くの処理は「ルックアヘッドバイアス」を防ぐため、date.today() / datetime.today() を内部で直接参照しない設計です。target_date を明示的に渡して利用してください。
- .env の自動ロード:
  - パッケージ起点で .git または pyproject.toml を探索してプロジェクトルートを決定し、.env → .env.local の順で読み込みます。
  - OS 環境変数が優先され、.env.local は上書き可能です。テスト等で自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- J-Quants API クライアントにはレートリミット制御、トークン自動リフレッシュ、リトライ（指数バックオフ）等が組み込まれています。
- OpenAI 呼び出しは JSON mode を用いる（厳密な JSON 出力を期待）ため、レスポンスのパースやリトライ処理を行っています。API 失敗時はフェイルセーフとして 0.0 を返す等の措置がある関数もあります（例: _score_macro）。
- DuckDB の executemany はバージョン差異に注意（空リストの扱いなど）。コード内でチェック済みです。

ディレクトリ構成（主なファイル）
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
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - audit（関数群）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージのエクスポート: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank

ロギングとモード
- 環境変数 LOG_LEVEL でログレベルを指定できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- KABUSYS_ENV によって動作モードを切替可能（development, paper_trading, live）。settings.is_live / is_paper / is_dev を参照して処理分岐できます。

依存関係（主要）
- duckdb
- openai
- defusedxml
- （標準ライブラリ: urllib, json, datetime, logging, math など）

貢献・開発
- コードを変更する際はユニットテストを追加してください（特に外部 API 呼び出し部分はモック可能な設計になっています）。
- 環境変数自動ロードは開発時に便利ですが、CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を活用してください。

補足
- README はコードベース全体の要点をまとめたものです。詳細な API ドキュメント（各関数の引数・戻り値・ログ出力・例外）については各モジュールの docstring を参照してください。

以上。必要であれば、README に例コマンド（docker-compose、systemd サービス化、cron での ETL スケジュール化）や、より詳細な .env.example（全環境変数一覧）を追加できます。どの情報を追加したいか教えてください。