# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants API を用いたデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（監査テーブル）などのユーティリティ群を含みます。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 概要

KabuSys は以下の用途に向けたモジュール群を提供します。

- J-Quants API からの株価 / 財務 / カレンダー取得と DuckDB への差分保存（ETL）
- RSS ニュース収集と OpenAI を用いた銘柄別センチメント（ai_score）生成
- マクロニュースと ETF の MA200 を組み合わせた市場レジーム判定
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal / order_request / executions）用のスキーマ初期化ユーティリティ

設計上、ルックアヘッドバイアスに注意した実装（日時参照を呼び出し側から与える）や堅牢なエラーハンドリング、冪等性（INSERT … ON CONFLICT）などが考慮されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 呼出し・ページネーション・保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 収集 -> raw_news 保存（SSRF 対策・サイズ検査）
  - calendar_management: 営業日判定・next/prev_trading_day、calendar_update_job
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用スキーマ作成・init_audit_db
  - etl / stats: ETL 用結果クラスや統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: ニュースから銘柄ごとの ai_score を生成して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321)の MA200 乖離とマクロセンチメントを合成して market_regime に書き込む
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - 環境変数自動読み込み (.env / .env.local)、Settings クラス（各種必須設定をプロパティで取得）

---

## 要件（主な依存ライブラリ）

- Python 3.10+
- duckdb
- openai
- defusedxml

※実際のプロジェクト環境では pyproject.toml / requirements.txt を参照してください。

---

## 環境変数（必須 / 推奨）

主要な環境変数は kabusys.config.Settings 経由で取得されます。少なくとも以下を設定してください：

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を用いる場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- KABU_API_PASSWORD — kabuステーション API を使う場合のパスワード

OpenAI 関連:
- OPENAI_API_KEY — news_nlp / regime_detector で利用（関数呼び出し時に api_key を渡すことも可能）

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出して `.env` → `.env.local` の順に読み込みます。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env の例（README 用の簡易サンプル）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## インストール / セットアップ

1. リポジトリをクローン（あるいはパッケージをインストール）:
   - 開発中: python パッケージとして編集可能インストール
     ```
     pip install -e .
     ```
   - あるいは requirements.txt / pyproject.toml に従って依存をインストールしてください。

2. 環境変数を設定（上記参照）。プロジェクトルートに `.env` を置くと自動で読み込まれます。

3. DuckDB データベースの準備:
   - デフォルトは data/kabusys.duckdb（Settings.duckdb_path）。
   - 必要に応じて `kabusys.data.audit.init_audit_db(...)` で監査専用 DB を初期化してください（例は下記参照）。

---

## 使い方（例）

以下は Python スクリプトや REPL から使う基本例です。

- DuckDB 接続と ETL の実行（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（news_nlp）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジームのスコア算出（regime_detector）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査ログ用）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# init_audit_db は UTC タイムゾーン設定とスキーマ作成を行う
```

- カレンダー関連ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

ログレベルは環境変数 LOG_LEVEL で調整できます（例: LOG_LEVEL=DEBUG）。

注意点:
- AI 呼び出し（OpenAI）は API キーの設定が必要です。関数引数で api_key を明示してもよいです。
- ルックアヘッドバイアス防止のため、関数の多くは target_date を外部から渡す設計です。内部で date.today() を参照しない実装になっています。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール構成（src/kabusys 以下）:

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
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージは研究用ユーティリティ（ファクター計算・IC 等）
  - その他: strategy / execution / monitoring 等が __all__ に含まれる可能性あり（現在はモジュール定義ベース）

（README の先頭にある __all__ 宣言は public API の一例: ["data", "strategy", "execution", "monitoring"]）

---

## 実運用上の注意

- 認証トークンや API キーは機密情報です。`.env` ファイルや CI シークレットで安全に管理してください。
- OpenAI の呼び出しはレートやコストを考慮してください（バッチ化や最小トークン設定を検討）。
- J-Quants の API レート制限に合わせた RateLimiter 実装が組み込まれていますが、ETL 実行頻度や同時実行には留意してください。
- DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, ai_scores など）は ETL / 保存関数が期待する形式に従う必要があります。スキーマ初期化関数がリポジトリにある場合はそれを使ってください（audit 用の init_audit_db 等）。

---

## 開発 / 貢献

- 自動ロードされる `.env` が原因でテストに影響が出る場合は、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- OpenAI / ネットワーク呼び出し部分はテストでモックしやすいように設計されています（内部の _call_openai_api や HTTP 関数を patch して差し替え可能）。

---

この README はコードの主要機能と使い方の要点をまとめたものです。実際の導入や運用にあたっては、プロジェクト内のドキュメント（DataPlatform.md, StrategyModel.md 等）、および該当モジュールの docstring を参照してください。必要があればサンプルスクリプトやデータベーススキーマ定義の追記も作成します。