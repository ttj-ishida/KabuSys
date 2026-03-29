# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ／発注トレーサビリティなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 主要な概要

KabuSys は以下の主要機能を提供します。

- J-Quants API からの差分取得（株価日足 / 財務 / 上場情報 / カレンダー）と DuckDB への冪等保存
- 日次 ETL パイプライン（差分取得 → 保存 → 品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）とニュース前処理（SSRF・サイズ制限・トラッキング除去）
- OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score）と市場レジーム判定
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と統計ユーティリティ
- 監査ログ（signal / order_request / executions）用スキーマ初期化ユーティリティ
- 環境変数ベースの設定読み込み（.env 自動読み込みをサポート）

設計方針として「ルックアヘッドバイアス防止」や「冪等性」「フェイルセーフ（API障害時はスキップ/デフォルト値）」を重視しています。

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env の自動ロード（プロジェクトルート検出）および必須設定チェック
  - 環境変数:
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - KABU_API_BASE_URL (任意, デフォルト http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN (必須)
    - SLACK_CHANNEL_ID (必須)
    - DUCKDB_PATH (任意, デフォルト data/kabusys.duckdb)
    - SQLITE_PATH (任意, デフォルト data/monitoring.db)
    - KABUSYS_ENV (development|paper_trading|live, デフォルト development)
    - LOG_LEVEL (DEBUG|INFO|...)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化可能

- kabusys.data
  - jquants_client: J-Quants API 呼び出し、認証トークン取得、DuckDB への保存関数
  - pipeline / etl: 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - news_collector: RSS 収集、安全対策（SSRF／サイズ制限）、raw_news保存補助
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ用テーブル作成 / init_audit_db
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で解析して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 必要条件 / 推奨環境

- Python 3.10+
- 必須ライブラリ（代表）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）
- J-Quants のリフレッシュトークン、OpenAI API Key 等の外部資格情報

（プロジェクトに requirements.txt があればそれを利用してください。ここではコードから依存を推定しています）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに setup.py / pyproject.toml があれば、pip install -e . を使用）

3. 環境変数設定
   - プロジェクトルートに .env を配置するか OS 環境変数を設定します。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB 用データディレクトリを作成（必要であれば）
   - mkdir -p data

---

## 使い方（代表的な例）

以下はライブラリを直接呼び出す最小例です。実運用ではロギング設定やエラーハンドリングを追加してください。

- 日次 ETL 実行（株価・財務・カレンダーの差分取得と品質チェック）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント解析（指定日分を ai_scores に書き込む）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されているか、api_key を明示的に渡す
written_count = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", written_count)
```

- 市場レジーム判定（MA200 とマクロニュースを合成）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成される
```

- 研究用ファクター計算（例: モメンタム）

```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026,3,20))
# factors は各銘柄ごとの dict のリスト
```

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API パスワード（自動発注等で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID

必須ではないが重要:
- OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

環境変数はプロジェクトルートの .env / .env.local より読み込まれます（OS 環境変数が優先）。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索します。

---

## テスト時の注意・モックポイント

- OpenAI 呼び出しは内部で client.chat.completions.create を呼ぶため、ユニットテストでは kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api を patch してモックすることが想定されています。
- news_collector._urlopen はネットワーク呼び出しのためテスト時にモック可能です。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効にできます（テストで環境を制御する際に便利）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル一覧（このリポジトリのコードに基づく）:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
- src/kabusys/research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（README に載せていない補助モジュールやテストコードはリポジトリ内を参照してください）

---

## 運用上の留意点

- OpenAI / J-Quants 等の外部 API に対してはレート制限、タイムアウト、リトライが実装されていますが、運用環境ではキー管理・コスト管理を注意してください。
- run_daily_etl 等は ETL の失敗を完全停止させず、各ステップでエラーを収集して戻します。呼び出し側で result.has_errors / result.has_quality_errors などをチェックして運用アラートを出すことを推奨します。
- DuckDB の executemany に空リストを渡せないなどの制約（バージョン差）がコードに考慮されていますが、使用する DuckDB バージョンでの挙動確認を推奨します。
- ニュース収集では SSRF 対策やレスポンスサイズ制限などを実装していますが、外部フィードの扱いは注意して運用してください。

---

もし README に追加してほしい使用例（CI/CD、Docker、cron ジョブでの実行例、監視 / Slack 通知の例など）があれば、用途を教えてください。必要に応じてそのセクションを追記します。