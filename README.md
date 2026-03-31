KabuSys — 日本株データプラットフォーム & 自動売買基盤
=================================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・自動売買のためのライブラリ群です。本コードベースは以下の要素を含みます：
- J-Quants API を用いた株価・財務・マーケットカレンダーの ETL
- RSS ベースのニュース収集（SSRF/DoS 対策済み）
- OpenAI を用いたニュース NLP（銘柄ごとのセンチメント）と市場レジーム判定
- 監査ログ（signal → order_request → executions）の DuckDB スキーマ
- 研究用ファクター計算・特徴量探索ユーティリティ
- データ品質チェック・カレンダー管理等の補助機能

主な特徴（機能一覧）
------------------
- データ取得 / 保存
  - J-Quants API 経由で日足（OHLCV）/ 財務 / 上場銘柄情報 / マーケットカレンダーを差分取得・保存（DuckDB）
  - 保存は冪等（ON CONFLICT DO UPDATE）で設計
- ETL
  - run_daily_etl による日次 ETL（カレンダー → 日足 → 財務 → 品質チェック）
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース
  - RSS 収集（トラッキングパラメータ削除、SSRF/プライベートアドレス対策、サイズ上限）
  - ニュース→銘柄紐付け → raw_news 保存
- AI（OpenAI）
  - 銘柄別ニュースを gpt-4o-mini に投げて銘柄ごとの ai_score を ai_scores に保存（score_news）
  - ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定（score_regime）
  - API 呼び出しは JSON Mode を使用、リトライ・バックオフを実装
- 監査ログ（audit）
  - signal_events / order_requests / executions を含む監査スキーマ生成・初期化
  - init_audit_db / init_audit_schema による DuckDB 初期化
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクターサマリー
- 設定管理
  - .env / .env.local を自動ロード（環境変数優先）、settings オブジェクトでアクセス可能

前提条件
--------
- Python 3.10+
- 必要な主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで動作する部分も多数）
- J-Quants のリフレッシュトークン、OpenAI API キーなど外部サービスの資格情報

インストール
-----------
例: ソースをローカルで開発する場合
1. リポジトリをクローン
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（以下は代表例）

pip install -e .  # setup.py / pyproject がある場合
pip install duckdb openai defusedxml

（プロジェクトに requirements.txt や pyproject.toml がある場合はそちらを使用してください）

環境変数 (.env)
----------------
プロジェクトは .env / .env.local を自動でプロジェクトルート（.git または pyproject.toml が基準）から読み込みます（ただし OS 環境変数が優先）。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主に必要な環境変数（一例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要なら）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用 Slack 設定
- DUCKDB_PATH: デフォルト data/kabusys.duckdb（省略時）
- SQLITE_PATH: 監視 DB（省略時）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/...

settings オブジェクトからアクセス:
from kabusys.config import settings
token = settings.jquants_refresh_token

セットアップ手順（簡易）
----------------------
1. .env を作成（.env.example を参照）
2. Python パッケージのインストール
3. DuckDB データベースの場所を確認（デフォルト: data/kabusys.duckdb）
   - 必要に応じて親ディレクトリを作成
4. 監査 DB を初期化（オプション）
   - Python セッション例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
5. ETL を一度実行してテーブル群を作成・データ取得
   - run_daily_etl を呼び出す（後述）

基本的な使い方（コード例）
------------------------

1) DuckDB 接続を取得して日次 ETL を実行
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) ニュースのスコアリング（AI）
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数

3) 市場レジームの判定（AI + MA200）
from datetime import date
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))

4) 監査 DB 初期化
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")

5) RSS 取得（ニュースコレクタ）
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

注意点・設計上のポイント
-----------------------
- ルックアヘッドバイアス防止:
  - 各処理は内部で date を明示的に受け取り、datetime.today()/date.today() を直接参照しないことを推奨しています（score_news / score_regime 等）。
- OpenAI 呼び出し:
  - JSON モードを用いて厳密な JSON レスポンスを期待します。API エラー時はフェイルセーフ（スコア 0 や処理スキップ）で継続する設計です。
- J-Quants クライアント:
  - レート制限（120 req/min）とリトライ・トークン自動更新を実装しています。
- .env ロード:
  - プロジェクトルート検出は .git または pyproject.toml を基準に行います。見つからない場合は自動ロードをスキップします。

主要モジュール / ディレクトリ構成
------------------------------
（抜粋。詳しくはリポジトリを参照してください）

src/kabusys/
- __init__.py
- config.py                 — 環境変数/設定管理（settings）
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP（score_news）
  - regime_detector.py      — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント / 保存関数
  - pipeline.py             — ETL パイプライン（run_daily_etl, run_prices_etl...）
  - etl.py                  — ETLResult 再エクスポート
  - news_collector.py       — RSS 収集（fetch_rss 等）
  - calendar_management.py  — 市場カレンダー管理
  - quality.py              — データ品質チェック
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - audit.py                — 監査ログスキーマ初期化（init_audit_db）
- research/
  - __init__.py
  - factor_research.py      — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py  — calc_forward_returns / calc_ic / factor_summary / rank

README に載せきれないが重要な点
-------------------------------
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。運用時は settings.duckdb_path に接続して利用してください。
- OpenAI を使う処理は API キーの設定（引数経由または OPENAI_API_KEY 環境変数）が必須です。キー未設定時は ValueError を投げます。
- news_collector は SSRF 対策（リダイレクト検査・プライベートホスト拒否）・レスポンスサイズ制限を実装しています。
- 監査スキーマは冪等に作成できます。init_audit_schema の transactional 引数でトランザクション制御が可能です（DuckDB のトランザクション挙動に注意）。

ライセンス・貢献
----------------
（ここにはプロジェクトのライセンスや貢献方法を記載してください。リポジトリに LICENSE があればそちらを参照してください）

問い合わせ
----------
不明点や使い方の質問はプロジェクトの issue またはリポジトリ管理者にお問い合わせください。

以上。必要ならセットアップ用の .env.example のテンプレートや、よく使うサンプルスクリプト（ETL定期実行・ニューススコアリングの cron/airflow 例）を追加で作成します。どの出力を優先してほしいか教えてください。