# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI を用いたセンチメント算出）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー／約定トレース）などの機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API からの株価日足、財務データ、カレンダー取得（ページネーション・レート制御・トークン自動リフレッシュ）
  - DuckDB への冪等的保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合などの検出（QualityIssue を返す）
- ニュース収集
  - RSS 取得（SSRF 対策・Gzip 上限・URL 正規化）
  - raw_news / news_symbols への冪等保存（記事ID は正規化 URL のハッシュ）
- ニュース NLP
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのセンチメントスコア算出（score_news）
  - レスポンス検証・バッチ処理・リトライ実装
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成（score_regime）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions 等、発注〜約定のトレーサビリティを担保するスキーマ／初期化関数
- 設定管理
  - .env/.env.local または環境変数からの設定自動読み込み（プロジェクトルート検出）

---

## 動作要件

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS など）

実際のプロジェクトでは poetry / pipenv / requirements.txt によって固定することを推奨します。

---

## 環境変数（主要）

必須（用途）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等で利用）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用。score_news / score_regime に渡さない場合はこれを参照）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 任意値を設定すると自動で .env を読み込む処理を無効化

README 内やコード内で示されている .env.example を参考に .env を作成してください。

自動読み込み:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を検出すると、ルート直下の `.env` を読み、さらに `.env.local` を上書きで読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb

---

## インストール（開発・ローカル利用例）

1. リポジトリをクローン（またはソースを用意）
2. 仮想環境を作成して有効化（例: python -m venv .venv; source .venv/bin/activate）
3. 依存パッケージをインストール（pip の例）:
   - pip install duckdb openai defusedxml

（実運用では requirements.txt / pyproject.toml を整備してください）

開発インストール（パッケージ化されている場合）:
- pip install -e .

---

## セットアップ手順（最小セット）

1. 必要な環境変数を .env に設定またはシェルに export
2. DuckDB データベースファイルの親ディレクトリを作成（例: mkdir -p data）
3. 監査ログ用 DB 初期化（必要な場合）:

Python REPL 例:
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ファイルを作成してスキーマを初期化

---

## 使い方（簡単なコード例）

- 日次 ETL を実行する（DuckDB 接続を渡す）:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメント（score_news）を実行する:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# APIキーを引数で渡すか、環境変数 OPENAI_API_KEY をセットしてください
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n} symbols")

- 市場レジーム判定（score_regime）:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査 DB 初期化（ファイルパス指定）:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # テーブルとインデックスを作成

- ファクター計算例:

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026,3,20))
v = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))

注意:
- score_news / score_regime は OpenAI API 呼び出しを行います。テストではモックするか api_key を設定して実行してください。
- 各関数はルックアヘッドバイアスを避ける設計です（date 引数を受け取り内部で date.today() を参照しない）。

---

## API の設計上の注意点・運用ヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に干渉する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化してください。
- J-Quants クライアントには内部で簡易的な RateLimiter・リトライ・トークンキャッシュが実装されています。大量取得時は設定を調整し、API レートに注意してください。
- OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証を行いますが、API 料金やレート制限に配慮してバッチサイズ（news_nlp の _BATCH_SIZE 等）を設定してください。
- DuckDB への批次保存は executemany を使っています。DuckDB バージョンの互換性（空リストの executemany 不可など）に注意してください。

---

## ディレクトリ構成

以下は主要ファイルとモジュールの一覧（プロジェクトルート: src/kabusys）です。実際のリポジトリルートに pyproject.toml 等が存在すると自動で .env を読み込みます。

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         # ニュースのセンチメント算出（score_news）
  - regime_detector.py  # 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py
  - etl.py               # ETL の公開インターフェース（ETLResult 再エクスポート）
  - pipeline.py          # 日次 ETL 実装（run_daily_etl 等）
  - stats.py             # zscore_normalize 等
  - quality.py           # 品質チェック（check_missing_data 等）
  - audit.py             # 監査ログスキーマと初期化
  - jquants_client.py    # J-Quants API クライアント（fetch_*, save_* 等）
  - news_collector.py    # RSS 取得・前処理・記事保存
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*（ファクター、IC、rank 等）
- その他（strategy, execution, monitoring 等のトップレベル公開は __init__ にて想定）

---

## 開発・テストに関して

- OpenAI / J-Quants 呼び出し部分は外部 API に依存するためテスト時はモックして差し替えることを想定しています（コード内に patch しやすい _call_openai_api 等の抽象化あり）。
- DuckDB を使うことでテストはインメモリ（":memory:"）の DB を用いて高速に行えます。
- ニュース収集の RSS 関連は SSRF 対策やサイズ上限チェックを実装しています。外部通信はネットワークに依存するためユニットテストではモック推奨です。

---

この README はコードベースの主要な機能・使い方の概要をまとめたものです。詳細な設計や追加のユーティリティは各モジュールの docstring を参照してください。質問や README に追加してほしい内容があれば教えてください。