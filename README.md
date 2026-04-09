# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ群です。  
DuckDB を中心としたローカル DB、J-Quants からの ETL、ニュース収集・NLP（OpenAI）によるスコアリング、リサーチ用ファクター計算、監査ログ／発注トレーサビリティなどを提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・ページネーション対応、ID トークン自動リフレッシュ、レート制御・リトライ実装

- データ品質管理
  - 欠損・スパイク・重複・日付整合性チェック（quality モジュール）

- ニュース収集・NLP
  - RSS からニュース収集（SSRF/トラッキング防止、安全な XML パース）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（ai.score_news）
  - マクロニュース + ETF MA200 乖離を合成した市場レジーム判定（ai.score_regime）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算、将来リターン・IC 計算、Z スコア正規化

- 監査ログ（audit）
  - signal → order_request → execution を辿れる監査テーブルの初期化・管理（DuckDB）

- 設定管理
  - .env / 環境変数からの設定自動読み込み（プロジェクトルートを探索）。自動読み込みは無効化可。

---

## 動作前提（依存・推奨）

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, datetime, json, logging, sqlite3 など

（プロジェクト用途によりその他パッケージが必要になる場合あり）

---

## セットアップ手順

1. Python 仮想環境（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. パッケージをインストール
   必要最小パッケージをインストールします（pip の利用例）。
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意している場合はそちらを使ってください。

3. ソースをインストール（開発）
   プロジェクトルートで (例: src 配下をパッケージ化している場合)：
   ```bash
   pip install -e .
   ```

4. 環境変数設定
   プロジェクトルートの `.env` または `.env.local` に必要な設定を記述するか、OS 環境変数として設定します。
   自動ロードの優先順位: OS 環境変数 > .env.local > .env  
   自動ロードを無効化するには:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 必須／重要な環境変数

- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD      — kabuステーション API のパスワード（発注等で使用）
- OPENAI_API_KEY         — OpenAI を利用する場合に必要（news_nlp / regime_detector）
- （任意）LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（LINE）

設定例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

設定に関する注意:
- settings（kabusys.config.settings）経由でアクセスできます。必須変数が未設定だと ValueError を送出します。
- PAPER_FILL_MODE（paper trading 用挙動）: instant | partial | never | reject

---

## 主要な使い方（コード例）

以下は代表的なユースケースの呼び出し例です。DuckDB 接続は `duckdb.connect(path)` で作成します。

- 日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成（OpenAI API キー必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```

- 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへアクセスできます
```

- リサーチ関数（例: モメンタム計算）
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の dict のリスト
```

---

## よく使うモジュールと説明（抜粋）

- kabusys.config
  - Settings: 環境変数読み取りと検証。自動 .env ロード（プロジェクトルート基準）を行う。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。

- kabusys.data
  - jquants_client: J-Quants API とのやり取り、取得・保存ロジック（fetch_*, save_*）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl 等
  - quality: データ品質チェック
  - calendar_management: market_calendar を使った営業日判定ユーティリティ
  - audit: 監査ログテーブル（init_audit_schema / init_audit_db）
  - news_collector: RSS 収集、安全対策済み

- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime: ETF(1321) MA200 とマクロ記事の LLM スコアを合成して market_regime に書き込み

- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize を利用した標準化ユーティリティ

---

## ディレクトリ構成

（抜粋。実際はプロジェクトルートに src/、pyproject.toml 等が存在する想定です）

- src/kabusys/
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
    - quality.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - stats.py
    - pipeline.py
    - (その他 data 関連モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（補助）
  - ai/, data/, research/ 内にさらに細かな実装ファイルあり

---

## 運用上の注意 / トラブルシューティング

- 環境変数未設定エラー
  - settings の必須プロパティ（例: JQUANTS_REFRESH_TOKEN）が未設定だと ValueError が発生します。`.env.example` を参照して .env を用意してください。

- OpenAI 呼び出し
  - API 利用時は OPENAI_API_KEY を設定してください。API 側エラーや JSON パース失敗時はフェイルセーフで 0.0 を返す等の設計が一部にあります（ログに警告が出ます）。

- J-Quants API レート制御
  - モジュール内で 120 req/min の制限を守る実装があります。大量のリクエストを並列で投げるとレート不足や 429 が発生するため注意してください。

- DuckDB の executemany 空リスト制約
  - 一部実装で DuckDB (特に古いバージョン) の executemany に空リストを渡せないため事前チェックを行っています。問題が出た場合は duckdb パッケージのバージョンを確認してください。

---

## 開発・テスト

- 自動 .env 読み込みをテスト中に無効化するには
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出し部分は内部で分離されており、ユニットテスト時は関数をモックして置き換えるように設計されています（例: unittest.mock.patch で _call_openai_api を差し替え）。

---

必要であれば README に以下を追加できます:
- 具体的な .env.example（テンプレート）
- CI / GitHub Actions の設定例（ETL のスケジューリング）
- 詳細な API 使用例（jquants_client の fetch/save の挙動）
- ライセンス表記

追加してほしい項目があれば教えてください。