# KabuSys

KabuSys は日本株向けの自動売買 / データパイプライン / リサーチ基盤ライブラリです。  
DuckDB をデータ層に使い、J-Quants API で市場データを取得、OpenAI（gpt-4o-mini 等）でニュース NLP を行い、ファクター計算・品質チェック・監査ログなどのユーティリティを提供します。

主な設計方針
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を参照しない設計）
- DuckDB を用いた idempotent な ETL / 保存
- OpenAI / J-Quants API 呼び出しはリトライ・バックオフ等の耐障害性を考慮
- ニュース収集は SSRF 対策・トラッキングパラメータ除去などの安全設計

---

## 機能一覧

- 環境設定読み込み（.env / 環境変数）: kabusys.config.settings
- データ ETL（J-Quants からの株価・財務・カレンダー取得）: kabusys.data.pipeline.run_daily_etl 等
- J-Quants クライアント（rate limit / token refresh / pagination）: kabusys.data.jquants_client
- データ品質チェック（欠損・スパイク・重複・日付不整合）: kabusys.data.quality
- ニュース収集（RSS）: kabusys.data.news_collector.fetch_rss 等
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント）: kabusys.ai.news_nlp.score_news
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）: kabusys.ai.regime_detector.score_regime
- ファクター計算（Momentum / Value / Volatility 等）: kabusys.research.*
- 監査ログ（シグナル→発注→約定のトレーサビリティ）: kabusys.data.audit.init_audit_db / init_audit_schema
- 汎用統計ユーティリティ: kabusys.data.stats.zscore_normalize

---

## セットアップ手順

前提
- Python 3.10 以上（Union types, | 演算子などを使用）
- DuckDB, OpenAI SDK, defusedxml などの依存パッケージ

例: 仮想環境を作ってインストールする手順（プロジェクトルートで実行）

1. 仮想環境作成・有効化
   - unix/mac:
     python -m venv .venv
     source .venv/bin/activate
   - Windows:
     python -m venv .venv
     .venv\Scripts\activate

2. 必要パッケージのインストール（最低限）
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. 開発インストール（ソースを編集しながら使う場合）
   pip install -e .

環境変数（.env）  
プロジェクトは .env / .env.local を自動読み込みします（ただし CWD に依存せずパッケージのファイル位置からプロジェクトルートを探索）。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、ETL に使用）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）
- KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（default: data/monitoring.db）
- KABUSYS_ENV: execution 環境 ("development" | "paper_trading" | "live"), デフォルト development
- LOG_LEVEL: "DEBUG","INFO","WARNING","ERROR","CRITICAL"（デフォルト INFO）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（監視/実行管理用）

例 .env（プロジェクトルートに配置）
JQUANTS_REFRESH_TOKEN=xxxxxxx
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要な API と例）

※ 実行例は Python REPL / スクリプト内で行えます。DuckDB に対する接続は duckdb.connect(path) で取得します。

1) DuckDB 接続の作成
from datetime import date
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")

2) 日次 ETL を実行（J-Quants からデータ取得→保存→品質チェック）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 19))
print(result.to_dict())

- id_token を直接指定したい場合やバックフィル等のオプションも引数で指定可能。

3) ニュース NLP によるスコアリング
from kabusys.ai.news_nlp import score_news
from datetime import date
n_written = score_news(conn, target_date=date(2026,3,19))
print(f"AI スコアを書き込んだ銘柄数: {n_written}")

- OPENAI_API_KEY を引数 api_key に渡すか、環境変数で設定してください。
- テスト時は kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替え可能。

4) 市場レジーム判定
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,19), api_key=None)  # 環境変数 OPENAI_API_KEY を使用

5) 監査ログ DB の初期化
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# 監査テーブルが作成されます（UTC タイムゾーン固定）

6) RSS 取得（ニュース収集）
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# 返り値は NewsArticle のリスト（id, datetime, source, title, content, url）

---

## テストとモックのポイント

- OpenAI 呼び出しは各モジュール内の _call_openai_api を呼んでいるため、ユニットテストではそれらを patch して応答を制御できます。
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
- J-Quants API 呼び出しは kabusys.data.jquants_client._request 経由。get_id_token や fetch_* をモックすると ETL の外部依存を切れます。
- News collector のネットワーク呼び出しは kabusys.data.news_collector._urlopen を差し替えてテスト可能。

---

## ディレクトリ構成

以下は主要なソースツリーの抜粋（src/kabusys 以下）:

src/kabusys/
- __init__.py                (パッケージ定義 / バージョン)
- config.py                  (環境変数 / 設定管理)
- ai/
  - __init__.py
  - news_nlp.py              (ニュースセンチメント → ai_scores)
  - regime_detector.py       (マクロ + ETF MA による市場レジーム判定)
- data/
  - __init__.py
  - jquants_client.py        (J-Quants API クライアント、保存ロジック)
  - pipeline.py              (ETL パイプライン実装 / run_daily_etl)
  - quality.py               (データ品質チェック)
  - news_collector.py        (RSS 収集 / 前処理 / 保存)
  - calendar_management.py   (市場カレンダー管理 / is_trading_day 等)
  - audit.py                 (監査ログスキーマ初期化)
  - etl.py                   (ETLResult 再エクスポート)
  - stats.py                 (zscore_normalize 等の統計ユーティリティ)
- research/
  - __init__.py
  - factor_research.py       (momentum/value/volatility)
  - feature_exploration.py   (forward returns, IC, factor summary, rank)

パッケージは上記モジュールを通じて、ETL/研究/運用/監査に必要な機能を提供します。

---

## 運用上の注意・実践的なヒント

- 環境設定は .env/example をプロジェクトルートに配置して管理してください。config モジュールは自動的に .env → .env.local の順で読み込みます（既に OS 環境変数がある場合は上書きしません）。テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB ファイルは path の親ディレクトリを事前に作成することを推奨します（audit.init_audit_db は親ディレクトリを自動作成します）。
- OpenAI 呼び出しはレート・エラー時にフェイルセーフで 0.0 を返す等の処理が入っていますが、本番では API キーのローテーションや利用制限に注意してください。
- ETL の run_daily_etl は各ステップでエラーを捕捉して継続します。戻り値の ETLResult をチェックしてエラーや品質問題に対応してください。

---

必要であれば、README に以下の追加を作成できます:
- .env.example の完全なテンプレート
- 具体的な SQL スキーマ一覧（テーブル定義）
- デプロイ / systemd サービス例（実行/監視の運用例）
- CI / テスト実行手順

どれを追加希望か教えてください。