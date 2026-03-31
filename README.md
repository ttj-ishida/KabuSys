# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いた銘柄センチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどを含むモジュール群を提供します。

---

## 主要な特徴

- J-Quants API 経由の差分 ETL（株価、財務、マーケットカレンダー）  
  - ページネーション・レート制御・リトライ・トークン自動リフレッシュ対応
- ニュース収集（RSS）と NLP スコアリング（OpenAI）  
  - 銘柄ごとに記事を集約し LLM に渡して ai_score を生成
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ（モメンタム、ボラティリティ、バリューなどのファクター計算、将来リターン、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を保存する DuckDB スキーマの初期化ユーティリティ
- 設定は環境変数 / .env で管理。パッケージ読み込み時にプロジェクトルートの `.env` / `.env.local` を自動読み込み（無効化可）

---

## 動作要件（想定）

- Python 3.10+
- 主な依存ライブラリ（抜粋）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで実装されている箇所が多いです）
- J-Quants / OpenAI の API キー、kabuステーション API のパスワード等が必要

必要なパッケージはプロジェクトの pyproject.toml / requirements.txt に合わせてインストールしてください。例:
```
pip install duckdb openai defusedxml
```

---

## セットアップ

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成して依存をインストール
3. プロジェクトルートに `.env` を作成（自動読み込みされます）。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例：.env に最低限必要な変数（実運用では安全に管理してください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

設定クラスは `kabusys.config.settings` として提供され、Python から直接参照できます。
```py
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

---

## 使い方（クイックスタート）

以下は代表的な利用例です。duckdb 接続は `duckdb.connect(path)` で行います。

- 日次 ETL を実行する（prices / financials / calendar を差分で取得）
```py
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（ai_scores テーブルへ書き込み）
```py
from kabusys.ai.news_nlp import score_news
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```py
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB を初期化
```py
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は初期化済み DuckDB 接続
```

- 研究用ファクター計算（例：モメンタム）
```py
from kabusys.research.factor_research import calc_momentum
from datetime import date
conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

注意点:
- OpenAI 呼び出しは `api_key` 引数で上書き可能（指定しない場合は環境変数 `OPENAI_API_KEY` を参照）。
- LLM 呼び出し部はテスト容易性のため差し替え可能（各モジュール内の `_call_openai_api` をモック）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM を使う機能で必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト "http://localhost:18080/kabusapi"）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: one of "development", "paper_trading", "live"
- LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

設定値は `kabusys.config.settings` からプロパティとして参照できます。

---

## テスト・モックについて

- OpenAI への実際の API 呼び出しは時間とコストがかかるため、ユニットテスト時は各モジュールの `_call_openai_api` 関数をパッチして差し替える設計です（例: unittest.mock.patch）。
- RSS の取得関数 `_urlopen` などもモック可能に実装されています。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch / save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult のエクスポート
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py             — RSS 収集・正規化
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Value / Volatility 等
    - feature_exploration.py        — forward returns / IC / rank / summary
  - research/... (補助関数等)

各モジュールは DuckDB 接続オブジェクトを受け取る設計が基本です（副作用を最小化）。

---

## 開発上の注意・設計方針（抜粋）

- ルックアヘッドバイアスに配慮：内部で datetime.today() / date.today() を直接参照しない関数が多く、target_date を明示的に渡す設計。
- API 呼び出しはフェイルセーフ：LLM / 外部 API の失敗時は例外により全体を止めず、フォールバックやスキップで継続する設計（ログに警告を出す）。
- DuckDB に対する書き込みは冪等性を担保する（ON CONFLICT で更新）。
- ニュース収集では SSRF 対策、gzip サイズチェック、XML 攻撃対策（defusedxml）を実施。

---

## 貢献 / 変更案内

- テストを書く場合は各外部コール（OpenAI、HTTP、J-Quants）をモックしてください。モジュール内に差し替えポイント（例えば `_call_openai_api`）が用意されています。
- schema の変更や追加の ETL ジョブを作る際は既存の ETLResult / quality チェックと整合性を保つようにしてください。

---

README に記載のない詳細（API の戻り値フォーマット、DB スキーマ定義の細部など）は各モジュールのドキュメンテーション文字列を参照してください。必要であれば README に追加すべき項目（セットアップの自動化スクリプト・例 .env.example の具体的中身・デプロイ手順 等）を教えてください。