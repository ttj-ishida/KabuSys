# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（注文→約定トレーサビリティ）、市場レジーム判定などの機能を備えた Python パッケージです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env）例
- 基本的な使い方（例）
- よく使う API の説明
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システムや研究基盤で必要になるデータプラットフォーム機能を集約したライブラリです。  
主に以下を目的とします。

- J-Quants API を使った株価・財務・マーケットカレンダーの差分 ETL（DuckDB への永続化）
- RSS によるニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP スコアリング（銘柄ごとのセンチメント）
- 市場レジーム判定（ETF の MA とマクロニュースを組合せ）
- 研究（ファクター計算、将来リターン、IC 計算、正規化等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API 失敗時はスキップして継続）」を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 各種）
  - ニュース収集（RSS fetch, 前処理、raw_news 保存）
  - カレンダー管理（営業日判定、next/prev_trading_day）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを LLM に投げて各銘柄の ai_score を ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースから日次市場レジームを判定
- research/
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: forward returns / IC / summary / rank
- config.py: 環境変数・設定管理（.env 自動読み込み機能あり）
- audit / execution / monitoring 等（パッケージ化のための名前空間）

---

## セットアップ手順

1. リポジトリをクローン（あるいはソースを取得）
2. 仮想環境を作成・有効化（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージをインストール（開発インストール）
   - pip install -e .
4. 必要な外部パッケージ（主に）:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外のパッケージがあれば requirements.txt を参照してください）
   例: pip install duckdb openai defusedxml

注意:
- パッケージは src/ 配下に配置される structure （PEP 517/518 準拠）を想定しています。
- 実行には J-Quants のリフレッシュトークン、OpenAI の API キー 等の環境変数が必要です（下記参照）。

---

## 環境変数（.env）例

KabuSys はプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

最低限設定が必要な変数（プロダクションで必須）:
- JQUANTS_REFRESH_TOKEN=...      # J-Quants のリフレッシュトークン
- KABU_API_PASSWORD=...         # kabuステーション API のパスワード
- SLACK_BOT_TOKEN=...           # Slack 通知用 Bot Token
- SLACK_CHANNEL_ID=...          # Slack 通知先チャンネル ID

任意 / デフォルト値あり:
- KABUSYS_ENV=development | paper_trading | live  (デフォルト: development)
- LOG_LEVEL=INFO | DEBUG | ...  (デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env ロードを無効化

LLM を利用する機能を使う場合:
- OPENAI_API_KEY=...            # OpenAI API キー（ai.score 系関数で利用可能）

データベースパス（デフォルトあり）:
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

.example（抜粋）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-......
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 基本的な使い方（コード例）

事前に DuckDB 接続を作成して、各関数に接続を渡して使います。

- DuckDB 接続の例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する（run_daily_etl）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai/news_nlp.score_news）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```
- 市場レジーム判定（ai/regime_detector.score_regime）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# あるいはインメモリ:
# audit_conn = init_audit_db(":memory:")
```

- 研究機能（ファクター計算）:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m", "mom_6m"])
```

エラーハンドリング:
- 多くの処理は API 障害や不足データ時にフェイルセーフで動作する（例: LLM エラー時に 0.0 を使う等）。
- DB 書き込み処理はトランザクションを使う箇所とそうでない箇所があります（関数の docstring を参照してください）。

---

## よく使う API（要点）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_base_url, settings.slack_bot_token, settings.duckdb_path, settings.env, settings.log_level など。
  - .env 自動読込（プロジェクトルートを .git / pyproject.toml で検出）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, id_token=None, run_quality_checks=True, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token(refresh_token=None)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - preprocess_text(text)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## 実行上の注意 / 運用ノウハウ

- 環境変数の自動読み込みは便利ですが、ユニットテスト等で無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しはレートや課金に注意。score_news と regime_detector はリトライやフェイルセーフを備えますが、API キーの管理は運用者で行ってください。
- J-Quants API はレート制限があるため、jquants_client 内でスロットリング・リトライ制御をしています。大量取得時は API レートに注意。
- DuckDB の executemany に関する互換性（空リストを渡せない等）を考慮した実装になっています。バージョン差に注意してください。

---

## ディレクトリ構成（主要ファイルの役割）

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン）
  - config.py — 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save/認証/保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult のエクスポート（alias）
    - news_collector.py — RSS 取得・前処理・保存ユーティリティ
    - calendar_management.py — マーケットカレンダー管理（営業日判定・更新ジョブ）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（missing/spike/duplicates/date consistency）
    - audit.py — 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/volatility/value）
    - feature_exploration.py — forward returns / IC / rank / summary
  - ai, research モジュールはバッチ処理・研究用途の関数を提供

テストや運用スクリプトはプロジェクト側で用意して利用してください。

---

## ライセンス / コントリビューション

（ここにはプロジェクトのライセンスやコントリビューション方針を記載してください。リポジトリに LICENSE がある場合はそちらを参照するようにしてください。）

---

以上が KabuSys の概要と利用方法です。  
追加で README に含めたい具体的な実行例（systemd ジョブ、dag、cron、CI 設定等）や、requirements.txt の内容、デプロイ手順などがあれば追記します。必要な出力や形式（英語版など）も指示してください。