# KabuSys

日本株向けのデータパイプライン・リサーチ・AI支援・監査を含む自動売買システムのライブラリ群です。  
本リポジトリは ETL（J-Quants 経由のデータ取得・保存）、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は以下の主要機能をモジュール化して提供します。

- J-Quants API を用いた株価・財務・カレンダーデータの差分 ETL（永続化は DuckDB）
- RSS ベースのニュース収集と前処理（SSRF / XML 攻撃対策を考慮）
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF の 200 日 MA とマクロセンチメントの合成）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）用スキーマ定義と初期化ユーティリティ
- 環境設定管理 (.env の自動ロードや Settings API)

設計上の特徴：
- ルックアヘッドバイアス防止（内部で date.today() や datetime.today() を不用意に参照しない実装方針）
- ETL / 保存処理は冪等（ON CONFLICT / upsert）で実行
- ネットワーク呼び出しはリトライ / バックオフ / レート制御を組み込み
- テスト容易性のため外部呼び出しを注入可能な設計

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env 自動ロード（プロジェクトルート基準）・Settings クラス（環境変数参照）
- kabusys.data
  - jquants_client: J-Quants API 経由の取得・DuckDB への保存関数
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl と ETLResult
  - news_collector: RSS 取得・前処理ユーティリティ
  - calendar_management: 市場カレンダー管理・営業日判定
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合）
  - audit: 監査ログ用 DDL / 初期化ユーティリティ（init_audit_schema, init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロセンチメントから市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要環境・依存ライブラリ

- Python 3.10+
- 推奨ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ以外は requirements.txt を用意するか下記をインストールしてください。

例（pip）:
```bash
pip install duckdb openai defusedxml
```

---

## 環境変数（主な項目）

設定は .env / .env.local / OS 環境変数から読み込まれます（優先順: OS > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用など）パス（デフォルト: data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt
   ```
   requirements.txt がない場合は最低限:
   ```bash
   pip install duckdb openai defusedxml
   ```
4. .env ファイルを作成（プロジェクトルート）。上記環境変数を設定する。
5. DuckDB データベースのディレクトリを作成する（必要であれば）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下はライブラリを Python から利用する基本例です。すべての操作は DuckDB 接続（kabusys.settings.duckdb_path を推奨）を使います。

- DuckDB 接続の作成、ETL の実行例:

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（ファイルは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date は省略で今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）スコアの実行例:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数でも、ここで直接渡してもよい
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定の実行例:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB 初期化:

```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# これで監査テーブルが作成されます
```

- カレンダー判定ユーティリティ例:

```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI を呼び出す関数（score_news / score_regime）は API キーを必要とします。api_key 引数または環境変数 OPENAI_API_KEY を用いてください。
- ETL / API 呼び出しにはネットワーク接続と有効なトークン（J-Quants など）が必要です。

---

## ディレクトリ構成（主要ファイル）

概要（src/kabusys）:

- kabusys/
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
    - pipeline.py (ETLResult 再エクスポート etl.py 経由)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py exports:
    - calc_momentum, calc_value, calc_volatility, zscore_normalize 等

各モジュールの責務:
- config.py: 環境変数のロード/検証・Settings 提供
- data/jquants_client.py: J-Quants API 呼び出し・保存ロジック（fetch / save）
- data/pipeline.py: 日次 ETL の Orchestrator（run_daily_etl 等）
- data/news_collector.py: RSS 取得・前処理ユーティリティ
- data/audit.py: 監査テーブル DDL と初期化
- ai/news_nlp.py: 銘柄別ニュースセンチメント→ai_scores への書き込み
- ai/regime_detector.py: マクロセンチメントと MA を合成した市場レジーム判定
- research/*: ファクター計算と解析ユーティリティ

---

## 運用上の注意点 / デザインノート

- Look-ahead バイアス対策として、外部 API 呼び出しや LLM 呼び出しは、対象日以前のデータのみを参照するように実装されています。バックテスト時は ETL のデータ整合性に注意してください。
- jquants_client はレート制限（120 req/min）とリトライ・トークン自動リフレッシュのロジックを持ちます。
- AI 呼び出しではレスポンスのパース失敗や API エラーに対してフェイルセーフ（デフォルトスコア 0 等）で継続する設計です。
- DuckDB に対する executemany の空リストバグ（過去の仕様）に配慮した実装があります（空時は実行しない）。
- news_collector は SSRF / XML 攻撃対策（URL 正規化・プライベート IP ブロック・defusedxml 利用・レスポンスサイズチェック）を備えています。

---

## テスト・開発補助

- config の自動 .env ロードはプロジェクトルート（.git または pyproject.toml が存在）を基準に動作します。ユニットテスト時などは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効にできます。
- AI 呼び出しのテストでは、各モジュール内の _call_openai_api 関数をモックすることで外部依存を排除できます（score_news / regime_detector 共に設計済み）。

---

README は以上です。追加で使用例や CI / デプロイ手順、より詳細な API ドキュメント（関数別引数・返り値・例外）を生成することも可能です。必要であれば作成します。