# KabuSys — 日本株自動売買基盤（README）

## プロジェクト概要
KabuSys は日本株のデータ取得・品質管理・ファクター計算・ニュースNLP・市場レジーム判定・監査ログなどを備えた自動売買プラットフォームのコアライブラリ群です。J-Quants API / DuckDB / OpenAI（LLM）を組み合わせ、ETL パイプライン、データ品質チェック、特徴量研究、AI を使ったニュースセンチメント評価、監査ログを提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部処理で date.today() を安易に参照しない）
- DuckDB を中心としたローカルデータ管理（冪等保存）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフ設計
- モジュール毎にテスト差し替えがしやすい実装（内部呼び出しの差し替えを想定）

---

## 機能一覧
- 環境変数・設定管理（kabusys.config）
  - .env/.env.local 自動読み込み（無効化可）
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants から株価日足、財務データ、マーケットカレンダー取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合チェック
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日取得、カレンダー更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、URL 正規化、SSRF対策、前処理、raw_news 保存
- AI ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント評価（ai_scores テーブル）
  - バッチ・トリム・リトライ・レスポンス検証
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の200日MA乖離とマクロニュースのLLMセンチメントを合成して日次レジーム判定
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- 監査・トレーサビリティ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査スキーマ初期化と DB 管理

---

## 必要環境
- Python 3.10+
- 推奨パッケージ（主要な依存）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI API、RSS ソース）

（実際の requirements.txt はプロジェクト側で用意してください）

---

## セットアップ手順

1. リポジトリを取得
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクト側に requirements がある場合はそれを使用）

4. パッケージのインストール（開発モード、src 配下の構成を想定）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに .env/.env.local を置くと自動読み込みされます（kabusys.config が .git または pyproject.toml を起点に探索）。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨の .env（例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- OPENAI_API_KEY=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

注意: Settings にある必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定だと ValueError を発生します（実行時に必要な場面で）。

---

## 使い方（主要な例）

以下は最低限の利用例です。実行前に環境変数（特に OPENAI_API_KEY や J-Quants トークン）を設定してください。

1) DuckDB 接続の作成（設定されたパスを利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する（データ取得 / 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP によるスコア付与
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY 環境変数がセットされていれば api_key 引数は不要
num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {num_written} ai_scores")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査スキーマの初期化（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して発注・約定ログを書き込めるようになります
```

6) 研究用ファクター計算の例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
volatility = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

---

## よく使う設定・環境変数
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（jquants_client が get_id_token で使用）
- KABU_API_PASSWORD: kabuステーション（発注）用パスワード（将来の execution モジュールで使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

---

## ディレクトリ構成（主要ファイル）
（リポジトリは src/kabusys 配下にパッケージ化されています）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS ニュース収集・保存
    - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー 等
    - feature_exploration.py — 将来リターン / IC / summary / rank 等

---

## 注意事項 / 運用上のヒント
- OpenAI や J-Quants の API 呼び出しは外部ネットワーク依存・コスト発生・レート制限があるため、環境変数とログ設定を確認してから実行してください。
- ETL の実行は通常バッチ（夜間）で実行し、calendar_update_job 等は先に実行して営業日情報を整えておくとよいです。
- DuckDB のスキーマやテーブルは ETL 処理側（あるいは別の schema 初期化処理）で準備する前提です。audit.init_audit_db は監査用 DB の初期化ユーティリティを提供します。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効にできます。
- LLM 呼び出しのテストは内部の _call_openai_api をモックして行う設計になっています。

---

必要であれば、インストール要件（requirements.txt）、CI 設定、実行スクリプト（例: cron / Airflow / GitHub Actions）やテーブルスキーマ（初期DDL）などの追加ドキュメントも作成します。どの部分を優先して詳述しますか？