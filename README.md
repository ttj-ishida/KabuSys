KabuSys
======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買・リサーチ基盤です。  
J-Quants や RSS、OpenAI 等を利用して市場データ・ニュースを収集・品質チェック・加工し、監査ログやファクター計算、ニュースセンチメント評価、マーケットレジーム判定などの機能を提供します。パッケージは DuckDB をデータレイヤに用い、ETL・品質チェック・AI スコアリング・監査テーブルの初期化などを行えます。

主な機能
--------
- ETL（差分取得・保存）
  - 株価日足（J-Quants）
  - 財務データ（四半期）
  - JPX マーケットカレンダー
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理（URL除去・正規化・SSRF対策）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント評価、ai_scores 書込）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 統計ユーティリティ（Zスコア正規化・IC 計算等）
- 監査ログ（信号→発注→約定をトレースする監査テーブル群、冪等設計）
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ機能）

動作要件 / 依存
---------------
主な依存ライブラリ（インストール時に requirements を参照してください）:
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, logging 等）

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY         : OpenAI API キー（ニュース / レジーム判定用）
- KABU_API_PASSWORD      : kabuステーション API パスワード（発注系）
- SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       : Slack チャンネル ID

任意 / デフォルト
- KABUSYS_ENV : environment（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL   : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト: INFO
- DUCKDB_PATH : DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH : 監視用 SQLite パス。デフォルト: data/monitoring.db

注: パッケージ起動時に .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みします。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。.env.local は .env を上書きします。

セットアップ手順
----------------

1. リポジトリをクローン / 配布パッケージを取得

2. Python 環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存インストール（例）
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を作成し、必須の環境変数を記載します。
     例 (.env):
       JQUANTS_REFRESH_TOKEN=xxxxxxxx
       OPENAI_API_KEY=sk-...
       KABU_API_PASSWORD=...
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       KABUSYS_ENV=development
       LOG_LEVEL=INFO

   - 読み込みの順序: OS 環境変数 > .env.local > .env。override の取り扱いは .env/.env.local 読み込みロジックに従います。

5. DuckDB データベース準備（任意）
   - data ディレクトリを作成する場合: mkdir -p data

使い方（代表例）
----------------

以下は Python REPL / スクリプトから利用する例です。いずれも DuckDB の接続オブジェクト（duckdb.connect(...) の戻り値）を渡して実行します。

1) DuckDB に接続して ETL を実行する（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース NLP（当日対象記事のスコア算出）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # 日付は任意
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログスキーマ初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
# 以降、order_requests / executions 等のテーブルを使用可能
```

5) 研究用ファクター計算 / 正規化
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))

normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

ログ・環境モード
----------------
- KABUSYS_ENV により環境を切替 (development, paper_trading, live)。settings.is_live / is_paper / is_dev で判定可能。
- LOG_LEVEL でログ出力レベルを指定（DEBUG 等）。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 配下の主要モジュールと役割の概観です。

- kabusys/
  - __init__.py                (パッケージ定義, version=0.1.0)
  - config.py                  (環境変数・設定の管理、.env 自動読み込み)
  - ai/
    - __init__.py              (score_news エクスポート)
    - news_nlp.py              (ニュース NLP スコアリング — OpenAI 呼び出し, ETL への書込)
    - regime_detector.py       (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py        (J-Quants API クライアント、保存ロジック)
    - pipeline.py              (ETL パイプライン: run_daily_etl 等)
    - etl.py                   (ETLResult の公開)
    - news_collector.py        (RSS 収集・前処理・保存)
    - calendar_management.py   (市場カレンダー・営業日ユーティリティ)
    - quality.py               (データ品質チェック)
    - stats.py                 (Zスコア等統計ユーティリティ)
    - audit.py                 (監査ログテーブル定義と初期化)
  - research/
    - __init__.py              (研究用ユーティリティの公開)
    - factor_research.py       (ファクター計算: momentum/value/volatility)
    - feature_exploration.py   (forward return, IC, rank, summary)
  - ai/, data/, research/ 以下に更に補助関数や内部ユーティリティが実装されています。

設計上の注意点
--------------
- ルックアヘッドバイアス対策: 日付計算やデータ取得では datetime.today() / date.today() 参照箇所を限定し、明示的な target_date を使う設計です。
- 冪等性: DB 保存は ON CONFLICT を使った冪等設計。発注系は order_request_id を冪等キーとして扱う想定です。
- フェイルセーフ: AI API や外部 API の一時失敗はロギングしてフォールバック（0.0 など）で続行する実装が多くあります。
- セキュリティ: news_collector は SSRF 防止、defusedxml を使った XML パース、防御的なバイト数上限チェック等を備えています。

開発・テスト
------------
- settings.KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（テストで環境変数を制御したい場合に有効）。
- AI 呼び出し部分は内部で _call_openai_api をラップしており、テスト時にはモック差替えが可能です（unittest.mock.patch を想定）。

ライセンス / コントリビューション
---------------------------------
（ここにプロジェクトのライセンス情報や貢献ガイドラインを追記してください）

補足
----
- README に書かれている実行例はライブラリ API の一部を示したものです。実運用ではログ設定・エラーハンドリング・資格情報管理（Vault 等）を適切に行ってください。  
- 外部 API（J-Quants / OpenAI / kabuステーション 等）の利用には各サービスの利用規約・レート制限に従ってください。

質問や追加のドキュメント（例: API 詳細、ER 図、ETL スケジュール）を希望される場合は、必要なトピックを指定してください。