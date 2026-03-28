# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。ETL による市場データ取得、ニュースの収集・NLP スコアリング、ファクター計算、監査ログ（オーディット）や市場レジーム判定まで、運用／研究で必要な機能群を提供します。

---

## 主な特徴（機能一覧）

- データ ETL / 管理
  - J-Quants API からの株価（OHLCV）、財務データ、JPX カレンダーの差分取得・保存（DuckDB）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS）と冪等保存（raw_news / news_symbols）
- AI（LLM）による解析
  - ニュースのセンチメントスコアリング（ai.news_nlp.score_news）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成、ai.regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を JSON mode で利用。リトライ・フェイルセーフを備える
- リサーチ／ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（情報係数）、統計サマリ（research.feature_exploration）
  - クロスセクション Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ・トレーサビリティ
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ（data.audit）
  - 発注フローの冪等性と時系列トレーサビリティを重視
- 実運用向け設計
  - 環境変数ベースの設定（config.Settings）、.env / .env.local の自動ロード（無効化可）
  - DuckDB を中心とした軽量永続化、Slack 通知等のインテグレーションポイント（設定で利用）

---

## 必須環境 / 依存パッケージ

- Python 3.10+
- 必要な主なパッケージ（例）
  - duckdb
  - openai
  - defusedxml

（その他、標準ライブラリを多用。実際のプロジェクトでは requirements.txt を用意して pip install してください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 任意: pip install -e .
```

---

## 環境変数（設定）

config.Settings は環境変数から設定値を読み込みます。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- OPENAI_API_KEY (必須 for AI 呼び出し時、関数引数で上書き可能)
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（必要な場合）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（モニタリング等で使用、デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（概要）

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトの requirements.txt / pyproject.toml を使用
   ```

3. 環境変数を用意
   - プロジェクトルートに `.env` を置く（上記例を参照）
   - テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化可能

4. データベース初期化（監査用テーブルなど）
   - DuckDB 接続を作成し、監査スキーマを初期化できます
   ```python
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db(settings.duckdb_path)  # DB ファイルを作成・スキーマ初期化
   ```

---

## 使い方（主要な呼び出し例）

- 日次 ETL（J-Quants からデータ取得・品質チェック）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（AI）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か、api_key 引数で指定可能
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {count}")
```

- 市場レジーム判定（MA + マクロセンチメント）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB を別途初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- J-Quants クライアントの直接利用（開発用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# トークンは settings.jquants_refresh_token から自動で取得されます
records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
```

---

## 注意点 / 設計上のポイント

- ルックアヘッドバイアス防止:
  - ほとんどの関数は内部で date.today() に依存せず、引数で基準日を受け取ることでバックテストでのルックアヘッドを防止しています。
- 冪等性:
  - ETL / 保存関数は可能な限り ON CONFLICT DO UPDATE / 挿入制約で冪等性を保つ設計です。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）呼び出しはリトライやフォールバック（失敗時はスコア 0.0 等）を行い、一部失敗がシステム全体を停止させないよう設計されています。
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動読み込みします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル）

（パッケージルート: src/kabusys）

- __init__.py
- config.py — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM ベースセンチメントスコアリング
  - regime_detector.py — ETF + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult のエクスポート
  - calendar_management.py — JPX カレンダー管理（営業日判定等）
  - news_collector.py — RSS ニュース収集と前処理
  - audit.py — 監査ログテーブル定義・初期化
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / サマリー等の分析ユーティリティ

---

## 開発・拡張のヒント

- テスト:
  - 多くのネットワーク呼び出し箇所（OpenAI / J-Quants / RSS）はモックしやすいように設計されています（内部の _call_openai_api や _urlopen を差し替え可能）。
- ロギング:
  - settings.log_level を利用してログレベル制御が可能です。運用時は INFO/WARNING、デバッグ時は DEBUG を推奨します。
- 本番化:
  - KABUSYS_ENV を `paper_trading` / `live` に切り替えた場合、発注まわりや外部連携の実装に注意してください（現コードベースはデータ取得・リサーチ・監査中心）。

---

もし README にサンプルの requirements.txt、Docker/Docker Compose や CI 用の設定例、より具体的な運用手順（ETL のスケジューリングや発注フロー統合）を追加したい場合は、用途に応じたテンプレートを作成します。どの部分を補足しましょうか？