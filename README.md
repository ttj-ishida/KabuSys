# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
DuckDB をデータレイクとして扱い、J-Quants からのデータ取得・ETL、ニュースの収集・LLM によるセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）等の機能を提供します。

主な想定用途
- データパイプライン（株価・財務・市場カレンダー）の差分取得と品質チェック
- ニュース記事の収集と銘柄単位の AI センチメントスコア算出
- 市場レジーム判定（ETF MA + マクロニュースの LLM スコア合成）
- 研究用ファクター計算・特徴量解析
- 発注フロー追跡のための監査ログスキーマ初期化

---

## 機能一覧（抜粋）

- 環境設定読み込み（.env / .env.local 自動読み込み、無効化オプションあり）
- J-Quants API クライアント（レートリミット・リトライ対応、トークン自動リフレッシュ）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS、SSRF 対策、記事正規化、raw_news / news_symbols への保存想定）
- ニュース NLP（gpt-4o-mini を使った銘柄別センチメント score_news）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM で score_regime）
- 研究モジュール（モメンタム・バリュー・ボラティリティ等のファクター計算、前方リターン、IC、統計サマリー）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

---

## 必要条件 / 依存パッケージ

- Python 3.10+
- duckdb
- openai
- defusedxml

（実行環境に応じて追加で requests 等が必要になるケースがあります。setup.py / pyproject.toml がある場合はそちらを参照してください。）

インストール例（ローカル開発）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# パッケージを開発モードでインストールする場合（プロジェクトルートで）
pip install -e .
```

---

## 環境変数 / .env

このプロジェクトは環境変数から設定を読み取ります（src/kabusys/config.py）。自動でプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を読み込みます。

重要な環境変数（主なもの）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が利用）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注機能がある場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）

自動読み込みを無効化する:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

.env の例（最低限必要なキー）
```
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン、仮想環境を作成・有効化
2. 必要パッケージをインストール（上記参照）
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB データベースのディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```
5. （任意）監査ログ用 DB を初期化する（例: data/audit.duckdb）

---

## 使い方（代表的なコード例）

以下は Python REPL / スクリプトから直接呼び出す例です。各例では DuckDB の接続を渡します。

1) ETL（日次 ETL を実行）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの AI スコア付与（score_news）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須（env か引数）
print("written:", n_written)
```

3) 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログスキーマの初期化（監査用 DB を作る）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_db_path = Path("data/audit.duckdb")
conn = init_audit_db(audit_db_path)
# conn を保持して必要な監査ログ操作を行います
```

注意点:
- OpenAI 呼び出しは外部 API のためコストとレート制限・エラーを考慮してください。テスト時は該当関数をモックする設計になっています（例: unittest.mock.patch）。
- DuckDB の接続はプロセス内で再利用することを推奨します。
- run_daily_etl は内部でカレンダー調整を行い、Look-ahead バイアスに注意した実装になっています。

---

## ディレクトリ構成（概要）

以下は主要なファイル / モジュールのツリー（抜粋）です：

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースの LLM スコアリング（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch / save）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult の再エクスポート
    - news_collector.py          — RSS ニュース収集・前処理
    - calendar_management.py     — 市場カレンダー管理（is_trading_day 等）
    - quality.py                 — データ品質チェック
    - stats.py                   — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py     — 前方リターン / IC / 統計サマリー
  - other modules...

各モジュールは docstring と関数注釈で動作意図が詳細に書かれています。API レベルでは DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取る関数が多く、外部依存（発注 API 等）を直接叩かない設計がなされています（安全性の確保とテスト容易性）。

---

## テスト・開発メモ

- OpenAI API など外部呼び出しは、ユニットテストでは該当関数をモックすることを推奨します。news_nlp と regime_detector は内部で _call_openai_api を使用しており、テスト用にパッチ可能です。
- 自動 .env ロードはテストで邪魔なときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- DuckDB の executemany に空リストを渡すと問題になるバージョンの考慮がコード内にあります（空チェック済み）。

---

もし README に追加したい「サンプル .env.example の完全なテンプレート」や「運用時の cron / Airflow での運用例」などがあれば、その内容に合わせて追記できます。必要なら運用フロー（ETL スケジュール例、監視 Slack 通知の実装例）も作成します。