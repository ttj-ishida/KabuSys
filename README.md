# KabuSys

日本株向けのデータプラットフォーム & 自動売買/リサーチ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー収集）、ニュース収集・NLP（OpenAI を用いたセンチメント）、ファクター計算、監査ログ（発注/約定トレース）、および補助ユーティリティを提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得（J-Quants API）
  - 株価日足 (OHLCV)
  - 財務諸表（四半期等）
  - JPX マーケットカレンダー
  - 上場銘柄情報
  - ページネーション／レート制御／トークン自動リフレッシュ／再試行ロジックを実装

- ETL パイプライン
  - 差分更新（最終取得日ベース、バックフィル対応）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次バッチ実行エントリ `run_daily_etl`

- ニュース収集・NLP
  - RSS 取得（SSRF対策、URL正規化、トラッキングパラメータ削除）
  - OpenAI（gpt-4o-mini） を用いたセンチメント解析（銘柄別/マクロ）
  - スコアを ai_scores テーブルへ書き込み（冪等）

- 市場レジーム判定
  - ETF(1321) の 200日移動平均乖離 と マクロニュース LLM センチメントを重み合成しレジーム（bull/neutral/bear）判定

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー 等のファクター群算出
  - 将来リターン・IC・統計サマリ機能
  - z-score 正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等のテーブル定義・初期化
  - 発注から約定まで UUID 連鎖で完全トレース可能

- 汎用ユーティリティ
  - カレンダー管理（営業日判定、next/prev/trading days）
  - DuckDB へのスキーマ初期化・保存ユーティリティ
  - 環境変数管理（.env 自動読み込み機能）

---

## 必要条件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml

実際の使用環境では他のライブラリも必要になる可能性があります。適宜 requirements.txt を用意してください。

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - あるいは最低限:
     - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を配置すると自動で読み込まれます。
   - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化できます（テスト等で利用）。

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（発注周りで使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャネル ID

推奨／任意
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が使用）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite モニタリング DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例 `.env`（テンプレート）
```
# .env.example 参考
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化（DB / スキーマ）

- 監査ログ専用 DuckDB を初期化する例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" でインメモリ可
# 返される conn は duckdb の接続オブジェクト
```

- アプリケーション用 DuckDB にスキーマなどを作るユーティリティがあればそれを利用してください（本コードベース内に schema init 用ユーティリティが存在する想定）。

---

## 使い方（主要 API の例）

- 設定の参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

- ETL（日次一括処理）:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア（銘柄別）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を渡さない場合は環境変数 OPENAI_API_KEY を使用
print("scored:", count)
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- リサーチ（ファクター計算）例:
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- RSS 取得（ニュース収集）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意:
- OpenAI などの外部 API 呼び出しは料金が発生する場合があります。API キーと使用量管理には注意してください。
- 実際の発注/実行ロジック（kabu ステーション連携）は本コードベース内に直接含めていない/限定的です。実運用前に十分なテストと安全策（ペーパートレード・制限）を設けてください。

---

## 自動 .env 読み込みの挙動

- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）を特定し、`<root>/.env` を読み込みます。その後 `.env.local`（あれば上書き）を読み込みます。
- OS 環境変数が優先され、.env の値は既存環境変数を上書きしません（ただし .env.local は上書き可）。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用）。

.env のパースはシェル形式（export を許可、シングル/ダブルクォート対応、コメント対応）です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント解析（銘柄別）
    - regime_detector.py         — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得・保存）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL 公開インターフェース
    - news_collector.py          — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py     — マーケットカレンダー管理（営業日判定など）
    - stats.py                   — 統計ユーティリティ（zscore 等）
    - quality.py                 — データ品質チェック
    - audit.py                   — 監査ログ（発注→約定トレーサビリティ）
  - research/
    - __init__.py
    - factor_research.py         — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py     — 将来リターン/IC/統計サマリー等

---

## 注意点 / 運用上のヒント

- ルックアヘッドバイアスを避ける実装方針が随所に反映されています：
  - API 取得時の fetched_at、ETL 内での target_date 明示、DB クエリの排他条件など。
- OpenAI 呼び出しは失敗時フォールバックやリトライを実装していますが、ネットワーク・料金面でのリスクは独自に管理してください。
- 本ライブラリはデータ基盤・リサーチ用途を主眼に設計されています。実際の資金を動かす前にペーパートレード環境で十分な検証を行ってください。
- DuckDB と OpenAI SDK のバージョン互換性に依存します。実運用では固定バージョンでのテストを推奨します。

---

この README はコードベースの主要ポイントをまとめたものです。詳細な API / スキーマ / 実行フローは各モジュールのドキュメント文字列（docstring）を参照してください。必要であれば README に「API リファレンス」や「運用手順（デプロイ/ジョブスケジューリング）」のセクションを追加します。