KabuSys
=======

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
DuckDB をデータレイクとして用い、J-Quants / RSS / OpenAI 等を組み合わせて以下を実現します:

- 市場データの差分ETL（株価、財務、JPXカレンダー）
- ニュース収集・NLP による銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF + LLM 混合スコア）
- ファクター計算 / 特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ定義・初期化

以下はコードベース（src/kabusys）に基づく README（日本語）です。

主な機能
--------
- ETL（kabusys.data.pipeline）
  - 日次差分 ETL（run_daily_etl）: 市場カレンダー→株価→財務→品質チェック
  - 個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
- J-Quants クライアント（kabusys.data.jquants_client）
  - API 取得、ページネーション、トークン自動リフレッシュ、保存処理（DuckDB へ冪等保存）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、raw_news への冪等保存（ID は正規化 URL の SHA256）
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとの記事を統合して OpenAI（gpt-4o-mini）の JSON mode でセンチメントを算出、ai_scores に書き込み
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離とマクロニュース LLM センチメントを重み合成して daily market_regime へ書き込み
- 研究用ユーティリティ（kabusys.research）
  - calc_momentum / calc_value / calc_volatility / forward returns / IC / 統計サマリ等
- データ品質チェック（kabusys.data.quality）
  - 欠損 / スパイク / 重複 / 日付不整合の検出
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ

必要条件 (概略)
----------------
- Python 3.9+（typing | match に依存する記法を用いているため、3.9 以上推奨）
- ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - その他: 標準ライブラリのみで動く箇所も多いですが、実行環境に合わせて適宜インストールしてください。

インストール
------------
仮想環境を作成してパッケージをインストールする例:

1. 仮想環境作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

3. ソースを開発モードでインストール（任意）
   - pip install -e .

設定（環境変数・.env）
---------------------
アプリケーション設定は環境変数またはプロジェクトルートの .env / .env.local から自動読み込みされます（kabusys.config）。自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（少なくとも実行する機能に応じて設定してください）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須：ETL / jquants_client）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携がある場合）
- KABU_API_BASE_URL: kabu API の base URL（任意、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知に使用する bot token（監視等で必要）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development / paper_trading / live)
- LOG_LEVEL: ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)

簡単な .env.example（プロジェクトルートに配置）:
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C0123456789
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

セットアップ例（DuckDB の初期化）
-------------------------------
監査ログ用テーブルを作成する例:

from kabusys.config import settings
from kabusys.data.audit import init_audit_db
conn = init_audit_db(settings.duckdb_path)
# conn は duckdb 接続オブジェクト

ETL 実行例
-----------
日次 ETL を実行する最低限のコード例:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

ポイント:
- run_daily_etl は market calendar → prices → financials → quality checks の順で実行します。
- J-Quants のトークンは settings.jquants_refresh_token（環境変数）で自動取得されます。

ニュース NLP / 市場レジーム算出の実行例
------------------------------------
OpenAI API キー（OPENAI_API_KEY）が必要です。

ニューススコア算出（ai スコアを ai_scores テーブルへ書き込む）:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → env を参照
print(f"wrote {n_written} scores")

市場レジーム判定:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)

研究用 API 例
-------------
ファクター計算や forward returns、IC 等は kabusys.research 以下の関数を利用します。例:

from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
fwd = calc_forward_returns(conn, target_date=date(2026,3,20), horizons=[1,5,21])
ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")

ログ・動作モード
----------------
- settings.env で development / paper_trading / live を選択できます（KABUSYS_ENV）。
- settings.log_level でログレベルを制御します（LOG_LEVEL）。
- 自動で .env / .env.local をロードします（OS 環境変数が優先、.env.local は .env 上書き）。テスト時に自動読み込みを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主なディレクトリ構成
-------------------
（src/kabusys 以下の主要ファイルと説明）

- kabusys/
  - __init__.py
  - config.py                    - 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                - ニュースの LLM センチメント算出と ai_scores 書き込み
    - regime_detector.py         - ETF MA と マクロ LLM を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          - J-Quants API クライアント / 保存ユーティリティ
    - pipeline.py                - 日次 ETL パイプラインと個別 ETL
    - etl.py                     - ETLResult のエクスポート
    - news_collector.py          - RSS 取得・正規化・保存
    - calendar_management.py     - JPX カレンダー管理 / 営業日判定 / calendar_update_job
    - quality.py                 - データ品質チェック群
    - stats.py                   - zscore 正規化 等の統計ユーティリティ
    - audit.py                   - 監査ログ（シグナル / 発注 / 約定）DDL と初期化
  - research/
    - __init__.py
    - factor_research.py         - Momentum / Volatility / Value の計算
    - feature_exploration.py     - forward returns, IC, rank, summary

注意事項 / 設計上のポイント
-------------------------
- ルックアヘッドバイアス対策: 多くの部分で datetime.today() に依存せず、target_date を明示して計算する設計です。バックテスト用途ではデータの取得日（fetched_at）や ETL 実行日を意識してください。
- 冪等性: J-Quants 保存関数や各種 INSERT は ON CONFLICT / 単一トランザクションでの削除→挿入等、冪等性を重視しています。
- フェイルセーフ: LLM / API 失敗時はゼロやスキップで続行するケースが多く、全体の ETL が停止しないよう配慮されています（ただし重要な欠損は品質チェックで検出されます）。
- セキュリティ: news_collector は SSRF 対策、defusedxml の使用、レスポンスサイズ上限などを実装しています。

開発・テスト
-------------
- 単体テストやモック：OpenAI 呼び出しやネットワーク呼び出しはモック可能な設計（内部の _call_openai_api や _urlopen を patch して差し替えられます）。
- 環境分離: DUCKDB_PATH や .env を切り替えることで開発・テスト用 DB を使い分けてください。

最後に
------
この README はコードベースの主要設計・使用方法をまとめたものです。実運用や詳細な API 仕様（J-Quants のパスやフィールド、kabu API の取り扱いなど）は該当する API ドキュメント・社内ドキュメントを参照してください。README に載っていない具体的な使い方（特定の関数サンプルやトラブルシューティング）が必要であれば教えてください。