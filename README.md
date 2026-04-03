KabuSys — 日本株自動売買プラットフォーム (README)
=================================================

概要
----
KabuSys は日本株のデータ取得（ETL）・品質検査・特徴量算出・ニュース NLP（LLM）によるセンチメント算出・市場レジーム判定・監査ログ管理などを行うライブラリ群です。DuckDB をデータ層に用い、J-Quants API からのデータ取得・前処理・保存、OpenAI（gpt-4o-mini）によるニュース解析を想定した設計になっています。

主な特徴
--------
- データ取得（J-Quants）: 株価日足、財務データ、JPXカレンダーの差分取得（ページネーション・レート制御・トークン自動リフレッシュ対応）
- ETL パイプライン: 日次差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集: RSS からの収集、URL 正規化・SSRF対策・前処理・冪等保存
- ニュース NLP: OpenAI を用いた銘柄別センチメント（JSON モード）とチャンク・リトライ制御
- 市場レジーム判定: ETF（1321）の MA とマクロニュースセンチメントを重み合成し日次で 'bull'/'neutral'/'bear' 判定
- 研究用ユーティリティ: モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC 計算、Z スコア正規化
- 監査ログ（audit）: シグナル→発注→約定までトレースできる監査テーブル定義・初期化ユーティリティ
- 設定管理: .env 自動読み込み（プロジェクトルート検出）、環境変数ベースの設定アクセス

動作要件（概略）
----------------
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）
- J-Quants のリフレッシュトークン、OpenAI API キーなど環境変数

インストール
------------
パッケージを編集可能モードでインストールする例:

pip install -e .
pip install duckdb openai defusedxml

（プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

環境変数（主なもの）
-------------------
以下は主要な環境変数（大文字）です。プロジェクトルートの .env / .env.local を自動で読み込みます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用。関数呼び出しで api_key を明示することも可能）
- KABU_API_PASSWORD — kabuステーション API パスワード（自動売買執行用）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（任意）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動 .env 読み込みの挙動:
- プロジェクトルートは __file__ を起点に .git または pyproject.toml を探して決定します。
- 読み込み順は OS 環境 > .env.local > .env。自動ロードを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

セットアップ手順（例）
--------------------
1. Python と依存パッケージをインストール
   - Python 3.10+
   - pip install -e . && pip install duckdb openai defusedxml

2. .env を作成（.env.example を参照）
   - 必須: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY（または関数呼び出しで渡す）
   - 任意: DUCKDB_PATH（デフォルト: data/kabusys.duckdb）

3. DuckDB 用ディレクトリを作成（必要なら）
   - mkdir -p data

4. 監査DBを初期化する（オプション）
   - Python スクリプトで init_audit_db() を呼ぶ（例は下記）

基本的な使い方（Python スニペット）
----------------------------------

- DuckDB 接続の作成例:

from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（株価・財務・カレンダー・品質チェック）:

from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- ニュースセンチメントの算出（前日15:00～当日08:30 JST を対象）:

from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n}")

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュース合成）:

from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに結果が書き込まれます

- 監査 DB の初期化（監査専用 DB を作る）:

from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" を使ってインメモリ作成も可

注意点・設計ポリシー
------------------
- ルックアヘッドバイアス対策: ほとんどの機能は内部で date.today() 等に依存せず、明示的な target_date を受け取ります。バックテスト時に過去データのみ参照するよう設計されています。
- OpenAI 呼び出し: JSON mode を使い、レスポンスのバリデーション・リトライ・フォールバック（失敗時 0.0）を実装しています。モデル名は gpt-4o-mini。
- J-Quants クライアント: 固定間隔レートリミッタ（120 req/min）、リトライ、401 検出時のトークン自動再発行を備えます。
- RSS 収集: URL 正規化・トラッキング除去、SSRF 回避（プライベート IP や不正スキームのブロック）、受信サイズ制限、XML パースの安全化（defusedxml）などを実装しています。
- データ品質: 欠損、スパイク、重複、日付不整合を検出し QualityIssue オブジェクトで返します。ETL は Fail-Fast にならず、可能な処理は継続します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主なファイル／モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（銘柄別センチメント算出）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存関数）
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize など）
    - audit.py               — 監査ログ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - ai/（上記）
  - research/（上記）

開発・テスト
-------------
- 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテストなどで便利です）。
- OpenAI 呼び出しや外部 HTTP 呼び出しはテスト時にモック可能な設計になっています（モジュール内の _call_openai_api / _urlopen などを patch）。

運用上のヒント
--------------
- 本番環境（KABUSYS_ENV=live）では必ず API キーやパスワードの管理（シークレット管理）を行ってください。
- ETL スケジュールは営業日ベースの調整を行うため calendar ETL (run_calendar_etl) を事前に実行しておくと良いです。
- ニュース NLP / レジーム判定はコスト（OpenAI API）や実行時間を考慮してバッチ化してください。

ライセンス / 責任
----------------
本 README はコードベースの説明を目的とするものであり、実際の運用時は金融取引のリスク管理・法令順守を十分に行ってください。

補足
----
README の内容はコード内の docstring と実装に基づき作成しています。関数の詳細やパラメータは各モジュール（例: kabusys.data.pipeline, kabusys.ai.news_nlp など）の docstring を参照してください。必要ならサンプルスクリプトや CI 設定のテンプレートも追加できます。