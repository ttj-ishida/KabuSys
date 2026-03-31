# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
ETL（J-Quants -> DuckDB）、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、ファクター算出、データ品質チェック、監査ログ（発注→約定の追跡）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム／研究プラットフォーム用の共通モジュール群です。主に以下を目的としています。

- J-Quants API からの株価・財務・カレンダーの差分ETLと DuckDB への保存（冪等）
- RSS ベースのニュース収集と OpenAI を使った銘柄別センチメント算出
- ETF・マクロニュースを用いた市場レジーム判定
- ファクター計算・特徴量探索・統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定の監査ログ（DuckDB ベースの監査DB 初期化機能）
- 実行時設定の環境変数読み込みユーティリティ

設計上、ルックアヘッドバイアスを避けるために内部で `date.today()` 等を不用意に参照しない実装方針が取られています。

---

## 主な機能一覧

- ETL: 差分取得 + 冪等保存（kabusys.data.pipeline）
- データ品質チェック: 欠損・スパイク・重複・日付不整合（kabusys.data.quality）
- ニュースNLP: 銘柄ごとのセンチメント算出（kabusys.ai.news_nlp）
- 市場レジーム判定: ETF MA200 とマクロセンチメントを合成（kabusys.ai.regime_detector）
- ファクター計算 / 研究用ユーティリティ（kabusys.research）
- J-Quants クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- ニュース収集（RSS、SSRF対策、正規化）
- 監査ログテーブル初期化・監査DB生成（kabusys.data.audit）
- 設定管理: .env 自動読み込み（プロジェクトルート基準）と Settings API（kabusys.config）

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（代表）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - （標準ライブラリの urllib を多用しているため requests は必須ではありません）

実際のプロジェクトでは requirements.txt を用意してください（本リポジトリに直接含まれない場合は上記をインストール）。

---

## セットアップ手順（開発環境）

1. リポジトリをクローン（例）
   - git clone <リポジトリURL>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （あるいはプロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）の `.env` / `.env.local` が自動で読み込まれます（デフォルト）。
   - テスト／手動管理したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。

5. 必須設定の例（.env）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション (必要に応じて)
   KABU_API_PASSWORD=...

   # Slack (通知等)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（相対パスまたは絶対パス）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # システム
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 主要な環境変数（Settings API で参照されるもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注等で使用）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

config へのアクセス例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## 使い方（代表的な例）

以下では DuckDB 接続に対して各機能を実行する例を示します。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を開く
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（指定日）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（指定日）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DB（発注/約定トレース用）の初期化（独立したファイルとして）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を用いて order_requests / executions テーブルにアクセス可能
```

注意点:
- AI モジュールは OpenAI の JSON Mode を利用しています。テストでは内部の _call_openai_api をモックすることが想定されています（例: unittest.mock.patch）。
- 各種 API 呼び出しはリトライ・バックオフやフェイルセーフが組み込まれており、失敗時はゼロスコア等で継続する実装が多くあります。ログで詳細を監視してください。

---

## 開発・テストのヒント

- 自動環境変数の読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト実行時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部はモジュール内でラップされており、ユニットテストではモックしやすいよう設計されています（kabusys.ai.news_nlp._call_openai_api などをパッチ）。
- DuckDB は手軽にインメモリで起動できます（db_path=":memory:" を使用）。

---

## ディレクトリ構成（主要ファイル）

（省略可能なファイルは除外、代表的な構成）
```
src/kabusys/
├── __init__.py
├── config.py
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py
│   └── regime_detector.py
├── data/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── etl.py
│   ├── jquants_client.py
│   ├── news_collector.py
│   ├── calendar_management.py
│   ├── quality.py
│   ├── stats.py
│   └── audit.py
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
└── research/...（ファクター・探索ユーティリティ）
```

---

## 付録: 既知の想定値・設定

- Python バージョン: 3.10 以上（型ヒントの | 演算子などを使用）
- KABUSYS_ENV の有効値: development / paper_trading / live
- LOG_LEVEL の有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

もし README に特定の実行スクリプト（CLI）や CI / 開発用の依存関係一覧、あるいは .env.example の具体的なテンプレートを追加したければ、どの形式で記載するか教えてください。さらに詳細な使い方（ETL のスケジュール例、Slack 通知の利用法、kabu ステーション連携の手順等）も作成できます。