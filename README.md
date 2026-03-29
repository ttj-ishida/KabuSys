KabuSys — 日本株自動売買基盤 README（日本語）
=====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／自動売買基盤のコアライブラリ群です。  
主に以下を提供します。

- J-Quants からのデータ取得（株価日足、財務、取引カレンダー）と DuckDB への ETL パイプライン
- ニュース収集・NLP による銘柄センチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- データ品質チェック、マーケットカレンダー管理
- 監査ログ（signal → order_request → execution のトレーサビリティ）初期化ユーティリティ

設計上の特徴：
- Look-ahead バイアス回避や冪等性（ON CONFLICT）を意識した実装
- 外部 API 呼び出し（J-Quants / OpenAI）に対するリトライ・レート制御・フェイルセーフ
- DuckDB を中心としたローカルデータプラットフォーム

主な機能一覧
----------------
- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save 各種）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days）
  - ニュース収集（RSS パーサ、SSRF/サイズ制限対策）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索／IC 等（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数管理（自動 .env ロード、必須 env チェック）

セットアップ手順
----------------

前提
- Python 3.9+ (typing の一部注釈に合わせることを推奨)
- システムにネットワーク接続（J-Quants / OpenAI / RSS 取得用）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (UNIX) または .venv\Scripts\activate (Windows)

2. 依存ライブラリをインストール
   以下は代表的な依存パッケージ（プロジェクトに requirements.txt があればそれを利用してください）。
   - duckdb
   - openai
   - defusedxml

   例:
   - pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   必須の環境変数（少なくとも以下を設定してください）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能利用時）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知を使う場合）
   - SLACK_CHANNEL_ID — Slack チャンネル ID

   任意 / デフォルトあり:
   - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
   - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — SQLite（監視等）パス（デフォルト: data/monitoring.db）
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）

   自動 .env 読み込み:
   - パッケージはプロジェクトルート（.git または pyproject.toml）から .env を自動的に読み込みます（OS 環境変数 > .env.local > .env の順）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. データベース／スキーマの初期化
   - 監査ログ用 DB を作成する例:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 必要に応じてアプリケーション側でスキーマ初期化処理を呼び出してください（init_audit_schema を利用）。

使い方（簡易例）
----------------

1) 日次 ETL 実行（J-Quants からデータ取得・保存・品質チェック）
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl は ETLResult を返します。品質チェックの結果やエラー情報を確認してください。

2) ニュース NLP による銘柄スコアリング（OpenAI を用いる）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print("written", n_written)
```
- 対象の raw_news / news_symbols テーブルのデータ範囲は calc_news_window に準拠します（前日15:00 JST〜当日08:30 JST）。

3) 市場レジーム判定
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```
- ETF 1321 の 200 日 MA 乖離と OpenAI によるマクロセンチメントを合成して market_regime テーブルに書き込みます。

4) ファクター計算（研究用途）
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026,3,20))
v = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

主要な API / 返り値の説明
- run_daily_etl(...) → ETLResult（target_date, fetched/saved counts, quality_issues, errors）
- score_news(conn, target_date, api_key) → 書き込んだ銘柄数（int）
- score_regime(conn, target_date, api_key) → 1（成功時）
- init_audit_db(path) → duckdb connection（監査ログ用 DB を初期化）

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                     — 環境設定 / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL 公開型（ETLResult 再エクスポート）
    - news_collector.py            — RSS ニュース収集
    - calendar_management.py       — マーケットカレンダー管理
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログ（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算
    - feature_exploration.py       — 将来リターン・IC・統計サマリー
  - research/（他ファイル）
  - ...（その他戦略 / 実行 / モニタリングモジュールは __all__ に準備）

運用上の注意点 / ヒント
-----------------------
- 環境変数管理:
  - OS 環境変数が優先されます。プロジェクトルートの .env/.env.local を自動読み込みしますが、テスト時など自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使えます。
- OpenAI 呼び出し:
  - API エラー時はフェイルセーフでスコアを 0.0 に戻す等の設計になっていますが、API キーは必須です（score_news/score_regime）。
- J-Quants:
  - get_id_token はリフレッシュトークンから id token を取得します。JQUANTS_REFRESH_TOKEN を設定してください。
  - API レート制限（120 req/min）に対するスロットリング実装がありますが、ETL 実行時は負荷に注意してください。
- DuckDB:
  - デフォルト DB パスは data/kabusys.duckdb。必要なら DUCKDB_PATH を上書きしてください。
- RSS / ニュース:
  - fetch_rss は SSRF / gzip bomb / 大容量レスポンス対策を備えています。RSS ソースは DEFAULT_RSS_SOURCES を変更するか関数を呼んで下さい。

貢献 / 開発
-----------
- コーディング規約やテスト方針はリポジトリ内の CONTRIBUTING や pyproject.toml（存在する場合）を参照してください。
- モジュール内のプライベート関数はテスト時に patch して差し替え可能な設計になっています（例: OpenAI の呼び出し _call_openai_api をモック）。

免責
----
本リポジトリは自動売買のための基盤的なユーティリティを提供しますが、実際の取引では自己責任でリスク管理を行ってください。live 環境での実行前に十分なテストを行ってください。

問い合わせ
-----------
問題や改善提案はリポジトリの issue を立てるか、プロジェクトの連絡先に問い合わせてください。

以上。README に記載して欲しい追加情報（ライセンス、実行例の拡張、requirements.txt の正確な内容など）があれば教えてください。