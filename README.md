# KabuSys

日本株向け自動売買 / データプラットフォームのライブラリ群です。  
ETL・データ品質チェック・ニュース収集・ニュースNLP（LLM）・市場レジーム判定・ファクター計算・監査ログなど、戦略開発と運用に必要なコンポーネントを持ちます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等の差分ETL
- DuckDB を用いたデータ格納と品質チェック
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント（ai_scores）と市場レジーム判定
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（signal → order_request → execution）用スキーマと初期化ユーティリティ

設計上の特徴：
- Look-ahead バイアスを避ける設計（内部で date.today() や datetime.today() を不用意に参照しない）
- DuckDB を中心とした軽量ローカルDB設計（ETL の冪等性・効率重視）
- 外部 API 呼び出しに対するリトライ・レート制御・フェイルセーフ処理

---

## 機能一覧

主要モジュールと提供機能（抜粋）:

- kabusys.config
  - .env 自動読み込み（プロジェクトルートの `.env`, `.env.local`）。環境変数経由の設定管理。
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL ヘルパー
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得・前処理・保存ロジック（SSRF 対策・XML 攻撃対策）
  - calendar_management: JPX カレンダーの管理・営業日判定・更新ジョブ
  - audit: 監査ログスキーマ作成・初期化ユーティリティ
  - stats: 汎用統計（Zスコア正規化）
- kabusys.ai
  - news_nlp.score_news: 指定日のニュースを集約して LLM でまとめて銘柄ごとにスコア化し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321) の MA とニュースセンチメントを合成して market_regime を生成
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提:
- Python 3.10 以上（コード内で | 型注釈等を使用）
- DuckDB, OpenAI SDK, defusedxml などが必要

例: 仮想環境の作成と依存パッケージのインストール

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール（最低限）
   - pip install duckdb openai defusedxml

   ※ 実際の運用で必要なパッケージは用途により増えます。プロジェクトに requirements.txt や pyproject.toml があればそちらを使用してください。

3. パッケージをローカル開発インストール（任意）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数（主なものを下に示します。必要に応じて設定してください）:

     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / regime_detector のデフォルト）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_FILL_MODE — paper trading のモード ("instant", "partial", "never", "reject")
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - PID_FILE_PATH / KILL_FLAG_PATH など監視設定
     - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト "development"）
     - LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト "INFO"）

---

## 使い方（サンプル）

以下は主要な操作の簡単な例です。実際はログ設定やエラーハンドリングを追加してください。

- DuckDB 接続を用意して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} scores")
```

- 市場レジーム判定（regime）を実行する

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB の初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで監査ログテーブルが作成されます
```

- リサーチ用ファクター計算例

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

注意点:
- OpenAI API を利用する関数は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- 多くの関数は DuckDB 上の期待スキーマ（テーブル）を前提としています。初回は ETL を走らせてスキーマとデータを用意してください。

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ニュースNLP・レジーム判定で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- PAPER_FILL_MODE: Paper Trading の執行モード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）
- KABUSYS_ENV: environment（development|paper_trading|live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: true にすると .env 自動ロードを無効化

（設定項目は kabusys.config.Settings で参照でき、各プロパティにデフォルトやバリデーションが定義されています）

---

## ディレクトリ構成

主要ソースファイルのツリー（抜粋）

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
    - stats.py
    - news_collector.py
    - calendar_management.py
    - audit.py
    - pipeline.py
    - etl.py
    - (その他 data 関連モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/ (LLM 関連)
  - research/ (リサーチ/ファクター)
  - data/ (ETL、品質管理、外部APIクライアント、監査ログ等)

ファイルごとの主な責務は各ファイルの冒頭 docstring に詳細が記載されています（例: news_collector.py、jquants_client.py、pipeline.py など）。

---

## 運用上の注意

- ETL / API 呼び出しにはレート制御・リトライが実装されていますが、運用時は API キーやレート制限を考慮してジョブ頻度を設定してください。
- DuckDB のスキーマは ETL と監査初期化ルーチンで作成されます。既存スキーマと衝突する場合はバックアップを取ってから実行してください。
- LLM 呼び出し（OpenAI）はコストが掛かります。ローカルでのテスト時はモック（unittest.mock.patch）で _call_openai_api 等を差し替える設計になっています。
- news_collector は外部 RSS を取得するため SSRF/XML 攻撃対策を実装していますが、運用時には対象ソースの監視とソースリストの管理を行ってください。

---

必要であれば、README に含めるサンプル .env.example、テーブルスキーマ（DDL）、または具体的な CLI / systemd unit の例なども作成できます。どの情報を追加しますか？