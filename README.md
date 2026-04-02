# KabuSys

日本株向けの自動売買／データプラットフォームのライブラリ群です。ETL、ニュースNLP（LLMを使ったセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログスキーマなどを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群です：

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）と DuckDB への冪等保存
- RSS からのニュース収集と前処理（SSRF対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別・マクロ）
- ETF（1321）の MA とマクロセンチメントを合成した市場レジーム判定
- 研究（Research）用途のファクター計算、将来リターン・IC計算、Zスコア正規化など
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査（audit）用のテーブル定義と初期化ユーティリティ

設計上、ルックアヘッドバイアスを避けるために内部で `date.today()` / `datetime.today()` を不用意に使わないように注意されています。API呼び出しはリトライ・バックオフやフェイルセーフ（失敗時にゼロやスキップ）を備えています。

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants API クライアント（fetch / save / token refresh / rate limit）
  - 日次 ETL パイプライン（run_daily_etl）
  - 市場カレンダー更新ジョブ（calendar_update_job）
- ニュース収集・NLP
  - RSS 取得・前処理（SSRF対策、URL正規化、記事ID生成）
  - OpenAI を使った銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF MA による市場レジーム判定（score_regime）
- 研究（Research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
  - z-score 正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（run_all_checks）
- 監査（Audit）
  - signal_events / order_requests / executions テーブル定義
  - 監査DB初期化ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラッパー（kabusys.config.settings）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型記法に `|` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発パッケージをまとめる場合 requirements.txt / pyproject.toml を用意して pip install -e . 等
```

---

## 環境変数 / 設定 (.env)

プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。自動読み込みを無効化するには環境変数を設定してください：

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（ライブラリ内 Settings が要求するもの）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

OpenAI を使う処理を行う場合:

- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime の引数で渡すことも可能）

任意（デフォルト値が存在するもの）:

- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV in {development, paper_trading, live} (default: development)
- LOG_LEVEL in {DEBUG, INFO, WARNING, ERROR, CRITICAL} (default: INFO)

.env の書式は一般的な KEY=VALUE 形式をサポートし、export KEY=val やクォート、インラインコメントの扱いも考慮されています。

---

## セットアップ手順

1. リポジトリをクローン（またはコードを配置）:

   ```bash
   git clone <repository-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

3. 環境変数 (.env) を作成:

   プロジェクトルートに `.env` を作り、必須トークン等を設定します。

   例:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB 用データディレクトリを作成（必要であれば）:

   ```bash
   mkdir -p data
   ```

5. （オプション）監査DB初期化:

   Python インタプリタから:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()
   ```

---

## 使い方（主要 API の例）

以下はライブラリを直接インポートして使う例です。実運用ではこれらをジョブスケジューラ（cron、systemd タイマー等）やワークフローから呼び出します。

- ETL（日次パイプライン）を実行する例:

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
conn.close()
```

- ニュースセンチメント（銘柄別）を生成する例:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_scored = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY が環境変数にある場合は None で可
print(f"scored {n_scored} codes")
conn.close()
```

- 市場レジーム判定を実行する例:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

- ニュース RSS を取得する（単体）例:

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- 研究用ファクター計算の例:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
conn.close()
```

- データ品質チェック（ETL後に利用）:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=target)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点：
- OpenAI を使う関数は `api_key` 引数でキーを渡すか、環境変数 `OPENAI_API_KEY` を設定してください。
- J-Quants の API 呼び出しは ID トークンを内部でリフレッシュしますが、`JQUANTS_REFRESH_TOKEN` の設定が必要です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env 自動読み込み、Settings）
- ai/
  - __init__.py
  - news_nlp.py — 銘柄別ニュースセンチメント（score_news）
  - regime_detector.py — ETF MA + マクロセンチメントによる市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save/get_id_token, rate limit, retry）
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl...）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py — RSS 収集・前処理
  - quality.py — データ品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - audit.py — 監査スキーマ定義・初期化（init_audit_db）
- research/
  - __init__.py
  - factor_research.py — Momentum/Volatility/Value 計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ等

---

## 補足 / 実運用の注意点

- セキュリティ
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml の使用などを考慮していますが、本番導入前に環境固有のセキュリティレビューを行ってください。
- トークン・キー管理
  - J-Quants、OpenAI、kabuステーション、Slack のキーは安全に管理し、リポジトリにコミットしないでください。
- レート制限とコスト
  - OpenAI / J-Quants の API はレート制限とコストがあります。バッチサイズや頻度は運用に合わせて調整してください（コード中にバッチサイズ・バックオフ設定あり）。
- DuckDB
  - データはデフォルトで `data/kabusys.duckdb` に保存されます。バックアップや運用ストレージの管理を検討してください。
- ログ
  - settings.log_level でログレベルを調整できます。運用では INFO 以上が推奨です。

---

## 開発 / テストのヒント

- 自動 .env 読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で有用）。
- OpenAI 呼び出しや外部 HTTP 呼び出しはモック化しやすい設計（内部関数の置き換えを想定）になっています。例えば `kabusys.ai.news_nlp._call_openai_api` をパッチしてテストできます。

---

問題報告・機能追加の要望があれば、詳細（再現手順、ログ抜粋）を添えて Issue を作成してください。