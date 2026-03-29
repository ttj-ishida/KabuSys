# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLPによるセンチメント評価、マーケットレジーム判定、監査ログ（トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム開発に必要な下記機能群をモジュール化して提供します。

- J-Quants API からの株価・財務・カレンダー取得（レートリミット／リトライ対応）
- DuckDB を使った ETL パイプライン（差分取得・冪等保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ベースのニュース収集と前処理（SSRF 対策, トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）およびマクロセンチメントを用いた市場レジーム判定
- 監査ログ（signal → order_request → execution）のスキーマ定義と初期化ユーティリティ
- 研究用ユーティリティ（ファクター計算・IC 計算・Z スコア正規化等）

設計上、バックテストでのルックアヘッドバイアスを避けるように日付の扱いに注意が払われています（date.today()/datetime.today() を内部処理で直接参照しない等）。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API との通信、取得データの DuckDB への保存
  - pipeline / etl: 日次 ETL（市場カレンダー／株価／財務）と ETL 結果レポート
  - news_collector: RSS 取得と raw_news 保存（SSRF対策、記事ID冪等化）
  - quality: データ品質チェック（missing / duplicates / spike / date consistency）
  - calendar_management: 営業日判定、next/prev/trading day ヘルパー、カレンダー更新ジョブ
  - audit: 監査ログスキーマの作成・初期化ユーティリティ
  - stats: zscore_normalize など統計ユーティリティ
- ai/
  - news_nlp: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に書き込む
  - regime_detector: ETF（1321）MA200乖離とマクロニュースの LLM センチメントを合成して market_regime を生成
- research/: ファクターモジュール（momentum / volatility / value）と特徴量探索ユーティリティ
- config: 環境変数管理（.env 自動読み込み、必須値チェック、settings オブジェクト）

---

## 要件

- Python 3.10+
- 主要依存ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、各 RSS ソース、OpenAI API（使用する機能に応じて）

（プロジェクトの配布側で requirements.txt / pyproject.toml が提供されることを想定しています。開発環境では仮想環境を推奨します。）

---

## 環境変数 / .env

パッケージはプロジェクトルート（.git または pyproject.toml のある場所）を探索して自動で `.env` / `.env.local` を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu API（kabuステーション）接続用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）

オプション / デフォルト:

- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (監視等) のパス（デフォルト: data/monitoring.db）

サンプル `.env`（例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（例）

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストール
   - もし pyproject.toml / requirements.txt がある場合はそれを使ってください。無ければ最低限:
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、必要な環境変数をエクスポートしてください（上のサンプル参照）。

4. DuckDB ファイルのディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下は Python REPL やスクリプト内での使用例です。すべての関数はモジュール化されており、DuckDB 接続を受け取ります。

- 共通: settings を使った DB パス取得
```python
from kabusys.config import settings
import duckdb

# settings.duckdb_path は pathlib.Path を返す
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を算出して ai_scores テーブルへ書き込む
```python
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書込銘柄数:", n_written)
```

- 市場レジーム判定（ma200 + マクロニュース）を実行
```python
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```
注意: OpenAI API キーは環境変数 `OPENAI_API_KEY` で提供するか、各関数の api_key 引数に渡してください。

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # :memory: も可能
```

- JPX カレンダーを差分取得・保存する夜間ジョブ（直接呼び出し）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
saved = calendar_update_job(conn)
print("saved:", saved)
```

---

## 備考 / 注意点

- OpenAI 呼び出しや外部 API 呼び出しの失敗は、設計上フェイルセーフ（例: スコア 0 を採用、処理を継続）になる箇所があります。ログを確認して運用判断してください。
- ETL / API 呼び出しではレート制限やリトライロジックを備えていますが、J-Quants や OpenAI のレート上限は遵守してください。
- DuckDB への executemany に空リストを渡すとエラーになるバージョン差分に配慮した実装があります。環境の DuckDB バージョンに注意してください。
- プロダクション（is_live）運用では特に KABUSYS_ENV の設定、ログレベル、シークレット管理に注意してください。

---

## ディレクトリ構成（抜粋）

（実装済みモジュールの主なファイル構成）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - monitoring/  (README の要件に合わせて monitoring 関連が __all__ に含まれる想定)

各モジュールはコメントや docstring で設計方針・処理フローが明示されています。詳細は該当ファイルをご参照ください。

---

## 連絡・貢献

バグ報告、機能要望、改善提案はリポジトリの Issue にお寄せください。プルリクエストは歓迎します。変更を行う際は既存の設計方針（冪等性、ルックアヘッドバイアス防止、外部依存の分離）を尊重してください。

--- 

以上。必要であれば、README に含めるサンプル .env.example、Docker / CI の設定例、より詳細な API 使用例（各関数の引数説明付き）を追加で作成します。どの部分を補足しますか？