# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリセットです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、監査ログ（注文→約定トレース）など、取引システムと研究環境で必要となる機能群を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル・品質チェック機能を備えた日次 ETL パイプライン

- ニュース収集・NLP
  - RSS からニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメントスコアリング（ai_scores への保存）
  - マクロニュースと ETF の移動平均乖離を組み合わせた市場レジーム判定（bull/neutral/bear）

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等の分析ユーティリティ
  - Zスコア正規化ユーティリティ

- データ品質チェック
  - 欠損、スパイク（急変）、重複、日付不整合の検出とレポート

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを提供し、シグナル→発注→約定までのトレースを保証
  - 監査 DB 初期化ユーティリティ（DuckDB）

- 設定管理
  - .env / .env.local / 環境変数の自動読込（プロジェクトルート検出）
  - 必須環境変数チェック、環境（development / paper_trading / live）・ログレベル設定

---

## 要求環境（推奨）

- Python 3.10+（型注釈に union 型などを使用）
- 依存ライブラリ（主なもの）
  - duckdb
  - openai（OpenAI Python SDK v1 系想定）
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード）
- ローカル DB: DuckDB ファイル（デフォルト: data/kabusys.duckdb）

（実際のセットアップで利用するパッケージバージョンはプロジェクトの requirements.txt / pyproject.toml を参照してください。）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する（例: venv, pyenv-virtualenv）。
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストールする（例: pip）。
   - pip install duckdb openai defusedxml

   ※ 実際にはプロジェクトの requirements.txt / pyproject.toml に合わせてインストールしてください。

3. 環境変数を設定する（.env をプロジェクトルートに置くか、CI/CD のシークレットで設定）。
   - パッケージは自動的にプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探して `.env` / `.env.local` を読み込みます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB のデータディレクトリを作成（デフォルト: data/）
   - mkdir -p data

---

## 必要な環境変数（例）

以下は最低限必要となる代表的な環境変数の例です。プロジェクト利用機能に応じて追加で設定してください。

必須:
- JQUANTS_REFRESH_TOKEN=xxxxx
- OPENAI_API_KEY=xxxxx  （ai モジュールを使う場合）
- SLACK_BOT_TOKEN=xxxxx
- SLACK_CHANNEL_ID=xxxxx
- KABU_API_PASSWORD=xxxxx  （kabu API と連携する場合）

任意（デフォルト値あり）:
- KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
- LOG_LEVEL=INFO | DEBUG | WARNING | ERROR | CRITICAL  （デフォルト: INFO）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

例 (.env):
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=jq-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## 使い方（簡易チュートリアル）

以下は Python REPL / スクリプト内での利用例です。適宜エラーハンドリングやログ設定を行ってください。

1) DuckDB 接続と日次 ETL の実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は環境変数 DUCKDB_PATH に基づく Path
conn = duckdb.connect(str(settings.duckdb_path))

# ETL 実行（target_date を指定可能、省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントのスコアリング（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# target_date に対して前日 15:00 JST ～ 当日 08:30 JST の記事を評価して ai_scores に書き込み
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照
print("scored:", n_written)
```

3) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ（audit）データベース初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

db_path = Path("data/audit.duckdb")
conn_audit = init_audit_db(db_path)
# これで signal_events / order_requests / executions テーブル等が作成されます
```

5) 研究系ユーティリティ（例: ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
# records: [{"date":..., "code":"XXXX", "mom_1m":..., ...}, ...]
```

---

## 運用上の注意点

- OpenAI / J-Quants への API 呼び出しはコストとレートリミットに注意してください。モジュール内でリトライやスロットリングの実装が行われていますが、運用ポリシーに従って使用して下さい。
- AI 呼び出し（score_news / score_regime）は外部 API に依存します。API エラー時はフェイルセーフ（スコアを 0.0 とする等）のロジックが組まれていますが、結果の取り扱いは運用側で検討してください（例: 再試行、モニタリング）。
- データの「ルックアヘッドバイアス」を防ぐため、本ライブラリの多くの関数は内部で date.today() を参照せず、明示的な target_date を受け取る設計です。バックテスト等での使用時は target_date を確実に指定してください。
- .env の自動読み込みはプロジェクトルートを探索して行われます。テストなどで環境の固定をしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読込を無効化できます。

---

## ディレクトリ構成（主要ファイルの役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み / Settings クラス（J-Quants / kabu / Slack / DB パス / 環境設定）
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄別ニュースの集約と OpenAI によるセンチメント評価、ai_scores への書き込み
    - regime_detector.py
      - ETF（1321）の MA200 乖離とマクロニュース LLM 評価を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レートリミット・リトライ）
    - pipeline.py
      - 日次 ETL のオーケストレーション（run_daily_etl 等）、ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 収集・前処理・raw_news への保存ロジック（SSRF 対策等）
    - calendar_management.py
      - market_calendar 管理、営業日計算、calendar_update_job
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログスキーマ定義・初期化（signal_events/order_requests/executions）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数など
  - ai、data、research などはそれぞれ再利用しやすいモジュールに分割されています。

---

## テスト・開発

- 自動環境変数読み込みを避けたいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用してください。
- OpenAI / J-Quants 呼び出し部は内部で分離されているため、ユニットテスト時は該当関数（例: _call_openai_api, _urlopen, jquants_client._request 等）をモックして API 呼び出しを差し替える設計になっています。

---

必要に応じて README に追記します（例: 実運用でのシステム構成図、CI/CD ハンドブック、具体的な .sql スキーマ、例外ハンドリング方針など）。どの情報を追加したいか教えてください。