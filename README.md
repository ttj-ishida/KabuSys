# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログなどを備え、バックテスト／運用のデータ基盤と研究ワークフローを支援します。

主なポイント
- DuckDB をデータレイヤに使った ETL・品質チェック機能
- J-Quants API 経由の株価・財務・カレンダー取得（レート制御・リトライ完備）
- RSS ベースのニュース収集と OpenAI を使った銘柄センチメント / マクロ判定
- ファクター計算（モメンタム／バリュー／ボラティリティ）と特徴量探索ユーティリティ
- 発注〜約定までトレース可能な監査ログスキーマ（冪等性・インデックスあり）

---

## 機能一覧

- data/jquants_client
  - J-Quants API クライアント（認証、ページネーション、リトライ、RateLimit）
  - save_* 関数で DuckDB へ冪等保存（raw_prices, raw_financials, market_calendar 等）
- data/pipeline
  - 日次ETL（run_daily_etl）: カレンダー / 株価 / 財務 の差分更新 + 品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- data/news_collector
  - RSS フィード取得、前処理、raw_news への冪等保存（SSRF対策・サイズ制限あり）
- data/quality
  - 欠損、スパイク、重複、日付不整合のチェック（QualityIssue 型で報告）
- data/calendar_management
  - 営業日判定、前後営業日の取得、market_calendar の更新ジョブ
- data/audit
  - signal_events / order_requests / executions といった監査テーブルの初期化・接続ユーティリティ
- ai/news_nlp
  - 銘柄ごとのニュースを LLM（gpt-4o-mini）でスコア化し ai_scores に書込
- ai/regime_detector
  - ETF(1321) の 200日MA乖離 と マクロニュースセンチメントを合成して市場レジーム判定（market_regime へ保存）
- research
  - ファクター計算（momentum/value/volatility）・forward returns・IC・統計サマリ等
- config
  - .env / 環境変数読み込み、Settings オブジェクトで設定値を一元管理（自動読み込み可能）

---

## セットアップ

前提
- Python 3.10 以上（typing の | や型指定を使用）
- DuckDB と OpenAI SDK 等の依存ライブラリ

推奨手順（UNIX 系の例）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - 代表的な依存:
     - duckdb
     - openai
     - defusedxml
     - （必要に応じて）requests 等
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意している想定です。開発用に pip install -e . することも可能です（該当のパッケージ設定がある場合）。

3. 環境変数（.env）を準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（設定ファイル: kabusys.config）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（最低限必要）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース/レジーム機能利用時に必要）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注系利用時）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知（利用する場合）
- DUCKDB_PATH: （オプション）DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例 .env
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下はライブラリの代表的な利用方法（Python スクリプトや REPL で実行）。

共通: DuckDB 接続準備
```python
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)  # または ":memory:"
conn = duckdb.connect(db_path)
```

1) 日次 ETL を実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄ごとの ai_score）を作成
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written", n_written)
```

3) 市場レジーム判定（regime score を market_regime テーブルへ保存）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions が作成されます
```

5) 研究用ユーティリティ（ファクター計算）
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意点
- AI 系（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。API 呼び出し失敗時はフェイルセーフでスコアをゼロ扱いする設計の箇所もありますが、キーは必須です。
- ETL / カレンダー処理は日時（target_date）の扱いでルックアヘッドバイアスを避ける設計になっています（内部で date.today() を安易に使用しません）。

---

## 期待されるデータベーススキーマ（主なテーブル）

- raw_prices / raw_financials / market_calendar: J-Quants からの生データ格納先
- raw_news / news_symbols / ai_scores: ニュースと NLP スコア
- market_regime: regime_detector が書き込む市場レジーム（日次）
- signal_events / order_requests / executions: 監査ログ（発注フローのトレーサビリティ）

（各モジュールの save_* / init_* 関数でテーブル作成・更新のための DDL ロジックを持っています）

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ（抜粋）:

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
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - stats.py
    - pipeline.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/, strategy/, execution/ など（パッケージ公開名は __all__ に含まれていますが、この README の抜粋コードに全ては含まれていません）

プロジェクトルートには .env/.env.local/.env.example を置いて設定する想定です。

---

## 開発・運用上の注意

- 環境変数の自動読み込みは kabusys.config モジュールが .git または pyproject.toml を探索して行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API はレート制限（120 req/min）があるため、jquants_client は固定間隔の RateLimiter とリトライを実装しています。ETL やマス取得で注意してください。
- LLM 呼び出しは OpenAI の Chat Completions（gpt-4o-mini + JSON mode）を前提としています。レスポンスバリデーションとリトライを実装していますが、APIの仕様変更や料金に注意してください。
- DuckDB の executemany に関する互換性（空リスト不可等）を考慮した実装がされています。DuckDB のバージョン差異に注意してください。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。運用時のディスク管理方針を検討してください。

---

この README はコードベースの主要箇所に基づいて要点をまとめたものです。詳細な API 仕様や運用手順（cron ジョブ、systemd、コンテナ化、CI 設定など）は別途ドキュメント化してください。必要であればサンプルの .env.example、docker-compose / systemd ユニット、またはユニットテスト向けのモック方法（OpenAI 呼び出しの patch 方法等）を追記できます。