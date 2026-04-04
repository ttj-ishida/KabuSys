# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・AIセンチメント分析、リサーチ用ファクター計算、監査ログ（発注〜約定トレーサビリティ）、市場カレンダー管理などを提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得 / ETL
  - J-Quants API から株価（日次 OHLCV）・財務データ・JPX マーケットカレンダーを差分取得して DuckDB に保存
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集 / NLP
  - RSS フィードから記事を収集して raw_news テーブルへ保存
  - OpenAI（gpt-4o-mini）を利用した銘柄別ニュースセンチメント（ai_scores）生成（score_news）

- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを組み合わせて日次の市場レジームを算出（score_regime）

- リサーチ / ファクター計算
  - Momentum / Value / Volatility / Liquidity 等の定量ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化

- カレンダー管理
  - market_calendar テーブルを元に営業日判定・前後営業日取得・期間内営業日取得
  - J-Quants からのカレンダー差分更新ジョブ（calendar_update_job）

- 監査（Audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティを UUID で連鎖

- 設定管理
  - .env / .env.local / OS 環境変数から設定を自動ロード（プロジェクトルートを基準に検索）
  - settings オブジェクトでアクセス（例: settings.jquants_refresh_token）

---

## 必要条件

- Python 3.10 以上（型ヒントに `X | None` を使っているため）
- 主な外部パッケージ:
  - duckdb
  - openai
  - defusedxml

（実行環境に応じて追加パッケージが必要になる場合があります：urllib, json 等は標準ライブラリです）

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※プロジェクトがパッケージ化されている場合:
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` および（必要なら）`.env.local` を作成すると、パッケージインポート時に自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime などで使用）
   - KABU_API_PASSWORD     : kabuステーション API 用パスワード
   - （任意）KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH など

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pass
DUCKDB_PATH=data/kabusys.duckdb
```

settings はプロパティアクセスで使えます（例: settings.duckdb_path は Path オブジェクトを返す）。

---

## 使い方（抜粋・サンプル）

前提: DuckDB 接続を利用する関数が多いため、まず接続を作成します。

例: DuckDB 接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント生成（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数にセットするか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

# API キーを明示的に与えるか、環境変数 OPENAI_API_KEY を設定
score_regime(conn, target_date=date(2026, 3, 20))
```

4) リサーチ関数の利用（例: モメンタム計算）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
```

5) 監査スキーマ初期化 / 監査 DB 作成
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで audit_conn に監査用テーブルが作成されています
```

---

## 設定項目一覧（主なもの）

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)

- OpenAI / 通知
  - OPENAI_API_KEY (score_news / score_regime で使用可能)
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID

- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START

- 監視しきい値
  - CPU_THRESHOLD_PCT (デフォルト 90.0)
  - MEMORY_THRESHOLD_PCT (デフォルト 85.0)
  - DISK_THRESHOLD_PCT (デフォルト 90.0)

- 環境
  - KABUSYS_ENV: development | paper_trading | live （必須ではないが妥当な値を設定）

注意: settings のプロパティは未設定の必須値があると ValueError を投げます。`.env.example` を参考に `.env` を用意してください。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュールとファイルの配置（src/kabusys/ 以下）です。実際のリポジトリ構成に応じて、テストやスクリプト等が別途存在する場合があります。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py (ETL インターフェース再エクスポート)
    - jquants_client.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの責務（要約）
- config.py: .env / 環境変数の読み込みと settings オブジェクト
- data/jquants_client.py: J-Quants API との通信・保存ユーティリティ
- data/pipeline.py: 差分ETL と日次 ETL エントリポイント（run_daily_etl）
- data/news_collector.py: RSS→raw_news 保存
- ai/news_nlp.py: ニュースを LLM でスコアリングして ai_scores に書き込む
- ai/regime_detector.py: マクロセンチメント＋MA200 で市場レジーム判定
- research/*: ファクター計算・特徴量解析ユーティリティ
- data/audit.py: 監査テーブル DDL / 初期化

---

## 運用上の注意 / 設計上のポイント

- Look-ahead bias を避ける設計が至る所に取り入れられています（target_date 未満のデータのみを参照、datetime.today() を直接使わない等）。
- OpenAI 呼び出しはエラーハンドリング・リトライ・フォールバック（失敗時は中立スコア 0.0）を備えています。API キーは env で管理するか、関数に明示的に渡してください。
- J-Quants API はレート制限に配慮した RateLimiter とリトライロジックを備えています。401 はトークン自動リフレッシュを行います。
- DuckDB に対する複数行挿入や executemany の仕様（空リスト不可など）に注意した実装になっています。
- ニュース収集では SSRF 対策（スキーム検証、プライベート IP 排除、リダイレクト検査）や XML パースの安全化（defusedxml）を行っています。

---

## さらに知っておくと良いこと

- settings の自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に探索します。テスト等で自動読み込みを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はテスト容易性のため内部 API 呼び出し関数を差し替え（モック）可能になるよう実装されています（例: unittest.mock.patch で _call_openai_api を差し替え）。
- DuckDB のスキーマ作成や audit DB 初期化は冪等で実行できる設計です。既存データの保護を念頭に置いたロジック（部分的失敗時の保護）があります。

---

README はここまでです。特定の機能の詳細な使い方・API サンプルやテスト方法、CI 設定などが必要であれば、その項目を指定してください。