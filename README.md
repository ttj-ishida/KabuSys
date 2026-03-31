# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants からのデータ取得・ETL、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）などの機能を提供します。バックテストや本番運用（paper/live）を想定した設計方針（ルックアヘッド回避、冪等性、フォールバック処理、堅牢な API リトライ等）を持ちます。

主な用途例:
- 日次 ETL（株価・財務・市場カレンダー）の自動取得と品質チェック
- RSS ニュース収集 → OpenAI による銘柄別センチメント算出（ai_scores への保存）
- マーケットレジーム（bull/neutral/bear）判定（ETF とマクロニュースの混合スコア）
- 監査用テーブル（signal → order_request → execution のトレーサビリティ）初期化

---

## 機能一覧

- data（ETL / データ品質 / カレンダー / J-Quants クライアント）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - 市場カレンダー管理（営業日判定・next/prev_trading_day・calendar_update_job）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS -> raw_news 保存、SSRF / XML 爆弾対策付き）
  - 監査ログ初期化（init_audit_schema / init_audit_db）

- ai（ニュース NLP / レジーム判定）
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む（OpenAI）
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースの LLM スコアを合成して market_regime へ書き込み

- research（ファクター計算 / 特徴量探索）
  - momentum / value / volatility 等の定量ファクター算出
  - forward returns, IC（Spearman）の計算、ファクター統計サマリー、Zスコア正規化ユーティリティ

- config
  - 環境変数の自動読み込み（プロジェクトルートの .env / .env.local を読み込み）
  - Settings クラスによる集中管理（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）

- audit / execution / monitoring（監査・発注・監視のための基盤コード群）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 構文や型ヒントに依存）
- DuckDB（Python パッケージとしてインストール）
- OpenAI SDK（openai）
- defusedxml（RSS パーシングの安全対策）

推奨インストール例:
```bash
python -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install duckdb openai defusedxml
# 追加で開発用に: flake8, pytest など
```

環境変数（必須・主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が利用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能等で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能使用時）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- DUCKDB_PATH: (任意) DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: (任意) 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境識別 (development | paper_trading | live)（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）

自動 .env 読み込み
- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を起点）を探索し、.env と .env.local を自動で読み込みます。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

例: .env (プロジェクトルート)
```
JQUANTS_REFRESH_TOKEN="xxxxx"
OPENAI_API_KEY="sk-xxxx"
KABU_API_PASSWORD="your_kabu_pass"
SLACK_BOT_TOKEN="xoxb-xxxx"
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

1) DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース NLP で銘柄スコアを生成する:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

3) 市場レジームを判定して保存する:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査用の DuckDB を初期化する:
```python
from kabusys.data.audit import init_audit_db

# ファイルベースの DB（ディレクトリは自動作成）
audit_conn = init_audit_db("data/audit_duckdb.duckdb")
# またはインメモリ:
# audit_conn = init_audit_db(":memory:")
```

注意:
- OpenAI 呼び出しを含む機能は API キーとネットワーク接続が必要です。
- run_daily_etl 等は内部で ETL → 品質チェック → 保存 を実行します。実運用前にローカルで少量データを用いた動作確認を推奨します。
- DuckDB のスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar 等）は ETL 実行前に適切に作成されていることを前提とします。スキーマ管理は別途 data.schema モジュールや初期化スクリプトを用意してください（本リポジトリの intent に依存）。

---

## ディレクトリ構成（主要ファイル）

```
src/kabusys/
├─ __init__.py                 # パッケージ定義・バージョン
├─ config.py                   # 環境変数読み込み・Settings
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py              # ニュースの OpenAI スコアリング（score_news）
│  └─ regime_detector.py       # マーケットレジーム判定（score_regime）
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py        # J-Quants API クライアント（fetch/save 系）
│  ├─ pipeline.py              # ETL パイプライン（run_daily_etl 他）
│  ├─ etl.py                   # ETL の公開インターフェース（ETLResult）
│  ├─ quality.py               # データ品質チェック
│  ├─ news_collector.py        # RSS ニュース収集・前処理
│  ├─ calendar_management.py   # 市場カレンダー管理（営業日判定等）
│  ├─ audit.py                 # 監査ログスキーマ作成 / init_audit_db
│  └─ stats.py                 # 統計ユーティリティ（zscore_normalize）
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py       # ファクター計算（momentum, value, volatility）
│  └─ feature_exploration.py   # 将来リターン / IC / 統計サマリー 等
# 他に execution, monitoring, strategy 等のサブパッケージが想定される
```

各モジュールは設計方針コメントを付与しており、Look-ahead バイアス防止やフェイルセーフの挙動が明記されています。API 呼び出しにはリトライ / バックオフ / レート制御が組み込まれています。

---

## 設定や運用上の注意

- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかで、is_live/is_paper/is_dev が Settings により参照できます。運用モードに応じた安全策（注文抑止やモック化）を実装してください。
- OpenAI の呼び出し結果は外部依存のため、API エラー時は多くの箇所でフェイルセーフとして 0.0 を返す挙動があります。ログをチェックして未取得部分の追試やアラートを行ってください。
- .env の自動ロードは便利ですが、CI / テスト環境で環境を固定したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。
- DuckDB の executemany に関する互換性に注意（空リストを渡すとエラーになるバージョンがあるため、本実装は空チェックを行っています）。

---

README に書かれている以外の詳細な使用例や schema 初期化手順は各モジュールの docstring を参照してください。必要であれば、スキーマ生成スクリプトやサンプルデータ、CI / 実行スクリプトの追加をサポートします。