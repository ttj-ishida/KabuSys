# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。J-Quants や RSS、OpenAI（LLM）等の外部データを取り込み、ETL・品質チェック・特徴量計算・ニュースセンチメント・市場レジーム判定・監査ログなどの機能を提供します。

## 主な特徴
- データ収集・ETL
  - J-Quants API から株価（日足）・財務データ・マーケットカレンダーを差分取得・保存
  - DuckDB を用いた冪等保存（ON CONFLICT / DO UPDATE）
- データ品質管理
  - 欠損、重複、スパイク、日付整合性チェック（quality モジュール）
- ニュース処理と NLP
  - RSS 収集（news_collector）と前処理（URL除去等）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（news_nlp）
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離 + マクロニュースセンチメントを合成して日次レジーム判定（regime_detector）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン、IC 計算、Z スコア正規化
- 監査ログ（トレーサビリティ）
  - signal/events → order_requests → executions を追跡する監査テーブル・初期化ユーティリティ

---

## 必要条件
- Python 3.10+
- 必要な外部パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI など）

（プロジェクトに requirements.txt がある場合はそちらを参照してください。上記はコードから読み取れる依存の最小セットです。）

---

## 環境変数（主なもの）
以下の環境変数は .env ファイルまたは実行環境に設定してください。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector の呼び出しに必要）

自動的に .env / .env.local をルートから読み込む仕組みが入っています（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数を設定（.env をプロジェクトルートに作成）
5. DuckDB の初期テーブル定義は用途により必要（例: 監査ログ）
   - 監査ログ初期化（下記参照）

---

## 使い方（代表的な操作例）

以下は Python スクリプト / REPL での使用例です。DuckDB の接続には `duckdb.connect()` を使用します。

- DuckDB 接続準備（デフォルト DUCKDB_PATH を使用する例）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が使われます
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースセンチメントスコアの付与（news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API key を環境変数で設定しておくか、api_key 引数で渡す
n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")
```

- 市場レジーム判定（regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB を新規初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

- 研究用関数例（ファクター計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの dict のリスト
```

---

## 開発・テストに関するメモ
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml の存在を探索）を基準に行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部はリトライやフェイルセーフ（失敗時スコア 0.0）を備えています。テストでは該当モジュールの内部呼び出し関数を patch してモックすることが想定されています（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、実装側で空チェックが行われています。テスト時も同様の注意を払ってください。

---

## ディレクトリ構成（主要ファイル）
プロジェクトの主要モジュールと役割を示します（src/kabusys 以下）。

- kabusys/
  - __init__.py (パッケージ初期化)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメント付与、score_news)
    - regime_detector.py (市場レジーム判定、score_regime)
  - data/
    - __init__.py
    - calendar_management.py (マーケットカレンダー、営業日判定)
    - etl.py (ETL 結果型再エクスポート)
    - pipeline.py (日次 ETL パイプライン、run_daily_etl 等)
    - stats.py (zscore正規化 等)
    - quality.py (データ品質チェック)
    - audit.py (監査ログスキーマ初期化)
    - jquants_client.py (J-Quants API クライアント／保存処理)
    - news_collector.py (RSS 収集／前処理)
  - research/
    - __init__.py
    - factor_research.py (モメンタム / ボラティリティ / バリュー計算)
    - feature_exploration.py (forward returns, IC, rank, summary)
  - research/*.py など（リサーチ支援モジュール）

---

## 追加の注意点
- セキュリティ
  - news_collector は SSRF 対策や RSS のサイズチェック、XML の防御（defusedxml）を行っていますが、運用では追加のネットワーク制限や監査を推奨します。
- Look-ahead bias 対策
  - 各モジュール（news_nlp, regime_detector, jquants_client 等）は日付の扱いに注意を払い、内部で datetime.today() を無闇に参照しない設計になっています。バックテスト用途では、対象日を明示的に渡してください。
- エラーハンドリング
  - 外部 API の一部（OpenAI / J-Quants）呼び出しはリトライやフォールバックを行いますが、API レート制限やコストに注意してください。

---

必要であれば、README に入れる .env.example や requirements.txt、簡易の起動スクリプト（例: run_etl.py）のテンプレートも作成できます。どの情報を追加したいか教えてください。