KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けのデータプラットフォームと研究／自動売買基盤のライブラリ群です。  
主に以下を目的とします。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- ニュース収集と LLM（OpenAI）によるニュース／マクロセンチメント評価
- ファクター計算・特徴量探索（リサーチ用）
- ETL パイプラインとデータ品質チェック
- 監査ログ（signal → order → execution のトレーサビリティ）
- Paper trading / Live 環境切替に対応した設定管理

主要機能
--------
- 環境設定管理（.env / 環境変数の自動ロード、保護付き上書き）
- J-Quants API クライアント（取得・ページネーション・トークン自動リフレッシュ・レート制御）
- ETL パイプライン（差分取得、保存、品質チェック、日次実行エントリ）
- ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去、前処理）
- ニュース NLP（OpenAI を使った銘柄別センチメント、JSON Mode + バッチ処理）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースを合成）
- 研究用モジュール（モメンタム、ボラティリティ、バリューのファクター計算、IC・統計）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ初期化・専用 DB 初期化ユーティリティ

セットアップ手順
----------------

前提
- Python 3.10+（typing | 型注釈に union 型演算子を使用）
- DuckDB（Python パッケージ）
- OpenAI SDK（openai）
- defusedxml（RSS パースの安全対策）

推奨手順（開発環境）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクト配布時は requirements.txt / pyproject.toml を用意して pip install -r requirements.txt または pip install -e . を使用してください）

3. 環境変数を設定
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

任意／運用
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に引数で渡すことも可）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- DUCKDB_PATH: データ DB のパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_FILL_MODE: instant | partial | never | reject
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）

例: .env
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

基本的な使い方（スニペット）
-------------------------

1) DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントをスコアして ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で渡すか、OPENAI_API_KEY 環境変数を設定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込件数: {n_written}")
```

3) 市場レジーム（bull / neutral / bear）を判定して market_regime に書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB を初期化する（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

設定に関する注意点
- settings は kabusys.config.settings から参照できます（プロパティ経由で値を取得）
- .env ファイルのパースは堅牢化されています（クォートやコメント、export 形式に対応）
- 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）に対して行われます
- テスト時などで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要 API 要点
- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 関数で DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - レート制御とリトライを内蔵

- ニュース NLP（kabusys.ai.news_nlp）
  - calc_news_window(target_date) でニュースウィンドウを計算
  - score_news(conn, target_date, api_key=None) で ai_scores へ書き込み

- レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None) で market_regime に書込

- リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize は kabusys.data.stats で提供

- データ品質（kabusys.data.quality）
  - run_all_checks(conn, target_date=..., reference_date=..., spike_threshold=...) がすべてのチェックを実行

ディレクトリ構成（主なファイル）
--------------------------------
以下はパッケージ内部の主要ファイル・モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py             : パッケージ初期化（公開モジュール定義）
  - config.py               : 環境変数と設定を読み込む Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py           : ニュースセンチメント（銘柄別）処理、OpenAI 呼び出し、バッチ処理
    - regime_detector.py    : マクロ + MA200 乖離で市場レジームを判定
  - data/
    - __init__.py
    - jquants_client.py     : J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py          : ETL パイプライン（run_daily_etl 等）
    - etl.py               : ETLResult の再エクスポート
    - stats.py             : zscore_normalize 等の統計ユーティリティ
    - quality.py           : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - news_collector.py    : RSS 取得・前処理・保存ロジック（SSRF 対策あり）
    - calendar_management.py: 市場カレンダー管理（is_trading_day 等）
    - audit.py             : 監査ログスキーマ定義／初期化
  - research/
    - __init__.py
    - factor_research.py   : Momentum / Volatility / Value のファクター計算
    - feature_exploration.py: 将来リターン計算、IC、統計サマリー、rank 関数
  - ai/regime_detector.py  : マクロセンチメントと MA を合成してレジーム判定

開発・運用上の注意
-----------------
- ルックアヘッドバイアス対策: ほとんどの処理で datetime.today() / date.today() を直接参照せず、target_date を明示的に渡す設計になっています。バックテスト等では過去の target_date を指定して使用してください。
- OpenAI 呼び出しは JSON Mode を使用し、レスポンスの厳格検証を行っています。API エラー時はフェイルセーフ（0.0 スコア）にフォールバックする設計です。
- DuckDB への大量書き込みは executemany / トランザクションでまとめているため、部分失敗時は ROLLBACK を試みます。
- news_collector は SSRF 対策（リダイレクト検査、プライベートホスト判定）と XML パースの安全化（defusedxml）を行っています。

FAQ / トラブルシューティング
----------------------------
Q: .env が読み込まれない／テストで読み込みを抑えたい  
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

Q: OpenAI のキーが無いと score_news 等は動きますか？  
A: OpenAI API キーが未設定で score_news/score_regime を実行すると ValueError になります。api_key 引数か OPENAI_API_KEY を設定してください。API 呼び出し失敗時は処理の一部だけをスキップする（全体が落ちない）設計です。

Q: J-Quants のトークンが期限切れになったら？  
A: jquants_client.get_id_token はリフレッシュトークンを用いて ID トークンを取得します。_request は 401 を検知してトークンを自動リフレッシュして1回リトライします。

最後に
------
この README はソースコード（config / data / ai / research モジュール群）を元にまとめた概要です。実際の運用スクリプト（起動エントリ、サービス化、監視設定など）はプロジェクト側で別途用意してください。質問や追加のドキュメント化したい箇所があれば教えてください。