# KabuSys

日本株向けのデータプラットフォーム＆自動売買基盤コンポーネント群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、研究用ファクター計算、監査ログ（発注／約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買に必要なデータ収集、品質チェック、特徴量生成、ニュースNLP、戦略用ユーティリティ、および監査ログ初期化を行うライブラリ群です。  
主な責務は「データの取得・整備」「NLP によるニューススコアリング」「市場レジーム判定」「研究用ファクター／特徴量計算」「監査テーブルの初期化／管理」です。バックテストや本番実行における Look-ahead bias を避ける設計や、API のリトライ・フェイルセーフを考慮した実装がなされています。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を基準）
  - 必須環境変数取得と検証
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化

- データ（kabusys.data）
  - J-Quants API クライアント（ページング・レート制御・トークン自動リフレッシュ・リトライ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - マーケットカレンダー管理（営業日判定・next/prev trading day 等）
  - ニュース収集（RSS -> raw_news、SSRF 対策・XML 安全パース・トラッキング除去）
  - 監査ログ（signal_events / order_requests / executions）のDDL・初期化ユーティリティ

- AI（kabusys.ai）
  - ニュース NLP: raw_news を銘柄別にまとめて OpenAI（gpt-4o-mini）で評価し ai_scores に保存（score_news）
  - 市場レジーム判定: ETF（1321）200日 MA 乖離とマクロニュースセンチメントを合成して market_regime に保存（score_regime）

- 研究（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
  - zscore_normalize（data.stats と共有）

---

## セットアップ手順

以下は推奨手順の一例です。実際の依存関係ファイル（requirements.txt / pyproject.toml）に従ってください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存関係をインストール（例）
   - 最低限必要なライブラリ:
     - duckdb
     - openai
     - defusedxml
   ```
   pip install duckdb openai defusedxml
   ```
   - パッケージとして開発インストール:
   ```
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルート（`.git` または `pyproject.toml` があるディレクトリ）に `.env`（または `.env.local`）を作成してください。
   - 必須（主要）環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用（必要に応じて）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に必要。関数引数で注入可能）
   - 省略可能／デフォルトあり:
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/…、デフォルト INFO）
     - DUCKDB_PATH（データ DB ファイル, デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（主なユースケース）

以下は代表的な呼び出し例です。各関数は duckdb の接続オブジェクト（duckdb.connect(...) の戻り値）を受け取ります。

- 設定取得
```python
from kabusys.config import settings

print(settings.duckdb_path)  # Path オブジェクト
print(settings.env)          # 'development' / 'paper_trading' / 'live'
```

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# conn は duckdb connection
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI API キーを環境変数に設定するか、api_key を渡す）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))  # OpenAI API key は env または api_key 引数で
```

- 監査DB（監査ログ）初期化
```python
from kabusys.data.audit import init_audit_db, init_audit_schema
from kabusys.config import settings

# 既存のデータベースに表を作る場合:
conn = init_audit_db(settings.duckdb_path)  # transactional=True は関数内で指定可能
# または既存接続に直接スキーマを追加:
# init_audit_schema(conn, transactional=True)
```

- 研究用関数（例：モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# records は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

注意:
- OpenAI を利用する関数は api_key 引数でキーを注入可能です（テスト容易性のため）。環境変数 OPENAI_API_KEY が未設定の場合は ValueError を投げます。
- ETL / API 呼び出しはリトライやレート制御を備えていますが、ネットワークや API 制限を考慮して運用してください。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)：J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須)：kabu API のパスワード
- KABU_API_BASE_URL (任意)：kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY (必須 for AI functions)：OpenAI API キー（score_news, score_regime）
- SLACK_BOT_TOKEN (必須 if Slack used)：Slack Bot Token
- SLACK_CHANNEL_ID (必須 if Slack used)：Slack Channel ID
- DUCKDB_PATH (任意)：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意)：SQLite (monitoring) path（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意)：development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意)：ログレベル（DEBUG/INFO/…）

.env 取り扱い:
- 自動読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイルと説明）

（ルート: src/kabusys 以下）

- __init__.py
  - パッケージ公開設定（__version__ 等）

- config.py
  - 環境変数の自動読み込み・取得ユーティリティ（Settings クラス）

- ai/
  - __init__.py
  - news_nlp.py — ニュースを銘柄別に集約し OpenAI でスコアリング（score_news）
  - regime_detector.py — ETF(1321) の MA 乖離とマクロニュースを合成して市場レジーム判定（score_regime）

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch_*/save_* 実装）
  - pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - news_collector.py — RSS 収集・前処理・保存ロジック
  - calendar_management.py — 市場カレンダー管理（is_trading_day / next/prev / calendar_update_job）
  - audit.py — 監査ログ用 DDL・初期化ユーティリティ（signal_events / order_requests / executions）
  - stats.py — zscore_normalize 等の統計ユーティリティ

- research/
  - __init__.py
  - factor_research.py — モメンタム／ボラティリティ／バリュー計算
  - feature_exploration.py — 将来リターン計算・IC・統計サマリー

その他:
- AI モジュールは OpenAI の JSON Mode を想定（gpt-4o-mini 等）で出力の検証を行います。
- J-Quants クライアントは内部で RateLimiter（120 req/min）・トークン自動リフレッシュを実装しています。

---

## 運用上の注意・ベストプラクティス

- Look-ahead bias を避けるため、関数群は基本的に内部で date.today() を参照しないか、引数で日付を受け取る設計になっています。バックテストでは常に明示的に target_date を渡してください。
- OpenAI 呼び出しには料金が発生します。score_news / score_regime 実行はバッチ化・レート制御を行ってください。
- .env にシークレットを保存する際はファイルのアクセス制御に注意してください（.gitignore に追加する等）。
- ETL / スキーマ初期化は適切なトランザクション管理の下で実行してください。init_audit_schema は transactional 引数を提供していますが、DuckDB のトランザクション挙動に注意してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 .env 読み込みを無効化し、テスト専用環境を構築してください。

---

## さらなる情報・拡張

- 各モジュールの docstring に設計意図や安全対策（SSRF防止、JSONパース回復、リトライ戦略など）が記載されています。実際に運用する際はそちらも参照してください。
- 実運用では Slack 通知、モニタリング、ジョブスケジューラ（cron / Airflow など）と連携して ETL / scoring を定期実行してください。

---

この README はコードベースの概要をまとめたものです。詳細な API や設定は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば README にサンプル .env.example や requirements.txt（依存）を追加できます。