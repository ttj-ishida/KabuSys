KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株のデータ取得・ETL・特徴量計算・ニュースNLP・市場レジーム判定・監査ログ等を備えた自動売買/リサーチ基盤のライブラリ群です。  
主に DuckDB を用いたローカルデータプラットフォームと、J-Quants / OpenAI 等の外部 API との連携により、データ収集 → 品質チェック → ファクター算出 → AI スコアリング → 監査トレーサビリティまでをカバーします。

主な特徴
--------
- データ ETL（J-Quants API 経由）
  - 株価日足 / 財務データ / 市場カレンダーの差分取得と冪等保存
  - レートリミット・再試行・トークン自動リフレッシュ対応
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集・NLP（OpenAI）
  - RSS 収集（SSRF 対策・トラッキング除去）と raw_news 保存
  - gpt-4o-mini を用いた銘柄単位のニュースセンチメントスコア生成（ai_scores への保存）
- 市場レジーム判定
  - ETF（1321）200 日移動平均乖離とマクロニュースセンチメント合成による日次レジーム判定
- 研究・ファクター群
  - モメンタム / ボラティリティ / バリュー 等のファクター計算、Z スコア正規化、将来リターン・IC 計算
- 監査ログ（audit）
  - signal → order_request → executions までのトレーサビリティを担保する監査スキーマ、初期化ユーティリティ
- 環境変数管理
  - .env / .env.local / OS 環境変数から自動読み込み（プロジェクトルート検出）を行う

セットアップ
-----------
前提
- Python 3.10 以上（型ヒントに | 演算子を利用）
- DuckDB（Python パッケージ）、OpenAI（公式 SDK）、defusedxml 等の依存

例: 仮想環境作成とインストール
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を用意して依存管理してください）

3. パッケージを開発モードでインストール（リポジトリルートで）
   - pip install -e .

環境変数 / .env
- 自動読み込みの優先順位: OS 環境変数 > .env.local > .env  
  （プロジェクトルートは .git または pyproject.toml を基準に自動検出）
- 自動読み込みを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須で ETL を実行する場合）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・プロセス管理
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

簡単な使い方（例）
-----------------

1) DuckDB 接続を作って日次 ETL を実行する
- ETL パイプラインを使って株価・財務・カレンダーを更新し品質チェックを行います。

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())

注意: 実行前に JQUANTS_REFRESH_TOKEN が設定されている必要があります（get_id_token が内部で参照）。

2) ニュースセンチメント（銘柄別）を計算して ai_scores に保存
- OpenAI キーが必要です（環境変数 OPENAI_API_KEY または api_key 引数）。

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, date(2026,3,20))
print(f"scored {count} codes")

3) 市場レジーム判定を実行（マクロセンチメント + MA 乖離）
- OpenAI キーが必要です。

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026,3,20))

4) 監査ログ DB を初期化する
- 監査用 DuckDB を作成してテーブル群を作成します。

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")

5) 研究用ファクター計算例

from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))

設計上の注意点 / ポリシー
-----------------------
- ルックアヘッドバイアス回避
  - モジュール内で datetime.today() / date.today() を直接参照しない設計（target_date を明示的に渡す）
  - DB クエリは target_date より前のデータのみ参照するなどの対策が講じられています
- フェイルセーフ
  - API エラー時（OpenAI / J-Quants など）はゼロスコアやスキップで継続し、例外で処理全体を停止しない箇所が多くあります
- 冪等性
  - ETL の保存処理は ON CONFLICT DO UPDATE / INSERT ... DO UPDATE などで冪等に設計
- セキュリティ
  - RSS 収集では SSRF 対策、defusedxml を用いたパース等を実施

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / .env 自動読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py             — ニュース集約・OpenAI による銘柄別スコア化
  - regime_detector.py      — ETF MA + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py  — 市場カレンダー管理 / 営業日ユーティリティ
  - etl.py                  — ETLResult 再エクスポート
  - pipeline.py             — 日次 ETL パイプライン・個別 ETL ジョブ
  - stats.py                — zscore 正規化など統計ユーティリティ
  - quality.py              — データ品質チェック（missing/spike/duplicates/date）
  - audit.py                — 監査ログスキーマ初期化 / audit DB 初期化
  - jquants_client.py       — J-Quants API クライアント（fetch/save 等）
  - news_collector.py       — RSS 取得・前処理・raw_news 挿入
- research/
  - __init__.py
  - factor_research.py      — Momentum / Volatility / Value ファクター
  - feature_exploration.py  — 将来リターン / IC / 統計サマリー 等

開発・テストに関する補足
-----------------------
- 自動 env 読み込みを無効化したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 関連の呼び出しは内部で独立した _call_openai_api 関数を用いており、ユニットテスト時はパッチしてモック化できます（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- DuckDB 操作は接続オブジェクトを受け取る設計のため、インメモリ DB (":memory:") を用いてテスト可能です。
- ロギングは各モジュールで logger = logging.getLogger(__name__) を用いているため、必要に応じてアプリ側でハンドラ/レベルを設定してください。

よくある質問
-----------
Q: OpenAI のレスポンスが壊れていたらどうなる？
A: news_nlp / regime_detector は JSON パース失敗時は警告ログを出してそのチャンクをスキップまたは score=0.0 にフォールバックします。例外を投げて処理全体を止めない設計です。

Q: J-Quants のレート制限はどう対策している？
A: jquants_client は固定間隔スロットリング（120 req/min）と指数バックオフを実装しています。401 はトークン自動リフレッシュで 1 回だけ再試行します。

Q: バックテストでのルックアヘッド対策は？
A: 関数群は target_date を明示的に渡すことを前提にし、クエリも target_date より前のデータのみを参照する等、ルックアヘッドを避ける実装になっています。

ライセンス・貢献
----------------
（ここにライセンス情報や貢献方法を追記してください）

この README はコードベースの主要機能・使い方の概要をまとめたものです。必要があれば各モジュールの詳細な API ドキュメント（関数ごとの引数/戻り値/例外）を追加で生成できます。希望があればどのモジュールの詳細説明を優先するか教えてください。