# KabuSys

日本株自動売買プラットフォームのライブラリ群です。データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレース）など、アルゴリズム取引に必要な基盤機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない実装）
- DuckDB を用いたローカルデータストア（ETL・集計用）
- OpenAI（gpt-4o-mini）を用いたニュース解析（JSON Mode）を組み込み
- J-Quants API 経由で株価・財務・市場カレンダーを取得（レートリミット・リトライ備えあり）
- 冪等性（ON CONFLICT 等）を重視した DB 書き込み

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価（日足）、財務、上場銘柄情報、JPX カレンダーを差分取得・保存
  - run_daily_etl による日次 ETL パイプライン
- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合の検出
- ニュース収集 / 前処理
  - RSS フィードの安全な取得（SSRF 防止、XML 攻撃対策）と前処理、raw_news への保存を想定
- ニュース NLP（OpenAI）
  - 銘柄ごとニュースのセンチメント（ai_scores）算出（batch + JSON Mode）
  - マクロニュースを使った市場レジーム判定（ETF 1321 の MA200 と LLM を重合）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC 計算、Z スコア正規化、統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local / 環境変数で設定を管理（自動読み込み）

---

## 必要要件（主な依存）

- Python 3.10+
- パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実際には pyproject.toml / requirements.txt を参照してインストールしてください）

---

## インストール

1. リポジトリをクローンし、パッケージをインストール（編集可能インストール等）:

```bash
git clone <repo-url>
cd <repo>
pip install -e ".[dev]"   # または pip install -e .
```

2. 必要なライブラリが不足している場合は個別にインストールしてください:

```bash
pip install duckdb openai defusedxml
```

---

## 環境変数 / 設定

設定は OS 環境変数、プロジェクトルートの `.env`、`.env.local` から読み込まれます。自動ロードは、パッケージ内 `kabusys.config` が .git または pyproject.toml を基準にプロジェクトルートを検出して行います。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（メジャーなもの）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OpenAI / News NLP
  - OPENAI_API_KEY (score_news / regime_detector のデフォルト)
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベース / ファイル
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH 等（監視用）
- システム / ログ
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env の読み込み優先度: OS 環境変数 > .env.local > .env
（.env.local は .env を上書きする目的で使用）

---

## セットアップ（簡単な例）

1. プロジェクトルートに `.env`（必要なキーを設定）を作成:

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=yourpassword
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

2. DuckDB 接続先のディレクトリを作る（自動的に作るユーティリティもありますが、手動で準備しておくと安心）:

```bash
mkdir -p data
```

---

## 使い方（主要ユーティリティ）

以下は Python インタプリタ / スクリプト内での利用例です。

- DuckDB に接続して日次 ETL を実行

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は .env またはデフォルトから取得
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）を算出

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 指定日に対するニュースウィンドウでスコアを算出（OPENAI_API_KEY が設定されている必要あり）
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（ma200 と マクロニュース（LLM）を合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（監査専用 DuckDB）

```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn は監査テーブルが作成された DuckDB 接続
```

- J-Quants クライアントを直接使用してデータ取得（テストや開発用）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
print(len(records))
```

---

## 監査 / 発注周り（簡単な紹介）

監査ログ（signal_events, order_requests, executions）は `kabusys.data.audit` で初期化可能です。order_request_id を冪等キーとして扱う設計で、発注の重複防止・フロー追跡を行います。初期化は init_audit_schema / init_audit_db を使って行ってください。

---

## 注意点 / 運用上のポイント

- OpenAI 呼び出しは課金対象となるため、API キーの管理・呼び出し頻度に注意してください。score_news / score_regime はエクスポネンシャルバックオフ・フェイルセーフを備えていますが、呼び出しに失敗した場合はスコア0（中立）で継続する設計です。
- J-Quants API はレート制限があるため、jquants_client では内部でスロットリングとリトライを実装しています。大量取得時は ETL の実行間隔を調整してください。
- テストや CI 環境で .env の自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany に空リストを渡すと問題となるバージョンがあるため、モジュール内で対策済みです（空チェックあり）。

---

## ディレクトリ構成（src/kabusys 以下の主なモジュール）

- kabusys/
  - __init__.py (パッケージ初期化、__version__)
  - config.py
    - 環境変数・.env 読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py : ニュースセンチメント算出（score_news）
    - regime_detector.py : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（fetch / save）
    - pipeline.py : ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py : ETLResult の再エクスポート
    - news_collector.py : RSS 取得と前処理ユーティリティ
    - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
    - stats.py : zscore_normalize 等の統計ユーティリティ
    - quality.py : データ品質チェック（check_missing_data, check_spike, ...）
    - audit.py : 監査ログ（DDL / init）
  - research/
    - __init__.py
    - factor_research.py : Momentum / Volatility / Value 計算
    - feature_exploration.py : forward returns, IC, factor_summary 等

（各モジュールは docstring に設計意図・処理フローが詳述されています）

---

## 開発 / 貢献

- 各モジュールの docstring に意図と使用上の注意が記載されています。変更時は docstring とユニットテストを更新してください。
- テスト環境で OpenAI / J-Quants 実 API を叩かないようにモック可能な構造（API 呼び出しラッパーの差し替え）になっています。

---

README はここまでです。追加で以下が必要であれば教えてください：
- .env.example の具体的なテンプレート
- 具体的な CLI / ジョブ起動スクリプト例（systemd / CRON / Airflow など）
- 詳細な API リファレンス（関数ごとの引数・戻り値の例）