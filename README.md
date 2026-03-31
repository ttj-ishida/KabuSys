# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
データ取得（J-Quants）、ETL、品質チェック、ニュース NLP、リサーチ用ファクター計算、監査ログ（オーダートレース）、市場レジーム判定などを含むモジュール群を提供します。

---

## 主な機能（抜粋）

- データ取得・ETL
  - J-Quants API から株価日足、財務データ、JPX マーケットカレンダーを差分取得・保存（DuckDB）
  - ETL の差分フェッチ、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS からニュース収集、前処理、raw_news への冪等保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出（ai_scores へ保存）
- リサーチ / ファクター
  - Momentum / Value / Volatility 等のファクター計算
  - 将来リターン計算、IC（スピアマン）算出、ファクター統計
  - z-score 正規化ユーティリティ
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して日次で市場レジーム（bull/neutral/bear）を算出・保存
- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査テーブルの初期化・管理（DuckDB）
  - 発注フローのトレーサビリティを UUID で保証
- カレンダー管理
  - market_calendar の管理、営業日判定・前後営業日探索・SQ 判定など

---

## 必要環境・依存パッケージ（例）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ

依存関係は pyproject.toml / requirements.txt を参照してください（存在する場合）。

---

## セットアップ

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)

2. パッケージをインストール
   - pip install -e .   （プロジェクトのパッケージとして編集可能にインストール）
   - または必要な依存だけをインストールする:
     - pip install duckdb openai defusedxml

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨する主な環境変数（例）
- JQUANTS_REFRESH_TOKEN=...     （必須: J-Quants リフレッシュトークン）
- OPENAI_API_KEY=...            （OpenAI API キー。score_news / regime で使用）
- KABU_API_PASSWORD=...         （kabuステーション API のパスワード）
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=（例: data/kabusys.duckdb）
- SQLITE_PATH=（例: data/monitoring.db）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=DEBUG|INFO|...

env ファイルのパースはシェル風の `KEY=val` のみならず `export KEY=val`、シングル/ダブルクォート、コメントの取り扱いにも対応しています。

---

## 使い方（主要な実行例）

以下はライブラリを使った代表的な操作例です。DuckDB 接続オブジェクト（duckdb.connect）を渡す設計です。

- DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースのセンチメントスコアを算出して ai_scores に保存する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print("written:", n_written)
```

- 市場レジームを判定して market_regime に保存する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへ挿入やクエリが可能
```

- リサーチ用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

注意点
- 多くの関数は Look-ahead bias を避けるため内部で date.today() 等を参照せず、必ず target_date を明示することが推奨されています。
- OpenAI 呼び出し時は `OPENAI_API_KEY` を環境変数でセットするか、関数へ `api_key` を渡して下さい。
- API 呼び出し・外部接続はリトライやフェイルセーフ（失敗時はスコア0やスキップ）を備えていますが、API クォータやキーの準備は事前に行ってください。

---

## 設定（settings）

kabusys.config.Settings 経由でアプリ設定を参照できます（環境変数ベース）。

主なプロパティ（呼び出すと環境変数を検証して返す）
- settings.jquants_refresh_token  (JQUANTS_REFRESH_TOKEN) - 必須
- settings.kabu_api_password      (KABU_API_PASSWORD) - 必須
- settings.kabu_api_base_url      (KABU_API_BASE_URL) - 既定 http://localhost:18080/kabusapi
- settings.slack_bot_token        (SLACK_BOT_TOKEN) - 必須
- settings.slack_channel_id       (SLACK_CHANNEL_ID) - 必須
- settings.duckdb_path            (DUCKDB_PATH) - Path オブジェクト
- settings.sqlite_path            (SQLITE_PATH)
- settings.env                    (KABUSYS_ENV) - development / paper_trading / live
- settings.log_level              (LOG_LEVEL)

.env 読み込みはプロジェクトルート（.git または pyproject.toml が見つかる場所）から行われ、優先順位は OS 環境 > .env.local > .env です。

---

## ディレクトリ構成（主要ファイル）

以下は提供されたコードに基づくパッケージ構成（src/kabusys 以下、抜粋）:

- kabusys/
  - __init__.py
  - config.py                           - 環境変数・設定管理（.env 自動ロード等）
  - ai/
    - __init__.py
    - news_nlp.py                        - ニュース NLP（銘柄別センチメント算出）
    - regime_detector.py                 - 市場レジーム判定（MA + LLM センチメント）
  - data/
    - __init__.py
    - calendar_management.py             - マーケットカレンダー管理（営業日判定等）
    - pipeline.py                        - ETL パイプライン（run_daily_etl 等）
    - etl.py                             - ETL インターフェース再エクスポート
    - stats.py                           - 統計ユーティリティ（zscore_normalize）
    - quality.py                         - データ品質チェック
    - audit.py                           - 監査ログ（監査テーブル初期化）
    - jquants_client.py                  - J-Quants API クライアント（fetch/save）
    - news_collector.py                  - RSS ニュース収集・前処理
  - research/
    - __init__.py
    - factor_research.py                 - Momentum / Value / Volatility 等
    - feature_exploration.py             - 将来リターン・IC・統計サマリー

各モジュールは DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取る設計が多く、DB 層が分離されています。

---

## ベストプラクティス / 注意事項

- DuckDB ファイルは settings.duckdb_path で管理し、バックアップ・バージョン管理を検討してください。
- OpenAI の API 呼び出しにはコストが発生します。batch サイズやモデルを運用とコストの両面で適切に設定してください。
- ETL・API 呼び出し処理はリトライ・レート制御を含みますが、外部 API のレート制限や認証トークンの管理（J-Quants, OpenAI）は運用での監視が必要です。
- audit（監査ログ）は削除しない前提設計です。ディスク容量に注意してください。
- テスト実行時に自動 .env ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 貢献・拡張

- 新しい ETL データソースやニュースソースの追加、ファクターの追加、戦略実行モジュールの統合などを想定しています。
- Unit テスト時には外部 API 呼び出し箇所（OpenAI / J-Quants / HTTP）をモックする設計になっています。内部の private 呼び出し関数はテストで差し替え可能です（例: news_nlp._call_openai_api を patch）。

---

この README はコードベースの主要機能・使い方・構成の要約です。詳細は各モジュールの docstring や関数ドキュメントを参照してください。必要であればサンプルスクリプトや運用手順（cron/CI）向けの README 追加を作成します。