KabuSys — 日本株自動売買 / データプラットフォーム
=================================================

概要
----
KabuSys は日本株のデータ収集・品質管理・ファクター研究・ニュース解析・市場レジーム判定などを行うための内部ライブラリ群です。主に以下の用途を想定しています。

- J-Quants API からのデータ ETL（株価・財務・マーケットカレンダー）
- ニュースの収集・前処理と OpenAI を使った銘柄別センチメント解析
- 市場レジーム判定（ETF + マクロニュースの合成）
- 監査（監査ログ）テーブルの初期化・管理
- リサーチ用のファクター計算・特徴量解析ユーティリティ
- データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）

設計上のポイント
- Look‑ahead bias（ルックアヘッド）防止設計：日付は明示的に渡す／DBクエリは target_date 未満などの排他条件を厳密に使う
- 冪等性：DB への保存は ON CONFLICT（UPSERT）で上書きし再実行可能
- フェイルセーフ：外部 API 失敗時はゼロスコアやスキップなど安全側へフォールバック
- リトライ・レートリミット：J‑Quants や OpenAI 呼び出しはリトライ／バックオフ・レート制御あり

主な機能一覧
---------------
- dataパッケージ
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save 日足・財務・カレンダー・上場情報）
  - 市場カレンダー管理（営業日判定 / next_trading_day / get_trading_days）
  - ニュース収集（RSS fetch_rss / 前処理 / raw_news への保存ロジック）
  - データ品質チェック（missing, spike, duplicates, date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- aiパッケージ
  - news_nlp: RSS/raw_news をまとめて OpenAI に投げ、銘柄別 ai_score を ai_scores テーブルへ書き込む（score_news）
  - regime_detector: ETF（1321）200日 MA 乖離 + マクロニュース LLM センチメントを合成して日次の market_regime を書き込む（score_regime）
- researchパッケージ
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算 / IC（calc_forward_returns, calc_ic）
  - 統計サマリー / ランクユーティリティ

セットアップ手順
-----------------
前提
- Python 3.10 以上（typing の新構文を使用）
- システム上にネットワーク接続（J-Quants / OpenAI 利用時）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリインストール
   - 必須（例）:
     - duckdb
     - openai
     - defusedxml
   - 具体的には:
     - pip install duckdb openai defusedxml

   （パッケージ要件ファイル requirements.txt が存在する場合は pip install -r requirements.txt）

4. パッケージを editable インストール（任意）
   - pip install -e .

環境変数 / .env
----------------
モジュール kabusys.config はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から .env / .env.local を自動ロードします。自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（必須・推奨）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（約定周り）
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー（news_nlp / regime_detector）
- LINE_CHANNEL_ACCESS_TOKEN (任意) — LINE 通知に使う場合
- LINE_USER_ID (任意)
- DUCKDB_PATH (任意) — デフォルト data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト data/monitoring.db
- PID_FILE_PATH, KILL_FLAG_PATH など（監視用）

例 (.env)
- JQUANTS_REFRESH_TOKEN=xxxxx
- OPENAI_API_KEY=sk-xxxx
- KABU_API_PASSWORD=your_pass
- DUCKDB_PATH=data/kabusys.duckdb

使い方（主要な呼び出し例）
--------------------------

基本的な DuckDB 接続
- メイン DB ファイルに接続して ETL 等を実行する例:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

ニューススコアリング（OpenAI 必須）
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")

市場レジーム判定（OpenAI 必須）
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

監査ログ DB 初期化
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定される

J-Quants ETL の個別実行
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))  # 日足
fetched_fin, saved_fin = run_financials_etl(conn, target_date=date(2026,3,20))
fetched_cal, saved_cal = run_calendar_etl(conn, target_date=date(2026,3,20))

RSS 取得（ニュース収集の一部）
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["title"], a["datetime"])

注意事項 / 運用メモ
-----------------
- OpenAI 呼び出しは API コストおよびレイテンシが発生します。batch size やモデル選択（gpt-4o-mini 等）を運用に合わせて調整してください。
- J-Quants の API レート制限に従うため内部でレートリミッタを使用しています。大量のページネーションを伴う処理では時間がかかることがあります。
- ETL・AI 処理はルックアヘッドバイアスを起こさない設計になっています。target_date は必ず明示的に渡すことを推奨します。
- テストや CI で環境変数自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py           — パッケージ初期化（バージョン等）
- config.py             — 環境変数 / .env 自動ロード / Settings
- ai/
  - __init__.py
  - news_nlp.py         — ニュース NLP（score_news）
  - regime_detector.py  — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py         — ETL パイプライン（run_daily_etl 他）
  - jquants_client.py   — J-Quants API クライアント（fetch/save 系）
  - news_collector.py   — RSS 取得 / 前処理
  - quality.py          — データ品質チェック
  - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - audit.py            — 監査ログスキーマの初期化
  - etl.py              — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py  — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- (その他) strategy/, execution/, monitoring/ などのインターフェース層を想定（実装はモジュール内を参照）

開発 / テスト
--------------
- 各 API 呼出し関数（OpenAI / J-Quants / urllib）の内部呼び出しはテスト容易性を考慮して置き換えやすく設計されています（モック可能）。
- DuckDB を :memory: で使えばユニットテスト用の軽量 DB を構築できます。

ライセンス / コントリビューション
---------------------------------
（ここにプロジェクトのライセンスやコントリビュートルールを記載してください。リポジトリ固有の情報があれば追記してください。）

---

README は主要な利用方法と設計方針を簡潔にまとめています。実際の運用では .env.example を用意して必要な環境変数を明示し、CI / デプロイ手順（systemd / supervisor などのプロセス管理、監視フラグファイル等）を追加してください。必要であれば README の実行例や CLI ラッパー例を追記します。