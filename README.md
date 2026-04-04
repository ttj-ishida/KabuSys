# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL・データ品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログなど、取引システム／リサーチ環境に必要な共通機能を提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存関係
- セットアップ手順
- 環境変数（.env）の例
- 使い方（サンプル）
  - ETL 実行（run_daily_etl）
  - ニュース NLP スコア（score_news）
  - 市場レジーム判定（score_regime）
  - 監査DB初期化（init_audit_db）
- ディレクトリ構成
- 補足（設計方針・注意点）

---

## プロジェクト概要
KabuSys は日本株の自動売買/リサーチ基盤向けユーティリティ群です。  
主に以下を目的としています：
- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いた ETL / 永続化
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュースを用いた銘柄ごとの NLP スコアリング（OpenAI 使用）
- 市場レジーム（bull/neutral/bear）判定（ETF + LLM 合成）
- ファクター計算 / 研究用ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）

設計では「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時の安全なフォールバック）」を重視しています。

---

## 機能一覧
- data:
  - J-Quants クライアント（fetch/save）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS の取得・前処理・保存）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査テーブル初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai:
  - ニュース NLP（score_news）: gpt-4o-mini を用いた銘柄別センチメント算出
  - レジーム検知（score_regime）: ETF(1321)のMAとニュースセンチメントを合成
- research:
  - ファクター計算（momentum / value / volatility 等）
  - 特徴量探索（forward returns, IC, summary 等）
- config:
  - .env / 環境変数の自動読込と Settings オブジェクト
- audit:
  - 監査ログ（signal_events, order_requests, executions）DDL と初期化

---

## 前提条件 / 依存関係
- Python >= 3.10
- 必須パッケージ（代表）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging などを多用します。

インストール例:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発時）:
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m pip install -e .
   ```
   （`src/` 配下にパッケージがあるため、開発インストールを推奨します）

2. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）:
   - 必須: JQUANTS_REFRESH_TOKEN
   - OpenAI を使う場合: OPENAI_API_KEY
   - 監視やローカル実行で使う環境変数: KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH など

3. DuckDB ファイル用ディレクトリを準備（デフォルトは data/kabusys.duckdb）:
   ```bash
   mkdir -p data
   ```

4. logging レベルやその他設定は環境変数（LOG_LEVEL, KABUSYS_ENV など）で調整可能。

---

## 環境変数（.env）の例
以下は代表的な環境変数の例（.env に配置）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# kabuステーション API (必要に応じて)
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# DBパス
DUCKDB_PATH=data/kabusys.duckdb

# システム
KABUSYS_ENV=development
LOG_LEVEL=INFO

# 自動 env ロードを無効化したい場合
# KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

注意: settings オブジェクトは自動で .env / .env.local を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを止めてください。

---

## 使い方（サンプル）

以下は主要な公開 API の使い方例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

- 共通インポート例:
```python
import duckdb
from kabusys.config import settings
```

### 1) 日次 ETL を実行する
ETL は J-Quants から差分をフェッチして DuckDB に保存し、品質チェックまで行います。

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

run_daily_etl は ETLResult を返します。エラー・品質問題は result.quality_issues / result.errors に格納されます。

### 2) ニュース NLP スコアを生成する（銘柄ごとの ai_score）
OpenAI API を使ってニュースをスコア化します。事前に raw_news と news_symbols が DB に存在する必要があります。

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {written} codes")
```

api_key を明示的に渡すこともできます（score_news(..., api_key="sk-...")）。未設定の場合は環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出します。

### 3) 市場レジーム判定
ETF(1321) の MA 乖離とニュースセンチメントを組み合わせて日次レジームを market_regime テーブルへ書き込みます。

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026, 3, 20))
print("done", res)
```

OpenAI の API キーは score_regime の引数または環境変数 OPENAI_API_KEY を使用します。API の失敗は macro_sentiment を 0.0 としてフォールバックします（フェイルセーフ）。

### 4) 監査ログ用 DB 初期化
監査テーブル（signal_events / order_requests / executions）を DuckDB に作成します。

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring.duckdb")
# 以降 conn を用いて audit テーブルを利用できます
```

init_audit_db はタイムゾーンを UTC に固定し、DDL を冪等的に作成します。

---

## ディレクトリ構成（主要ファイル）
（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & 保存関数
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult の再エクスポート
    - calendar_management.py— カレンダー管理（is_trading_day 等）
    - news_collector.py     — RSS 収集・前処理
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログ DDL / 初期化
    - stats.py              — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン / IC / サマリー / rank
  - ai/, research/ はそれぞれ研究・AI 機能を提供
  - （strategy/ execution/ monitoring モジュールは __all__ に含まれていますが、本リストのファイル群に応じて別途実装されます）

---

## 補足（設計方針・注意点）
- ルックアヘッドバイアス対策:
  - モジュールは内部で datetime.today() / date.today() を直接参照しないよう設計されており、必ず target_date を外部から渡すことを想定しています（ETL や scoring でも同様）。
- 冪等性:
  - DB への保存は ON CONFLICT DO UPDATE や INSERT ... DO NOTHING などで冪等に動作します。
- フェイルセーフ:
  - LLM / API 呼び出し失敗はスコアを 0 にフォールバックする等、処理を継続する設計です。ただし重大な DB 書き込み失敗は例外として上位へ伝搬します。
- テスト:
  - OpenAI / ネットワーク呼び出し箇所は簡単にモック可能な設計（_call_openai_api の差し替え等）になっています。
- セキュリティ:
  - RSS 収集では SSRF 対策、XML の defusedxml 使用、レスポンスサイズ制限等を実装しています。
- 環境変数読み込み:
  - config.Settings は .env/.env.local の自動読込を行います（プロジェクトルートは .git または pyproject.toml を基準に探索）。テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要であれば、README に「API リファレンス」「DB スキーマ定義」「運用手順（cron / systemd 例）」「CI/CD 設定」などの詳細を追加します。どの項目を優先して拡張しますか？