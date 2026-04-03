# KabuSys

日本株向け自動売買 / データ基盤ライブラリセット。  
市場データのETL、ニュース収集・NLPスコアリング、研究用ファクター計算、監査ログ・発注トレーサビリティ、AIを利用した市場レジーム判定などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部で datetime.today() を直接参照しない設計）
- DuckDB を中心としたローカル分析データベース
- 外部 API 呼び出しに対する堅牢なリトライ・バックオフ・レート制御
- ETL / 品質チェック / 監査ログの冪等性（idempotency）重視

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（主要）
- 注意事項・設計上のポイント
- ディレクトリ構成（ファイル一覧）

---

プロジェクト概要
----------------
KabuSys は日本株のデータプラットフォームと自動売買に関連するユーティリティ群を提供する Python パッケージです。主な用途は次のとおりです：

- J-Quants API からの株価 / 財務 / カレンダー等の差分 ETL
- RSS からのニュース収集と銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（銘柄別）およびマクロセンチメント（市場レジーム）の評価
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化ユーティリティ

---

機能一覧
--------
- 環境設定自動読み込み（.env / .env.local 優先度、プロジェクトルート検出）
- J-Quants クライアント（認証・ページネーション・レートリミット・保存用ユーティリティ）
- ETL パイプライン（run_daily_etl 等）
- ニュース収集（RSS、SSRF対策、前処理、raw_news への冪等保存）
- ニュース NLP（銘柄毎のセンチメント ai_scores への書込み）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコア合成）
- 研究モジュール（ファクタ計算、将来リターン、IC、統計サマリー、Zスコア正規化）
- データ品質チェック（QualityIssue を返す）
- 監査ログ初期化（audit schema / init_audit_db）
- DuckDB ユーティリティ（統計・日付管理・カレンダー処理等）

---

セットアップ手順
---------------
前提
- Python 3.10 以上（typing の | 記法を使用）
- DuckDB にアクセス可能な環境

推奨手順（開発環境）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）
   - pip install -e .[dev]
   必要な主な依存：
     - duckdb
     - openai（または OpenAI の新 SDK、ソース内で OpenAI クラスを使用）
     - defusedxml
     - その他（標準ライブラリ中心に実装されていますが、requests を使う箇所があれば追加）

（注）プロジェクトには setup.py / pyproject.toml がある想定で pip install -e . をしています。無ければ必要パッケージを手動で pip install してください。

環境変数の準備
- プロジェクトルートに .env または .env.local を作成して必要なキーを設定してください（下記参照）。パッケージ起動時に自動で読み込まれます。ただしテスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主要な環境変数（必須・任意）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- OPENAI_API_KEY (必須 for NLP/Regime) — OpenAI API キー（score_news / score_regime を使う場合）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注関連）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用途（任意）
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH 等 — データ/監視用パス（省略可能, デフォルト値あり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例 .env（最小）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...

---

簡単な使い方（コード例）
------------------------

- 設定取得（settings）
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.env)

- DuckDB 接続して日次 ETL 実行（例）
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())

- ニュースセンチメント（銘柄別）をスコア化して ai_scores に書き込む
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print("scored stocks:", written)

- 市場レジーム判定（market_regime テーブルへ書き込み）
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20))

- 監査DB 初期化（専用 DB）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算（例）
from kabusys.research.factor_research import calc_momentum
momentum = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

各関数は docstring に引数・返り値を詳述しているため、そちらを参照してください。

---

ディレクトリ構成（主要ファイル）
------------------------------
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント（銘柄別）
  - regime_detector.py     — マクロセンチメント＋ETF MA による市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得/保存）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult 再エクスポート
  - news_collector.py      — RSS ニュース収集（SSRF 対策、前処理）
  - calendar_management.py — 市場カレンダー管理（営業日判定など）
  - quality.py             — 品質チェック（欠損・スパイク・重複・日付）
  - stats.py               — Zスコア等統計ユーティリティ
  - audit.py               — 監査ログスキーマ初期化 / init_audit_db
- src/kabusys/research/
  - __init__.py
  - factor_research.py     — モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py — 将来リターン / IC / サマリー等
- その他：strategy, execution, monitoring 用のトップレベル公開（パッケージ __all__ に含むが別ファイル群は省略）

---

注意事項・設計上のポイント
------------------------
- 環境変数の自動読み込み：config モジュールはプロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動読み込みします。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Look-ahead bias 対策：AI スコアリング・ETL・リサーチ関数は内部で date 引数ベースで動作し、datetime.today() を直接参照しないよう設計されています。バックテストでの使用時は target_date の取り扱いに注意してください。
- OpenAI 呼び出し：gpt-4o-mini（コード中の定数）を使うように設計されています。API レスポンスのパース失敗や API エラー時にはフェイルセーフ（多くの場合スコア 0.0 を返し続行）する実装です。ただし実デプロイ時は API キー管理・コスト管理に注意してください。
- J-Quants API：リフレッシュトークンからの id_token 自動更新、固定間隔レートリミット（120 req/min）、リトライ、ページネーション対応などを備えています。get_id_token / fetch_daily_quotes / save_* 系ユーティリティを利用してください。
- セキュリティ：news_collector で SSRF 対策（リダイレクト検査、プライベートアドレス拒否）、defusedxml を使用した XML パース等に配慮しています。

---

トラブルシューティング
----------------------
- 環境変数が見つからない場合、config.Settings のプロパティは ValueError を投げします（必須のキー）。
- DuckDB の SQL 実行でエラーが出る場合、スキーマが未作成である可能性があります。audit.init_audit_schema や ETL の初回実行で必要テーブルを作成してください。
- OpenAI / J-Quants の API 呼び出しで 401 が出る場合はトークンの有効性・環境変数設定を確認してください。J-Quants は自動リフレッシュを行いますが、リフレッシュトークン自体が無効だと失敗します。

---

貢献 / 拡張
-----------
- 新しいニュースソース追加：news_collector.DEFAULT_RSS_SOURCES に追加し、fetch_rss を利用して保存処理を追加してください。
- 新しいファクター追加：research/factor_research.py に関数を追加し、zscore_normalize 等を活用してください。
- 実運用での実際の発注ロジック（kabu ステーション連携）は execution / strategy 層で実装してください（このコードベースはそのためのデータ・監査基盤を提供します）。

---

ライセンス
---------
プロジェクトのライセンス情報はリポジトリの LICENSE ファイルを参照してください。

---

この README はコードベース（src/kabusys）を元に記載しています。各関数・クラスの詳細な使用法は該当モジュールの docstring を参照してください。必要に応じて README を拡張しますので、使い方や追加してほしいセクションがあれば教えてください。