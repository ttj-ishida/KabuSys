# KabuSys

日本株向けの自動売買 / データ基盤ライブラリセットです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAIによるセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注トレース）などを含むモジュール群を提供します。

---

## 主要な特徴（概要）

- J-Quants API からの差分 ETL（株価日足 / 財務 / カレンダー）と DuckDB への冪等保存
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS） → raw_news 保存、銘柄紐付け
- ニュースに対する LLM ベースのセンチメント解析（gpt-4o-mini）
- 市場レジーム判定（ETF 1321 の 200 日 MA とマクロニュースの合成）
- リサーチ用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と統計ユーティリティ
- 監査ログスキーマ（signal → order_request → execution の完全トレーサビリティ）
- 設定管理（.env の自動読み込み、環境変数アクセス用 Settings）

---

## 機能一覧（モジュールと主な API）

- kabusys.config
  - settings: 環境変数から設定取得（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可能）
- kabusys.data
  - pipeline.run_daily_etl(conn, target_date, ...): 日次 ETL パイプライン
  - jquants_client.fetch_* / save_*: J-Quants との通信および DuckDB 保存
  - news_collector.fetch_rss(...), preprocess_text(...)
  - quality.run_all_checks(conn, ...): データ品質チェック群
  - calendar_management: 営業日判定、次/前営業日取得、calendar_update_job
  - audit.init_audit_db / init_audit_schema: 監査ログ DB 初期化
  - stats.zscore_normalize: Zスコア正規化ユーティリティ
- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None): 市場レジーム（bull/neutral/bear）を market_regime テーブルへ保存
- kabusys.research
  - calc_momentum / calc_volatility / calc_value: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank: 特徴量探索・評価

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）
- J-Quants リフレッシュトークン、OpenAI API キー等の環境変数

（プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

---

## セットアップ

1. リポジトリをクローン / 取得
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. インストール
   - プロジェクトが pyproject.toml を持つ場合:
     - pip install -e .
   - 必要最低限のパッケージを直接インストールする場合:
     - pip install duckdb openai defusedxml
4. 環境変数設定（.env）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: `.env` の内容（最低限必要なキー）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_station_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易例）

- DuckDB 接続を取得して ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
# conn は DuckDB 接続（raw_news / news_symbols / ai_scores が利用可能であること）
n_written = score_news(conn, date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
# conn は DuckDB 接続（prices_daily / raw_news / market_regime が利用可能であること）
score_regime(conn, date(2026, 3, 20))
```

- 監査ログ DB を初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルへ記録可能
```

- リサーチ関数の使用例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

自動.env読み込みを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 注意事項 / 設計方針（抜粋）

- ルックアヘッドバイアスを防ぐため、各モジュールは内部で date.today() を無条件に参照せず、関数に target_date を明示的に渡す設計になっています。
- LLM や外部 API 呼び出しはリトライ・フォールバック（失敗時はスコア 0 やスキップ）を備えたフェイルセーフ実装になっています。
- J-Quants クライアントはレート制限（120 req/min）遵守のため内部でスロットリングしています。
- DuckDB への書き込みは可能な限り冪等（ON CONFLICT）として設計されています。
- ニュース収集は SSRF 対策、受信サイズ制限、XML パースの安全処理を行っています。

---

## ディレクトリ構成（抜粋）

（プロジェクトの src/ 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py       — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch/save）
    - pipeline.py              — ETL パイプライン (run_daily_etl など)
    - etl.py                   — ETLResult 再エクスポート
    - news_collector.py        — RSS 取得・前処理
    - calendar_management.py   — 市場カレンダー・営業日ロジック
    - quality.py               — データ品質チェック
    - stats.py                 — 統計ユーティリティ (zscore_normalize)
    - audit.py                 — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py       — モメンタム / ボラティリティ / バリュー
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - research/... (その他の補助モジュール)

---

## 開発 / テストについて

- テストは各関数へのユニットテストでモックを使うことが想定されています（例: OpenAI 呼び出しは _call_openai_api をモック可能）。
- 自動 .env 読み込みが邪魔になるテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

不明点や README に追加したいサンプル（例: CI / デプロイ手順、DB スキーマ初期化スクリプト等）があれば教えてください。README内容をさらに詳しく拡張できます。