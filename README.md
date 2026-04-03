KabuSys
=======

日本株向けのデータ基盤・リサーチ・AI支援・監査ログを備えた自動売買/研究ライブラリです。  
DuckDB をデータストアに利用し、J-Quants / OpenAI / RSS 等と連携して ETL、ファクター計算、ニュース NLP、レジーム判定、監査ログ初期化などを提供します。

主な特徴
-------
- データETL：J-Quants API から株価（日次）・財務・市場カレンダーを差分取得し DuckDB に冪等保存
- 品質チェック：欠損、重複、スパイク、日付整合性チェックを実装
- ニュース収集：RSS 取得・前処理・冪等保存（SSRF対策、トラッキング除去）
- ニュース NLP：OpenAI（gpt-4o-mini）を用いた銘柄別センチメント集約処理（バッチ・リトライ対応）
- レジーム判定：ETF（1321）の MA 乖離 + マクロニュースセンチメントから日次で市場レジームを判定
- リサーチ：モメンタム / ボラティリティ / バリュー 等のファクター計算と特徴量解析ユーティリティ
- 監査ログ：シグナル→発注→約定のトレーサビリティ用テーブル／初期化機能（DuckDB）
- 設定管理：.env（.env.local）と環境変数を自動読み込み（プロジェクトルートベース）、保護機能あり

要件
----
- Python >= 3.10（| 型注釈を使用）
- 推奨パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

セットアップ手順
----------------

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）:
   - git clone ...
   - python -m pip install -e .

2. 必要パッケージをインストール:
   - pip install duckdb openai defusedxml

3. 環境変数の設定:
   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。読み込み順は OS 環境 > .env.local > .env です。

   最低限設定が必要な変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token          （必須：J-Quants 認証）
   - KABU_API_PASSWORD=your_kabu_station_password             （必須：kabuステーション API）
   - OPENAI_API_KEY=sk-...                                    （OpenAI を使う場合）
   - DUCKDB_PATH=data/kabusys.duckdb                           （任意：DuckDB ファイルパス）
   - SQLITE_PATH=data/monitoring.db                            （任意）
   - KABUSYS_ENV=development|paper_trading|live               （任意、デフォルト: development）
   - LOG_LEVEL=INFO|DEBUG|...                                  （任意）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABU_API_PASSWORD=secret
   LOG_LEVEL=INFO
   ```

使い方（主要 API の例）
---------------------

準備：DuckDB 接続を作成し settings を利用する例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

ETL（日次パイプライン）を実行する
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=None)
print(res.to_dict())
```

株価・財務・カレンダー個別 ETL（差分単位で呼べる）
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from datetime import date

target = date(2026, 3, 20)
fetched, saved = run_prices_etl(conn, target)
```

ニューススコアリング（OpenAI が必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {n_written}")
# api_key を引数で渡すことも可能： score_news(conn, date, api_key="sk-...")
```

市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
# こちらも api_key 引数で OpenAI キーを渡せます
```

監査ログスキーマ初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# テーブルとインデックスが作成されます
```

ディレクトリ構成（主要ファイル）
-----------------------------

- src/kabusys/
  - __init__.py
  - config.py                          : 環境変数 / .env 自動読み込み・設定ラッパー
  - ai/
    - __init__.py
    - news_nlp.py                       : ニュースのバッチ NLP スコアリング（OpenAI）
    - regime_detector.py                : ETF MA + マクロニュースで日次レジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 : J-Quants API クライアント（取得/保存/リトライ/レート制御）
    - pipeline.py                       : ETL パイプライン（run_daily_etl 等）
    - etl.py                            : ETLResult の再エクスポート
    - calendar_management.py            : 市場カレンダー管理・営業日判定
    - news_collector.py                 : RSS 収集・前処理・SSRF 対策
    - quality.py                        : データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py                          : zscore 正規化等ユーティリティ
    - audit.py                          : 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py                : Momentum / Volatility / Value のファクター計算
    - feature_exploration.py            : 将来リターン、IC、統計サマリー等
  - monitoring/ (未列挙の可能性あり)
  - strategy/ (未列挙の可能性あり)
  - execution/ (未列挙の可能性あり)

設計上の注意点 / 備考
---------------------
- Look-ahead バイアス対策：多くの処理で date を外部引数に取り、datetime.today()/date.today() を直接参照しないように設計されています。バックテスト時は明示的に target_date を与えることを推奨します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を上位に持つディレクトリ）を起点に行われます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はリトライや JSON パースの堅牢化が入っていますが、API 料金やレートに注意してください。関数は api_key を引数で受け取れるため、環境変数に依存せずキーを注入できます。
- J-Quants クライアントは内部でレート制御（120 req/min）・401 リフレッシュ・リトライを実装しています。JQUANTS_REFRESH_TOKEN の管理は慎重に行ってください。
- DuckDB に対する executemany の空リスト渡しなど DuckDB バージョン依存の注意点が実装上にあります（コード内コメント参照）。

開発 / テスト
--------------
- モジュール内で API 呼び出し等をモックしやすい設計になっています（例：news_nlp._call_openai_api や regime_detector の内部呼び出しを patch 可能）。
- 単体テストを行う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットし、必要な環境変数をテスト側で注入することを推奨します。

ライセンス / 貢献
-----------------
（このテンプレートではライセンス情報は含まれていません。実際のプロジェクトでは LICENSE を追加してください。）

問い合わせ
----------
問題報告や提案があれば Issue を開いてください。README で足りない使い方やサンプルがあれば追加します。

以上。必要であれば README に実行例（より詳細なスクリプトや crontab 例、Dockerfile サンプル等）を追記します。