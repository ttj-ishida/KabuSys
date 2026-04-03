# KabuSys

日本株向けの自動売買 / データプラットフォーム共通ライブラリ（KabuSys）

このリポジトリは、J-Quants や RSS、OpenAI（LLM）などを組み合わせて日本株のデータ ETL、ニュース NLP、市場レジーム判定、ファクター研究、監査ログ管理を行うためのモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない等）
- DuckDB を中心としたローカル DB 主導のデータ設計
- 冪等性（ON CONFLICT / idempotent 保存）とフォールトトレランス重視
- 外部 API はレート制御・リトライを備える

---

## 機能一覧

- データ ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック（kabusys.data.quality）
- ニュース収集・処理
  - RSS フィード収集、前処理、raw_news への冪等保存（kabusys.data.news_collector）
- ニュース NLP（LLM）
  - 銘柄ごとのニュースセンチメントを OpenAI に投げて ai_scores へ記録（kabusys.ai.news_nlp）
- 市場レジーム判定
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成（kabusys.ai.regime_detector）
- 研究用ファクター計算 / 特徴量解析
  - Momentum / Value / Volatility 等の自動計算、forward returns、IC や統計サマリー（kabusys.research）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査スキーマ初期化・DB作成（kabusys.data.audit）
- 設定管理
  - .env の自動読み込み、環境変数ラッパー（kabusys.config）

---

## 前提条件 / 依存関係

- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, json, logging, datetime などを使用

（実プロジェクトでは requirements.txt / pyproject.toml を用意してください。上記パッケージは最低限必要です。）

例（pip でのインストール）:
pip install duckdb openai defusedxml

---

## 環境変数（主要なもの）

設定は .env または環境変数で行います。パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索して自動で .env/.env.local を読み込みます（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

主なキー（kabusys.config.Settings 経由で取得）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / その他監視パラメータ
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/...

.env の読み込み順:
OS 環境変数 > .env.local > .env
（.env.local は .env をオーバーライド）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン、プロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate
3. 必要パッケージをインストール
   pip install duckdb openai defusedxml
4. .env を作成（.env.example を参考に）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - OpenAI を使う場合は OPENAI_API_KEY を設定
5. DuckDB の初期化（オプション）
   - 監査用 DB を作る例:
     python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

---

## 使い方（簡単な例）

以降のサンプルは Python REPL やスクリプト内で実行します。各例は duckdb を直接使用します。

1) 設定の利用
from kabusys.config import settings
print(settings.duckdb_path)

2) DuckDB に接続して日次 ETL を実行
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

3) ニュース NLP スコア（OpenAI 必須）
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn は duckdb 接続、target_date はスコアの基準日
n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")  # api_key を省略すると OPENAI_API_KEY 環境変数を参照
print(f"scored {n} symbols")

4) 市場レジーム判定
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を使う場合は api_key=None

5) 監査スキーマの初期化（既存の DuckDB 接続に追加）
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)

6) 研究用ファクター計算の例
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, date(2026,3,20))
print(len(factors))

---

## 自動 .env 読み込みについての注意

- パッケージはインポート時にプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を読み込みます。
- テストなどで自動ロードを無効化する場合は環境変数を設定:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env の読み込みルール:
  - export KEY=VALUE も許容
  - シングル/ダブルクォート内のエスケープを考慮したパース
  - inline コメントの取り扱い（クォート有無で挙動が異なります）

---

## ディレクトリ構成（要約）

src/kabusys/
- __init__.py (パッケージ定義)
- config.py (環境変数 / Settings)
- ai/
  - __init__.py
  - news_nlp.py (ニュースセンチメントスコアリング)
  - regime_detector.py (市場レジーム判定)
- data/
  - __init__.py
  - calendar_management.py (市場カレンダー管理)
  - etl.py (ETL インターフェース)
  - pipeline.py (ETL パイプライン実装)
  - stats.py (統計ユーティリティ)
  - quality.py (データ品質チェック)
  - audit.py (監査スキーマ初期化)
  - jquants_client.py (J-Quants API クライアント)
  - news_collector.py (RSS ニュース収集)
- research/
  - __init__.py
  - factor_research.py (ファクター計算)
  - feature_exploration.py (forward returns, IC, summary)
- その他（strategy / execution / monitoring といったサブパッケージは __all__ に含まれていますが、このコードベース断片では主に上記が実装されています）

---

## 開発 / テストのヒント

- OpenAI 呼び出しは各モジュール内部の _call_openai_api を unittest.mock.patch で差し替えてテストしやすく設計されています（news_nlp と regime_detector で独立した実装）。
- DuckDB を使ったユニットテストは ":memory:" 接続を使用すると便利です：
  duckdb.connect(":memory:")
- ETL・保存処理は冪等（ON CONFLICT）なので、繰り返し実行しても既存データを上書きできます。
- jquants_client の HTTP 呼び出しは内部で RateLimiter とリトライを行います。実環境では API レートと課金に注意してください。
- ニュース収集モジュールは SSRF・XML Bomb 対策をしっかり組み込んでいます。fetch_rss のテスト時はネットワークアクセスをモックすることを推奨します。

---

必要があれば、README にサンプル .env.example、docker-compose 用の DB 初期化手順、CI 向けのテストコマンド例などを追加します。どの情報を追記しましょうか？