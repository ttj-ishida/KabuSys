# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（監査テーブル初期化）などを統合的に提供します。

---

## 概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API から株価・財務・カレンダーデータを安全に取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と前処理、OpenAI を用いた銘柄別ニュースセンチメントの自動スコアリング
- ETF の移動平均乖離とマクロニュースの LLM センチメントを合成した「市場レジーム判定」
- リサーチ用のファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 注文→約定に至るフローをトレース可能にする監査テーブル初期化ユーティリティ

設計上の特徴として、バックテスト等でのルックアヘッドバイアス防止、API リトライやレート制御、SSRF 対策、冪等性（INSERT ON CONFLICT）などに配慮しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースNLP（score_news: 銘柄ごとのニュースセンチメント算出）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロセンチメントを合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み・管理（Settings クラス、.env 自動ロード機能）

---

## 必要条件 / 依存パッケージ

（プロジェクトの setup / pyproject.toml によるが、主に以下を使用します）

- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- 標準ライブラリ（urllib, json, logging など）

例（pip）:
```
pip install duckdb openai defusedxml
```

---

## 環境変数

設定は環境変数（またはルートの .env / .env.local）から読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数:

- JQUANTS_REFRESH_TOKEN  (必須)  — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD       (必須)  — kabuステーション API のパスワード
- KABU_API_BASE_URL       (任意)  — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN         (必須)  — Slack 通知用
- SLACK_CHANNEL_ID        (必須)  — Slack 通知用チャンネル ID
- DUCKDB_PATH             (任意)  — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH             (任意)  — SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV             (任意)  — one of: development, paper_trading, live (デフォルト development)
- LOG_LEVEL               (任意)  — "DEBUG","INFO","WARNING","ERROR","CRITICAL"（デフォルト INFO）
- OPENAI_API_KEY          (必須 for AI 機能) — OpenAI API キー（score_news / score_regime で参照）

.env の読み込みルール:
- プロジェクトルートの `.env` をまず読み、続けて `.env.local` を上書きで読み込みます。
- OS 環境変数が優先されます。
- `.env` ファイルのパースはシェル風（export 付き、クォート、コメント）に対応します。

---

## セットアップ手順

1. リポジトリをクローン
```
git clone <repo-url>
cd <repo>
```

2. Python 仮想環境を作成・有効化（任意）
```
python -m venv .venv
source .venv/bin/activate
```

3. 依存パッケージをインストール
```
pip install -r requirements.txt
# または最低限
pip install duckdb openai defusedxml
```

4. 環境変数を設定
- ルートに `.env`（と必要なら `.env.local`）を作成して上記の必須変数を設定するか、シェル環境にエクスポートしてください。
- 例: `.env`
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

5. DuckDB 初期スキーマ（必要に応じて）を用意する  
データテーブル / raw_* / market_calendar / ai_scores などは ETL 実行や監査初期化時に作成されるか、別途 schema 初期化関数を提供している場合はそれを呼んでください（このコードベースでは ETL / audit 初期化関数を通じて作成します）。

---

## 使い方（基本例）

以下は Python スクリプトまたは REPL で使う代表例です。いずれも duckdb の接続オブジェクト（duckdb.connect(...)）を渡して操作します。

- ETL（日次パイプライン）を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成（score_news）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_scores = score_news(conn, target_date=date(2026, 3, 20))
print(f"Scored {n_scores} tickers")
```
score_news は内部で OpenAI API (gpt-4o-mini) を呼びます。api_key を明示する場合は第3引数にキーを渡せます。

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY または api_key 引数が必要
```

- 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これにより監査テーブル（signal_events, order_requests, executions 等）が作成されます
```

- ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの dict のリスト
```

---

## 注意点 / 運用上のポイント

- OpenAI / J-Quants API の呼び出しにはそれぞれキーが必要です。テスト環境ではモック化して呼び出しを置き換えてください。
- AI モジュールは API レスポンスの不正や接続エラー時にフェイルセーフ動作（デフォルト値）を取るよう設計されていますが、API 利用料やレート制限は運用で管理してください。
- .env 自動ロードはプロジェクトルートを探索して行います（.git または pyproject.toml を基準）。CI 等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すと例外になるバージョン（0.10 等）があるため、コードは空チェックを行った上で executemany を呼んでいます。DuckDB バージョン依存に注意してください。
- RSS 取得は SSRF 対策・サイズ制限・gzip 解凍後のサイズチェック等を備えていますが、RSS ソースは信頼できるものを利用してください。

---

## ディレクトリ構成

（抜粋、主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント処理（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & 保存関数
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL 結果型の再エクスポート
    - news_collector.py              — RSS ニュース収集
    - calendar_management.py         — 市場カレンダー管理
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum, value, volatility）
    - feature_exploration.py         — 将来リターン / IC / summary
  - research/... (他ユーティリティ)
- pyproject.toml / setup.cfg (パッケージ設定がある場合)

---

## 開発・テストについて

- AI / ネットワーク関係の関数は外部 API 呼び出しの依存を避けるため、テスト時にモック化（unittest.mock.patch）する設計になっています。例: kabusys.ai.news_nlp._call_openai_api を差し替えてテストしてください。
- .env 読み込みは自動ですが、ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして明示的に設定を注入することを推奨します。

---

もし README に追加してほしい項目（例: CLI コマンド、より詳細なスキーマ定義、CI 設定例、運用手順書など）があれば教えてください。必要に応じてサンプルスクリプトや .env.example も作成します。