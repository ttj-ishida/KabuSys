# KabuSys

KabuSys は日本株のデータプラットフォームと研究 / AI / ETL / 監査機能を備えた自動売買支援ライブラリです。本リポジトリにはデータ取得（J-Quants）、日次 ETL、ニュースの NLP 評価、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ初期化などの主要コンポーネントが含まれます。

---

## プロジェクト概要

目的:
- J-Quants API から日次株価・財務・マーケットカレンダーを差分取得して DuckDB に蓄積する ETL パイプライン
- RSS ニュース収集および OpenAI を用いたニュースセンチメントの銘柄別スコア化
- ETF（1321）を用いた市場レジーム判定（MA とマクロニュースの組合せ）
- ファクター（Momentum/Value/Volatility 等）計算と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）スキーマの初期化ユーティリティ

設計上のポイント:
- ルックアヘッドバイアス対策（関数内で date.today() を直接参照しない等）
- J-Quants API のレート制御・リトライ・トークン自動更新
- OpenAI 呼び出しに対するリトライとフェイルセーフ（失敗時はスコア 0.0 等で継続）
- ニュース収集の SSRF 対策、受信サイズ制限、トラッキングパラメータ除去
- DuckDB を中心に冪等設計（ON CONFLICT / DELETE→INSERT 等）

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数、トークン管理、レートリミット、リトライ）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得、前処理、raw_news 保存）
  - 品質チェック（欠損/スパイク/重複/日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込む
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（特徴量解析）
- config:
  - 環境変数＋.env 自動読み込み（.env, .env.local、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で各種設定を取得

※ strategy / execution / monitoring モジュール群はパッケージ公開対象に含まれますが（__init__ の __all__）この抜粋では詳細実装は含まれていません。

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の OR 表記 Path | None 等を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

推奨手順:

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（最低限）
   pip install duckdb openai defusedxml

   （実運用では logger の設定やその他ユーティリティを追加することを推奨）

4. 環境変数の設定
   プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY        : OpenAI API キー（news/regime 判定で使用）
   - KABU_API_PASSWORD     : kabu ステーション API パスワード（必要に応じて）
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視 DB（デフォルト data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / その他監視設定
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL             : DEBUG/INFO/...（デフォルト INFO）

   例 (.env):
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. DB 初期化（監査用例）
   下記のように DuckDB 接続を作り監査スキーマを初期化できます。

   from pathlib import Path
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db(Path("data/audit.duckdb"))
   # または既存接続に init_audit_schema(conn)

---

## 使い方（代表的な API 例）

以下は Python スクリプト内での代表的な呼び出し例です。

- ETL（日次パイプライン）を実行する例:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースのセンチメントを評価して ai_scores に書き込む（OpenAI API キーを環境変数に設定済の場合）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")

- 市場レジーム判定を行う（1321 の MA200 とマクロニュースを合成）:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算・研究ユーティリティ例:

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))

- 監査スキーマの初期化（既存 DuckDB 接続を利用）:

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)

注意点:
- OpenAI の呼び出しは rate / cost に注意して利用してください。
- J-Quants の呼び出しは本実装でレート管理を行っていますが、トークンと API 利用制限を順守してください。
- 多くの関数は Look-ahead バイアス対策のため target_date を引数で受け取る設計です。バックテスト時は対象日以前のデータのみを使用するよう注意してください。

---

## ディレクトリ構成

以下は本コードベースの主なファイルと概要（抜粋）です。

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / .env 自動読み込みと Settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py                  — ニュースを OpenAI でスコアリングし ai_scores へ保存
  - regime_detector.py           — ETF MA とマクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（fetch/save / auth / rate limit）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETLResult の再エクスポート等
  - calendar_management.py       — 市場カレンダー管理（営業日判定／更新ジョブ）
  - stats.py                     — zscore_normalize など統計ユーティリティ
  - quality.py                   — データ品質チェック（欠損/スパイク/重複/日付一致）
  - audit.py                     — 監査ログスキーマ初期化（signal/order_request/executions）
  - news_collector.py            — RSS 取得・前処理・raw_news 保存（SSRF 対策等）
- research/
  - __init__.py
  - factor_research.py           — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py       — calc_forward_returns / calc_ic / factor_summary / rank
- research/ 以下は研究用ユーティリティ群

（その他: strategy/, execution/, monitoring/ をパッケージとして公開予定）

---

## 追加情報・運用上の注意

- .env の自動ロード: プロジェクトルート（.git または pyproject.toml を上位ディレクトリに持つ場所）を起点に .env, .env.local を読み込みます。テスト時など自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは JSON-mode を用い、レスポンス検証・パースに失敗した場合はログを残してフェイルセーフ動作（スコア 0 等）を返します。
- J-Quants クライアントは固定間隔スロットリング（120 req/min）、リトライ、401 時のトークン自動更新などを実装しています。
- DuckDB に対する SQL は一部バージョン固有の挙動（executemany の空配列等）を考慮して実装されています。DuckDB のバージョンが古い/新しい場合に差異が生じる可能性があるため注意してください。
- 本リポジトリは金融データを扱うため、機密情報（API キー等）は安全に管理してください。

---

必要であれば、README に以下を追加できます:
- CI / テスト実行方法（pytest など）
- 詳細な .env.example（各変数の説明とフォーマット）
- デプロイ / 運用のための systemd / supervisor サンプル
- strategy / execution モジュールの使用例（本番発注フロー）

追加の要望があれば教えてください。README を用途に合わせて拡張します。