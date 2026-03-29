# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリセットです。  
ETL（J-Quants からのデータ取得）・ニュース収集・LLM を用いたニュースセンチメント解析・市場レジーム判定・ファクター計算・データ品質チェック・監査ログ管理などの機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴（Overview / Features）

- データ収集・ETL
  - J-Quants API から株価（日足）・財務・上場情報・市場カレンダーを差分取得し、DuckDB に冪等保存
  - 差分更新・バックフィル・ページネーション・レートリミット対応・トークン自動リフレッシュ
- ニュース収集
  - RSS フィードの安全な収集（SSRF対策、gzip サイズ制限、URL 正規化、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（LLM を利用したセンチメント）
  - OpenAI（gpt-4o-mini）を利用した銘柄別センチメント（ai_scores へ保存）
  - バッチ処理・リトライ・レスポンスバリデーション・スコアクリップ
- 市場レジーム判定
  - ETF 1321（Nikkei225連動）の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して 'bull'/'neutral'/'bear' を決定
  - LLM リクエストに対するリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出
  - QualityIssue オブジェクトで問題を収集（Fail-Fast ではなく全件収集）
- 監査ログ（トレーサビリティ）
  - シグナルから発注・約定に至る監査テーブル群（signal_events, order_requests, executions）
  - init_audit_db を使った DuckDB 初期化ユーティリティ

---

## 必要条件（推奨）

- Python 3.10 以上（ソース内で `X | None` 等の構文を使用）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（LLM 呼び出しを行う場合）
- defusedxml（RSS パースの安全化）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

例（最低限のパッケージ）:
- duckdb
- openai
- defusedxml

（実際のプロジェクトでは requirements.txt を用意してください）

---

## 環境変数 / .env（必須・推奨）

主要な環境変数（ライブラリが参照するもの）:

- JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD … kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL … kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN … Slack 通知用トークン（必須: Slack 通知を使う場合）
- SLACK_CHANNEL_ID … Slack チャンネル ID（必須: Slack 通知を使う場合）
- OPENAI_API_KEY … OpenAI API キー（ai モジュールを使う場合、関数引数で上書き可）
- DUCKDB_PATH … デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH … モニタリング用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV … "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL … "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）

パッケージはプロジェクトルートにある `.env` / `.env.local` を自動で読み込みます（環境変数で無効化可能）。
自動読み込みを無効にする:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を参照してください）

3. .env をプロジェクトルートに作成して必要な環境変数を設定

4. DuckDB データベースのディレクトリを作成（必要なら）
   - mkdir -p data

5. （任意）自動環境変数読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（抜粋・サンプルコード）

以下は一部の主要 API の使用例です。実行前に環境変数（OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN など）を設定してください。

- ETL（日次パイプライン）を実行する:
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコアリングする:
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須（環境変数 or api_key 引数）
print(f"wrote {n_written} scores")
```

- 市場レジーム判定を行う:
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーが必要
```

- ファクター計算（研究用途）:
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, target_date=date(2026, 3, 20))
v = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- 監査データベース初期化:
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成される
```

- 設定の参照:
```
from kabusys.config import settings
print(settings.duckdb_path)       # Path オブジェクト
print(settings.env, settings.is_live)
```

---

## 注意点 / 設計上のポイント

- Look-ahead バイアス防止:
  - モジュールの多くは date / target_date を明示的に受け取り、内部で datetime.today() を参照しない設計。バックテストでの誤用を防ぐためです。
- フェイルセーフ:
  - LLM や外部 API 呼び出しの失敗時には例外を投げずにフォールバック（スコア 0.0）する箇所があり、パイプライン全体の頑健性を重視しています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE / 挿入時の PK 検査等で冪等に行われます。
- セキュリティ:
  - RSS 取得での SSRF 対策、defusedxml の利用、RSS レスポンスサイズ制限などを実装しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - pipeline.py
  - etl.py
  - jquants_client.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - etl.py (ETLResult re-export)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/__init__.py  (各研究用関数を再エクスポート)
- ai/__init__.py

（上記は本リポジトリ内で主要に使うモジュール群です。詳細は各モジュールの docstring を参照してください。）

---

## 開発・テスト

- 環境読み込みは自動で .env / .env.local をプロジェクトルートから行います（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください）。
- OpenAI 呼び出し等はユニットテストでモック可能な設計になっています（_call_openai_api の差し替え等）。
- DuckDB はインメモリ ":memory:" を利用してテストを容易にできます。

---

## 参考

- 主要モジュールの詳細は各ファイル先頭の docstring に処理フロー・設計方針が記載されています。各機能の利用前に docstring を確認してください。

---

README はここまでです。追加で「運用手順（cron / バッチ設定）」「具体的なテーブルスキーマ」「requirements.txt の推奨内容」などが必要であれば、その要望に合わせて追記します。