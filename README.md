KabuSys — 日本株自動売買 / データプラットフォーム
=================================================

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ、AI ベースのニュース解析、監査ログ、ETL、マーケットカレンダー管理などを含む自動売買・研究プラットフォームのコアライブラリです。  
主に DuckDB をデータレイヤーに用い、J-Quants API から市場データを取得、OpenAI（gpt-4o-mini 等）でニュースセンチメント評価を行い、研究・戦略モジュールへデータを供給します。

主な特徴（機能一覧）
------------------
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示的チェック（settings オブジェクト）
- データ取り込み（J-Quants クライアント）
  - 株価（日足）・財務データ・マーケットカレンダーの取得（ページネーション対応、リトライ、レートリミット）
  - DuckDB への冪等保存（ON CONFLICT / upsert）
- ETL パイプライン
  - 日次 ETL（calendar / prices / financials）と品質チェックの一括実行（run_daily_etl）
  - 差分フェッチ、バックフィル、品質（欠損・スパイク・重複・日付不整合）検査
- ニュース収集
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news へ冪等保存
- AI（ニュース NLP / レジーム判定）
  - ニュース記事をまとめて LLM に投げて銘柄ごとのセンチメントスコアを ai_scores に保存（score_news）
  - ETF（1321）200日 MA 乖離 + マクロニュース LLM を組み合わせた市場レジーム判定（score_regime）
  - OpenAI API 呼び出しはリトライ・失敗フォールバックあり
- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター算出（research パッケージ）
  - 将来リターン計算、IC（情報係数）計算、Zスコア正規化等
- 監査ログ（audit）
  - signal / order_request / execution を追跡する監査テーブル作成ユーティリティ（init_audit_schema / init_audit_db）

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈や代替記法に依存）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

1. リポジトリをクローン
   - git clone <repo-url>
   - 例: git clone https://example.com/your-repo.git

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合）pip install -r requirements.txt
   - 開発時は pip install -e . で編集可能インストール

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。
   - 必要な主要環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...    （必須：J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD=...       （必須：kabuステーション API 用）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...          （score_news/score_regime に渡すか環境変数で設定）
     - DUCKDB_PATH=data/kabusys.duckdb  （省略時のデフォルト）
     - SQLITE_PATH=data/monitoring.db   （省略時のデフォルト）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

   .env の例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG

使い方（基本例）
---------------

以下は最小限の実行例（Python スクリプトや REPL で実行）。

1) DuckDB 接続と ETL 日次実行
- ETL を実行して J-Quants からデータを取得・保存する例:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルに接続（デフォルトパスは settings.duckdb_path）
conn = duckdb.connect("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日が対象）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))

# 結果の確認
print(result.to_dict())

2) ニュース NLP スコアリング（AI）
- OpenAI API キーを環境変数に設定している前提:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written_count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written_count}")

- api_key を直接渡すことも可能（api_key="sk-..."）

3) 市場レジーム判定
- ETF 1321 の MA とマクロニュースで日次レジームを判定:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数または api_key 引数で指定

4) 監査 DB を初期化（監査ログ専用 DB を用いる）
- 監査ログ用 DuckDB を作成・初期化:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成された接続が返る

注意点・運用メモ
----------------
- 環境変数は .env / .env.local をプロジェクトルートから自動読み込みします（os 環境 > .env.local > .env の優先順）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは外部 API を使うためレイテンシ・料金が発生します。ローカル開発やテストではモック（unittest.mock）で _call_openai_api を差し替えることを推奨します（コード内に差し替えを想定したコメントあり）。
- J-Quants API はレート制限を厳守する設計になっているため過負荷になりにくいですが、大量同時実行は避けてください。
- DuckDB の executemany に空リストを与えると問題になるバージョンがあるため、コードは空チェックを入れてあります（注意は不要ですが設計思想として記載）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数 / 設定管理（settings）
- ai/
  - __init__.py
  - news_nlp.py                      — ニュース NLP（score_news）
  - regime_detector.py               — レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                — J-Quants API クライアント（fetch/save）
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - etl.py                           — ETL 結果型公開（ETLResult）
  - news_collector.py                — RSS ニュース収集
  - calendar_management.py           — マーケットカレンダー管理（is_trading_day 等）
  - quality.py                       — データ品質チェック
  - stats.py                         — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                         — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py               — ファクター計算（momentum/value/volatility）
  - feature_exploration.py           — 将来リターン・IC・統計サマリー等
- research/... other modules
- その他: strategy/ execution/ monitoring のプレースホルダ（パッケージ公開設定あり）

（上記は主なファイルを抜粋しています。詳細は src/kabusys 以下を参照してください。）

貢献・開発
---------
- 開発時は仮想環境を使い、必要な依存を追加してください。
- テスト時に環境変数自動ロードを無効にしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI API 呼び出しはモック可能なように実装に配慮されています（ユニットテストでは _call_openai_api を patch してください）。

ライセンス / 著作権
-----------------
- この README ではコードのライセンス情報を記載していません。実プロジェクトでは LICENSE ファイルを確認してください。

補足（よくある質問）
-------------------
Q: OpenAI API キーがなくても動きますか？
A: 一部機能（score_news, score_regime）は OpenAI API を必要とします。API キーを渡すか環境変数 OPENAI_API_KEY を設定してください。API 呼び出し失敗時はフェイルセーフ（0.0 などのフォールバック）する設計の箇所もありますが、主要機能は意味ある出力を得られません。

Q: DuckDB ファイルはどこに置かれますか？
A: settings.duckdb_path のデフォルトは data/kabusys.duckdb。settings.sqlite_path は data/monitoring.db。必要に応じて .env で上書きしてください。

Q: 自動で .env を読み込む仕組みはどのように動きますか？
A: config モジュールはパッケージ設置位置から親ディレクトリを遡って .git または pyproject.toml を検出しプロジェクトルートを決定します。プロジェクトルートが見つかれば .env を読み込み（OS 環境変数を上書きしない）、次に .env.local を読み込み（上書き許可）します。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

最後に
------
この README はコード内の設計思想と API（公開関数）を簡潔に説明することを目的としています。実運用前に .env に必要な値を設定し、ローカルで ETL と品質チェックを行って動作を確認してください。追加の詳細や運用ドキュメント、運用手順（ジョブスケジューリング、監視、ロギング設定等）はプロジェクトの上流ドキュメント（Design/Operations）を参照してください。