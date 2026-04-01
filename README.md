KabuSys — 日本株自動売買プラットフォーム
=======================================

概要
----
KabuSys は日本株のデータ取得（ETL）、データ品質チェック、ファクター計算、ニュース NLP（LLM）を用いた銘柄センチメント評価、さらに市場レジーム判定や監査ログ（発注／約定のトレーサビリティ）等の機能を提供するライブラリ群です。内部では DuckDB をデータ格納に用い、J-Quants API / OpenAI API / kabu ステーション等と連携することを想定しています。

主な特徴
--------
- データ取得（J-Quants）: 日足、財務、上場銘柄、JPXカレンダーをページネーション対応で取得・保存（冪等）。
- ETL パイプライン: 差分更新・バックフィル・品質チェック（欠損、スパイク、重複、日付不整合）。
- ニュース NLP: OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（batch, retry, JSON mode 対応）。
- 市場レジーム判定: ETF（1321）200日移動平均乖離とマクロニュースセンチメントの合成による日次レジーム判定。
- 研究用ユーティリティ: モメンタム / バリュー / ボラティリティなどのファクター計算、将来リターン、IC 計算、Z スコア正規化等。
- カレンダー管理: market_calendar に基づく営業日判定・前後営業日の探索・夜間更新ジョブ。
- 監査ログ（audit）: signal → order_request → execution の階層トレースを保存する監査スキーマを提供。
- セキュリティ・堅牢性: SSRF 対策、XML パース保護、API リトライ・バックオフ、レートリミット管理、フェイルセーフ設計。

セットアップ手順
----------------

1. リポジトリをクローン
   - 例: git clone <repository-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（コードベース参照）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   - （開発用や追加依存がある場合は requirements.txt / pyproject.toml を参照）

4. パッケージをインストール（開発モード）
   - pip install -e .

5. 環境変数設定
   - .env または実環境変数で下記を設定してください（最低限必要なものは太字で示します）:

     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (必須 for NLP/regime) — OpenAI API キー（score_news / score_regime を直接呼ぶ場合）
     - KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
     - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（利用する場合）
     - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネルID
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   - .env 自動ロード:
     - パッケージはプロジェクトルート（.git or pyproject.toml を基準）にある .env / .env.local を自動読み込みします。
     - 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（簡易サンプル）
--------------------

以下は主要な利用例です。各関数は DuckDB 接続（duckdb.connect(...)）を受け取ります。

1) DuckDB 接続を開く
   - from kabusys.config import settings
   - import duckdb
   - conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL 実行（市場カレンダー → 日足 → 財務 → 品質チェック）
   - from kabusys.data.pipeline import run_daily_etl
   - from datetime import date
   - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   - print(result.to_dict())

3) ニュースセンチメントスコア算出（LLM により銘柄ごとにスコア）
   - from kabusys.ai.news_nlp import score_news
   - from datetime import date
   - written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
   - print(f"書き込み銘柄数: {written}")

   - 注意: API キーを引数に与えることもできます: score_news(conn, date, api_key="sk-...")

4) 市場レジーム判定
   - from kabusys.ai.regime_detector import score_regime
   - from datetime import date
   - score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーが必要

5) 監査ログ用データベース初期化（監査専用 DB を作成）
   - from kabusys.data.audit import init_audit_db
   - audit_conn = init_audit_db("data/audit.duckdb")
   - # これで signal_events / order_requests / executions テーブルが作成されます

6) J-Quants ID トークン取得（直接使用する場合）
   - from kabusys.data.jquants_client import get_id_token
   - token = get_id_token()  # settings.jquants_refresh_token を使用

注意点・運用メモ
----------------
- Look-ahead bias 対策として、多くの関数は内部で date.today() を安易に参照しません。バックテスト等での使用時は target_date を明示してください。
- OpenAI 呼び出しはリトライ/バックオフ実装がありますが、API コストやレート制限に注意してください。
- ニュース収集モジュールは RSS のリダイレクトや URL を検査して SSRF を防止する設計です。fetch_rss はネットワーク制約・サイズ制限があります。
- 自動 .env ロードはプロジェクトルート検出に基づきます。意図しない環境設定を避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。
- DuckDB の executemany に関する互換性（空リスト不可）など実装上の注意があります（pipeline, news_nlp 等のコメント参照）。

ディレクトリ構成（主要ファイル）
------------------------------

- src/kabusys/
  - __init__.py                    — パッケージ定義（バージョン等）
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（銘柄ごとのスコア算出）
    - regime_detector.py          — 市場レジーム判定（ETF + マクロ NLP）
  - data/
    - __init__.py
    - calendar_management.py      — JPX カレンダー管理・営業日判定
    - etl.py                      — ETL 公開インターフェース（ETLResult エクスポート）
    - pipeline.py                 — 日次 ETL パイプライン（差分取得・保存・品質チェック）
    - stats.py                    — 統計ユーティリティ（Zスコア等）
    - quality.py                  — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                    — 監査ログスキーマ初期化（signal/order/execution）
    - jquants_client.py           — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py           — RSS ニュース収集（前処理・保存）
  - research/
    - __init__.py
    - factor_research.py          — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py      — 将来リターン / IC / 統計サマリー 等

開発者向けメモ
---------------
- テスト時は環境変数自動読み込みを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部通信部分はモジュール内部で差し替え（mock）しやすい設計になっています（例: news_nlp._call_openai_api を patch）。
- DuckDB の挙動やバージョン差異に注意（executemany の空リストなど）。

最後に
-----
この README はコードベースの主要設計・使い方をまとめた概要です。各モジュールの docstring に詳細な設計方針や挙動（フェイルセーフ／トランザクション運用等）が記載されていますので、実装・運用時は該当ファイルのドキュメントも参照してください。必要であれば導入用の .env.example や運用手順（cron / systemd / コンテナ化）例も追記できます。希望があれば作成します。