KabuSys
=======

日本株向けのデータ基盤・リサーチ・自動売買を想定した Python ライブラリ群です。
J-Quants / kabuステーション / OpenAI（LLM）等と連携して以下を実現することを目的とします：

- データETL（株価・財務・マーケットカレンダー）
- ニュース収集と LLM によるニュースセンチメント解析
- 市場レジーム判定（MA と マクロニュースの融合）
- ファクター計算・特徴量探索（Research）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

主な機能
--------

- data:
  - ETL パイプライン（run_daily_etl）で株価 / 財務 / カレンダーの差分取得と保存
  - J-Quants API クライアント（ルート取得・ページネーション・リトライ・トークンリフレッシュ）
  - ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去、前処理、冪等保存）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days、夜間バッチ更新）
  - データ品質チェック（欠損・スパイク・重複・日付矛盾）
  - 監査ログ DB 初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（Zスコア正規化）

- ai:
  - ニュース NLP（gpt-4o-mini を想定した JSON Mode 呼び出し）で銘柄ごとのセンチメント取得（score_news）
  - マクロニュース + ETF MA200 乖離による市場レジーム判定（score_regime）

- research:
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- config:
  - .env（.env.local）または OS 環境変数から設定を自動読み込み
  - 必須設定キーは取得時に検査（未設定なら例外）

セットアップ（開発環境）
--------------------

前提
- Python 3.10+（型注釈の | 演算子・新しい型ヒントを使用）
- pip / virtualenv 等

手順（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに extras/requirements ファイルがない場合、上記を最低限の依存として記載しています。
    実運用では logging 設定・Slack 通知等の追加ライブラリが必要になる可能性があります。）

3. このパッケージを開発モードでインストール（任意）
   - pip install -e .

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack ボットトークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime で使用）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV           : development | paper_trading | live（デフォルト development）
- LOG_LEVEL             : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動読み込みを無効化

.env 自動読み込み
- パッケージは起点ファイルからプロジェクトルートを .git または pyproject.toml を探して特定します。
- 見つかった場合、ルートの .env → .env.local を順に読み込み（.env.local は既存値を上書き）。
- テスト時に自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（簡単な例）
-----------------

1) DuckDB 接続と ETL 実行（日次パイプライン）
- ETL を実行してデータを取得・保存・品質チェックまで行う例：

from datetime import date
import duckdb
from kabusys.data import pipeline

conn = duckdb.connect("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ETLResult に取得件数・保存件数・品質問題・エラーメッセージ等が含まれます。

2) ニュースセンチメントをスコア化（LLM）
- ai.news_nlp.score_news を使って指定日のニュースをスコア化（DuckDB 接続と OPENAI_API_KEY が必要）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
print(f"wrote scores for {n_written} codes")

- api_key を省略すると環境変数 OPENAI_API_KEY を参照します。

3) 市場レジーム判定
- ETF（1321）の MA200 乖離とマクロニュース LLM を合成して日次レジームを market_regime テーブルへ書き込みます：

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")

4) 監査ログ DB 初期化
- 監査スキーマ（signal_events / order_requests / executions）を含む DuckDB を初期化：

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可

5) リサーチ API（例：モメンタム計算）
- research.factor_research.calc_momentum などを呼び出してファクター値を取得できます：

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))

ディレクトリ構成（主要ファイル）
------------------------------

src/
  kabusys/
    __init__.py                # パッケージ初期化、__version__
    config.py                  # 環境変数/.env 管理（自動読み込み）
    ai/
      __init__.py
      news_nlp.py              # ニュースの LLM スコアリング（score_news）
      regime_detector.py       # 市場レジーム判定（score_regime）
    data/
      __init__.py
      jquants_client.py        # J-Quants API クライアント（取得＋DuckDB保存）
      pipeline.py              # ETL パイプライン（run_daily_etl 等）
      etl.py                   # ETL インターフェース（ETLResult 再エクスポート）
      news_collector.py        # RSS 取得・前処理・raw_news 保存
      calendar_management.py   # マーケットカレンダー管理（営業日判定等）
      quality.py               # データ品質チェック
      stats.py                 # 共通統計ユーティリティ（zscore_normalize 等）
      audit.py                 # 監査ログ（テーブル定義・初期化）
    research/
      __init__.py
      factor_research.py       # モメンタム/バリュー/ボラティリティ等
      feature_exploration.py   # 将来リターン・IC・統計サマリー
    research/                  # (上記)
    (その他モジュールが追加される想定)

設計上の注意点 / ポイント
------------------------
- Look-ahead bias（将来情報の参照）回避に配慮：
  - 各モジュールは内部で date.today() を直接参照しない設計（呼び出し側で target_date を渡す）。
  - データ取得・スコア算出は target_date に対する過去・指定ウィンドウのみ参照。

- 冪等性・トランザクション：
  - J-Quants 保存関数は ON CONFLICT DO UPDATE を使用して冪等性を確保。
  - 監査ログ初期化や AI スコア書込など一部操作は BEGIN / DELETE / INSERT / COMMIT を使った冪等処理。

- フェイルセーフ：
  - LLM/API の一時失敗や予期せぬレスポンスではスコアを 0 にフォールバックしたり、処理をスキップして継続する設計。

- セキュリティ：
  - news_collector は SSRF 対策（リダイレクト検査・内部IP検出）、XML パースは defusedxml を利用。

追加情報 / 開発
----------------
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効化できます。
- OpenAI 呼び出し部分はテスト容易性のため _call_openai_api をモック可能に実装してあります。
- 実運用での発注（kabu API）、Slack 通知などは別モジュールでラップして接続する想定です。

ライセンス / 貢献
-----------------
（このリポジトリにライセンス表記が無い場合はプロジェクト方針に従って追加してください）
貢献やバグ報告は Pull Request / Issue にてお願いします。

---

この README はコードベース（src/kabusys 以下）を元にした概要です。導入・運用にあたっては .env.example（存在する場合）やプロジェクト内ドキュメント（DataPlatform.md / StrategyModel.md など）を参照してください。必要があればサンプル .env テンプレートや実行例の詳細を追記します。