# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究（ファクター計算）、監査ログ機能などを備えています。

## 主な特徴
- データ取得
  - J-Quants API から株価日足、財務データ、JPX マーケットカレンダーを差分取得（ページネーション対応）
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去）
- ETL / データ品質
  - 差分ETL（バックフィル対応）、品質チェック（欠損・スパイク・重複・日付不整合）
  - DuckDB への冪等保存（ON CONFLICT / upsert）
- AI（OpenAI）
  - ニュースを銘柄別にまとめて LLM に投げるニュースセンチメント（ai_scores へ保存）
  - ETF（1321）MA とマクロニュースの LLM センチメントを合成した市場レジーム判定（bull/neutral/bear）
  - 再試行・バックオフ・フェイルセーフ設計
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - order_request_id による冪等性保証
- 設定管理
  - .env 自動ロード（プロジェクトルート: .git または pyproject.toml を検出）と環境変数経由の設定

---

## 必要条件（主な Python パッケージ）
- Python 3.9+
- duckdb
- openai
- defusedxml

プロジェクトに合わせて他の依存が追加される可能性があります。実際は pyproject.toml / requirements を参照してください。

---

## インストール（開発向け）
リポジトリルート（pyproject.toml がある場所）で：

```bash
python -m pip install -e .
# もしくは必要パッケージを個別に
python -m pip install duckdb openai defusedxml
```

---

## 環境変数 / .env
主要な設定は環境変数で管理します。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須（少なくとも設定が必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 呼び出し時に引数で注入することも可）

任意（デフォルトあり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUS_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）

.env のサンプル（.env.example を参考に作成してください）。

---

## セットアップ手順（簡易）
1. リポジトリをチェックアウト
2. 開発インストール（上記参照）
3. 必要な環境変数を .env に設定
4. 初期データベースを作成（例は監査DB初期化）
   - Python REPL またはスクリプトで以下を実行

```python
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# settings.duckdb_path は環境変数 DUCKDB_PATH に従う
conn = init_audit_db(settings.duckdb_path)  # or init_audit_schema(conn)
```

5. ETL を実行してデータを取得
   - 後述の「使い方」を参照

---

## 使い方（主要な API と例）
以下はライブラリを直接呼ぶ例です。CLI は本コードベースに含まれていないため、Python スクリプトやジョブから呼び出します。

共通準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL（データ取得・品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュース NLP の実行（指定日）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"書き込んだ銘柄数: {written}")
# api_key を None にすると環境変数 OPENAI_API_KEY を参照します
```

市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

監査スキーマ初期化（既に説明）
```python
from kabusys.data.audit import init_audit_db
init_audit_db(settings.duckdb_path)
```

ファクター計算（研究用）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

マーケットカレンダー操作
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

d = date(2026, 3, 20)
is_trade = is_trading_day(conn, d)
next_trade = next_trading_day(conn, d)
days = get_trading_days(conn, date(2026, 3, 1), date(2026, 3, 31))
```

ニュース収集（RSS）を直接呼ぶ場合
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
```

注意点
- LLM 呼び出しや外部 API 呼び出しはネットワーク/レート制限の影響を受けるため、バッチ実行や監視設定を推奨します。
- OPENAI_API_KEY を明示的に渡すことでテストや並列実行での管理が容易になります。
- 本番での自動売買機能を統合する際は、KABUSYS_ENV（paper_trading / live）で安全マナーを守ってください。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下の抜粋）

- kabusys/
  - __init__.py
  - config.py  — 環境変数管理、.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースから銘柄別センチメント算出（OpenAI）
    - regime_detector.py  — ETF MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py            — 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL インターフェース再エクスポート
    - calendar_management.py — マーケットカレンダー操作・更新ジョブ
    - news_collector.py      — RSS 収集、前処理、保存ロジック
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付）
    - stats.py               — 汎用統計ユーティリティ（z-score 等）
    - audit.py               — 監査ログ（監査テーブル DDL、初期化）
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - research/*（その他研究用ユーティリティ）
  - その他（strategy, execution, monitoring 等の名前は __all__ に記載されているが抜粋）

---

## 開発 / テストに関する補足
- 設定自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト中に自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しや外部 HTTP 呼び出し箇所はモックしやすく設計されています（内部呼び出し関数を patch する想定）。
- DuckDB に対する executemany の挙動（空リスト不可等）を考慮した実装になっています。

---

README はここまでです。必要であれば、実行スクリプト例（systemd / cron / Airflow 用タスク定義）、Dockerfile、CI 設定サンプル、あるいは各モジュールの API リファレンスの追記も作成できます。どの情報を追加しますか？