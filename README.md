# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買（研究・シグナル・監査）を支援するライブラリ群です。J-Quants / DuckDB を用いたデータ ETL、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログスキーマなどを含みます。

主な目的は、
- データ収集・保存・品質チェックの自動化（J-Quants 経由）
- ニュースに基づく銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF + マクロニュース）
- 研究用ファクター計算・特徴量探索
- 発注・約定の監査ログスキーマ提供
などです。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local からの自動読み込み（無効化可能）
  - 必須設定の取得ユーティリティ
- データ ETL（J-Quants クライアント）
  - 株価日足（OHLCV）取得・保存（raw_prices）
  - 財務データ取得・保存（raw_financials）
  - JPX マーケットカレンダー取得・保存（market_calendar）
  - 差分更新、ページネーション、レートリミット、リトライを実装
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出
- ニュース収集・前処理
  - RSS フィード取得、SSRF 対策、トラッキングパラメータ除去、正規化、raw_news 保存想定
- ニュース NLP（OpenAI）
  - 銘柄別センチメント（ai_scores）を OpenAI（gpt-4o-mini）で評価
  - レスポンス検証・バッチ処理・リトライ実装
- レジーム判定
  - ETF 1321 の MA 乖離 + マクロニュースセンチメントから日次レジーム判定（bull/neutral/bear）
- 研究モジュール
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Z スコア正規化
- 監査ログ（audit）
  - signal_events, order_requests, executions テーブル定義と初期化ユーティリティ
  - 監査／トレーサビリティ設計（UUID ベースの階層）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントで `|` 演算子等を利用）
- DuckDB、OpenAI SDK 等の依存パッケージ

推奨インストール手順（プロジェクトルートで）:

1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 以下は代表的な依存パッケージ例です（requirements.txt があればそれを使ってください）。
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートの `.env`（または `.env.local`）に必要な設定を記載します。config モジュールは自動でプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（一例）
- JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API のパスワード（使用する場合）
- OPENAI_API_KEY : OpenAI を利用する場合に必要（score_news / score_regime）
- その他（任意）:
  - KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
  - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL
  - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH など（デフォルトは code 内で定義）

例 `.env`（最小）
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development

---

## 使い方（簡単な例）

基本的に DuckDB 接続を作成し、各モジュール API を呼び出します。以下は一例です。

1) ETL（日次 ETL の実行例）
- ETL パイプラインを実行して prices / financials / calendar を更新し、品質チェックを行う:

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュース NLP（ai スコア算出）
- OpenAI API キーが環境変数または引数で設定されている必要があります。

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")

3) レジーム判定（market_regime へ書き込み）
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログ初期化（独立した DuckDB ファイル）
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# これで監査ログ用テーブルが作成される

5) RSS フィードの取得（ニュース収集）
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])

注意点:
- OpenAI 呼び出しは HTTP リトライや JSON 検証を行いますが、API キーと API 利用量制限に注意してください。
- DuckDB のスキーマ（例: raw_prices, raw_financials, market_calendar, ai_scores, market_regime, etc.）は別途初期化・DDL 実行が必要です（ETL 実行前にスキーマを準備してください）。プロジェクトにはスキーマ初期化ユーティリティが含まれている場合があります（audit モジュールの init_audit_schema を参照）。

---

## 設定と環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必要時) : OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD (必要時) : kabu API パスワード
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : ログレベル（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化（値を設定すると自動ロードを行わない）

config.Settings クラスから各設定値を参照できます:
from kabusys.config import settings
settings.jquants_refresh_token
settings.duckdb_path
settings.is_live など

---

## ディレクトリ構成（主要ファイル概要）

src/kabusys/
- __init__.py
  - パッケージ初期化、バージョン情報
- config.py
  - .env 自動読み込み、Settings クラス（環境変数管理）
- ai/
  - __init__.py
  - news_nlp.py : ニュースセンチメントのバッチスコアリング（OpenAI）
  - regime_detector.py : ETF + マクロニュースを組み合わせた市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得 + DuckDB 保存ユーティリティ）
  - pipeline.py : ETL パイプライン（run_daily_etl 等）
  - etl.py : ETL 結果クラス再エクスポート
  - quality.py : データ品質チェック
  - stats.py : 統計ユーティリティ（zscore_normalize）
  - news_collector.py : RSS 取得・前処理・SSRF 対策
  - calendar_management.py : 市場カレンダー管理（営業日判定、カレンダー更新ジョブ）
  - audit.py : 監査ログスキーマ初期化（signal_events / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py : モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py : 将来リターン, IC, 統計サマリー 等

補足:
- 各モジュールは DuckDB 接続オブジェクト（duckdb.connect() で得られる接続）を受け取り、SQL と Python の組合せで処理します。
- OpenAI 呼び出しは openai.OpenAI クライアントを利用する設計で、ユニットテストでは内部の API 呼び出し関数をパッチして差し替え可能にしています。

---

## 注意事項 / ベストプラクティス

- Look-ahead bias の防止:
  - 多くの関数は内部で現在時刻（datetime.today()）を直接参照しない設計です。ETL や評価時は明示的に target_date を渡してください。
- 秘密情報（API キー等）は .env または秘密管理システムで管理し、リポジトリにコミットしないでください。
- OpenAI や J-Quants の API 利用はレート制限・課金に注意してください。
- DuckDB のスキーマ・初期テーブル作成はプロジェクトのスキーマ初期化コードを参照して行ってください（audit.init_audit_schema のようなユーティリティを参照）。

---

必要であれば、README に実際のスキーマ初期化手順（DDL 実行例）やサンプルスクリプト、requirements.txt の推奨内容、CI 用の設定例なども追記できます。どの追加情報が必要か教えてください。