KabuSys
=======

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI支援・監査ログを備えた自動売買支援ライブラリです。
主に以下を目的とします。

- J-Quants API からのデータ取得（株価日足・財務・カレンダー）
- DuckDB ベースの ETL パイプラインとデータ品質チェック
- ニュースの収集・NLP（LLM）によるセンチメントスコアリング
- マーケットレジーム判定（テクニカル × マクロニュース）
- ファクター計算・特徴量探索（研究用途）
- 発注〜約定に至る監査ログスキーマ（トレーサビリティ）

本リポジトリはモジュール群として設計され、ライブラリをインポートしてプログラム内から利用することを想定しています。

主な機能
--------
- data
  - jquants_client: J-Quants API からの差分取得（ページネーション、リトライ、レートリミット）と DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
  - pipeline / etl: 日次 ETL パイプライン（calendar → prices → financials）と ETL レポート（ETLResult）
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - news_collector: RSS 収集、URL 正規化、SSRF 対策、raw_news への挿入
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査テーブル定義・初期化（signal_events, order_requests, executions）
  - stats: 汎用統計（Zスコア正規化 等）
- ai
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini）で銘柄別にスコア化して ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF（1321）200日移動平均乖離とマクロニュース（LLM）を合成して市場レジーム（bull/neutral/bear）を判定・書き込み
- research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を利用）
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ等

セットアップ
-----------
前提
- Python 3.10 以上（型注記で | None 等を使用しているため）
- システムに合わせた適切な権限

基本手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要ライブラリをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使ってインストールしてください:
   pip install -r requirements.txt または pip install -e .）

3. 環境変数の設定
   本プロジェクトは環境変数／.env ファイルから設定を読み込みます（優先順位: OS 環境変数 > .env.local > .env）。
   自動ロードは、パッケージの配置先で .git または pyproject.toml が見つかった場合に行われます。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須の環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN   — J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
   - SLACK_BOT_TOKEN         — （Slack通知を使う場合）Slack Bot トークン
   - SLACK_CHANNEL_ID        — Slack 送信先チャンネル ID
   - KABU_API_PASSWORD       — kabuステーション API を使う場合のパスワード
   - OPENAI_API_KEY          — AI モジュール（news_nlp / regime_detector）で使用（関数引数からも渡せます）

   任意 / デフォルト設定（環境変数がなければ以下が使われます）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
   - KABUS_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視設定

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

使い方（コード例）
-----------------

基本的な DuckDB 接続を用いた ETL 実行
- ETL を日次で実行して DB を更新する例:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

ニューススコアリング（LLM）を呼ぶ例
- news_nlp.score_news は OpenAI API キーを引数または環境変数で受け取ります。

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} symbols")

市場レジームのスコア計算
- regime_detector.score_regime を使って market_regime テーブルへ書き込む:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

監査ログスキーマの初期化
- audit.init_audit_db / init_audit_schema を使用して監査用 DB を作成・初期化できます。

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")

research（ファクター計算）の呼び出し例
- calc_momentum / calc_volatility / calc_value は prices_daily / raw_financials を前提とします。

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
print(len(records))

設定読み込みの振る舞い
- src/kabusys/config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- settings オブジェクト経由で設定値を取得できます（例: from kabusys.config import settings; settings.duckdb_path）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLP（LLM）によるスコアリング
  - regime_detector.py           — マーケットレジーム判定
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント・保存ロジック
  - pipeline.py                  — ETL パイプライン（run_daily_etl など）
  - etl.py                       — ETL インターフェース（ETLResult 再エクスポート）
  - news_collector.py            — RSS 収集・前処理・raw_news 保存
  - calendar_management.py       — JPX カレンダー管理（営業日判定 等）
  - quality.py                   — データ品質チェック
  - stats.py                     — 統計ユーティリティ（zscore_normalize）
  - audit.py                     — 監査ログテーブル定義・初期化
- research/
  - __init__.py
  - factor_research.py           — ファクター計算（momentum/volatility/value）
  - feature_exploration.py       — 将来リターン・IC・統計サマリ等

注意事項 / 設計方針の要点
-----------------------
- Look-ahead bias 回避: バックテストや因果解析のため、関数は date や conn を明示的に受け取り、datetime.today()/date.today() を内部で参照しない設計が重視されています（ターゲット日を明示する必要があります）。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE / INSERT ... DO NOTHING 等で再実行に耐えるように設計されています。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時は局所的にフォールバック（0.0 スコア等）し、処理全体が停止しない設計です。ログに詳細を残します。
- セキュリティ: news_collector は SSRF 対策（リダイレクト検査・プライベートアドレス検査）、defusedxml による XML パース等の対策を実装しています。

貢献・拡張
----------
- 新しいデータソース・フィード、監視アラート（Slack 通知）、戦略実装（strategy モジュール）などをモジュール単位で追加できます。
- テスト: 各外部 API 呼び出しポイントは差し替え・モックしやすいように作られています（例: _call_openai_api をパッチ）。

ライセンス・連絡
----------------
- 本 README にはライセンス情報を含めていません。実際のプロジェクトに合わせた LICENSE を追加してください。
- 実装や使い方に関する質問があれば、リポジトリの issue を立てるか、プロジェクト管理者にお問い合わせください。

以上。必要に応じて README に追記（インストール手順の具体化、CI／テスト方法、例データの用意手順、SQL スキーマ定義の明示等）します。どの項目を深掘りしますか？