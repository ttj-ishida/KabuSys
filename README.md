# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリ群です。J-Quants や RSS、OpenAI（LLM）を活用してデータ収集（ETL）、品質チェック、ファクター計算、ニュース NLP、マーケット・レジーム判定、監査ログなどの機能を提供します。

主な設計方針は「バックテストでのルックアヘッドバイアス防止」「DuckDB を中心としたローカルデータ管理」「API 呼び出しの堅牢なリトライ制御」「ETL の冪等性・品質チェック」です。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得用 Settings クラス（kabusys.config.settings）

- データ ETL（J-Quants）
  - 株価日足（raw_prices）取得・保存（fetch / save）
  - 財務データ（raw_financials）取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分更新・バックフィル・ページネーション対応
  - レート制御（120 req/min）・リトライロジック

- データ品質チェック
  - 欠損（OHLC）・スパイク検出・重複・日付整合性チェック
  - QualityIssue オブジェクトで集約

- ニュース収集 / 前処理
  - RSS 取得（SSRF 対策・トラッキング除去・サイズ制限）
  - raw_news に冪等保存、news_symbols との紐付け想定

- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に投げ、ai_scores にスコアを書き込み
  - バッチ/チャンク処理、堅牢なリトライ・バリデーション

- 市場レジーム判定（AI + ETF MA）
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM 評価を合成して
    daily に market_regime を計算・保存

- 研究（Research）
  - ファクター算出（モメンタム/バリュー/ボラティリティ）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z-score 正規化

- 監査ログ（Audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - 発注フローのトレーサビリティを UUID 階層で確保

---

## セットアップ

前提
- Python 3.10 以上（型注釈で `X | None` などを使用）
- DuckDB を使います（pip パッケージ duckdb）
- OpenAI（LLM）を用いる機能は openai パッケージに依存
- RSS 処理で defusedxml を使用

例: 仮想環境作成と依存インストール（プロジェクト配下に requirements.txt がある場合はそちらを使う）
```
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 必要に応じて他の依存を追加
```

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動読み込みします（OS 環境変数が優先）。
- 自動ロードを無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 主要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (LLM 機能を使う場合は必須)
  - KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) - デフォルト: INFO
  - DUCKDB_PATH - デフォルト: data/kabusys.duckdb
  - SQLITE_PATH - デフォルト: data/monitoring.db
  - PID_FILE_PATH, KILL_FLAG_PATH, その他監視設定

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下のコード例は、DuckDB に接続して日次 ETL を実行したり、ニューススコアリングやレジーム判定を行うシンプルな使用例です。

共通準備:
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクトを返します
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象になります（内部で営業日に調整）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング（ai_scores テーブルへ書き込み）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で渡せます
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに結果が保存されます
```

4) 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.kabusys.duckdb")
# テーブルが作成されます
```

5) 研究系ファクター計算（Research）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の dict のリストです
```

logging 設定
- settings.log_level でログレベルが検証されます。アプリケーション側で logging.basicConfig(level=settings.log_level) 等を設定して下さい。

注意点
- LLM / OpenAI の呼び出しは API キーを必要とします。API キーは引数で渡すことも可能です（テスト時の差し替えやモック化が容易）。
- 日付処理はバックテスト向けにルックアヘッドを避ける実装になっています（内部で date.today() を参照しない、クエリで < target_date 等を使う等）。
- ETL の save / fetch 関数は冪等になる（ON CONFLICT DO UPDATE）ので繰り返し実行しても安全です。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソースは `src/kabusys` 以下に配置されています。主要モジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                   -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py               -- ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        -- 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py         -- J-Quants API クライアント & DuckDB 保存
    - pipeline.py               -- ETL パイプライン（run_daily_etl など）
    - etl.py                    -- ETLResult エクスポート
    - calendar_management.py    -- 市場カレンダーのユーティリティ
    - news_collector.py         -- RSS 収集・前処理
    - quality.py                -- データ品質チェック
    - stats.py                  -- 統計ユーティリティ（zscore）
    - audit.py                  -- 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py        -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py    -- 将来リターン、IC、統計サマリー

---

## 開発・テスト時のヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。テスト環境で自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しや外部 API はモック化しやすい設計（関数分離、内部の _call_openai_api を patch 可能）になっています。pytest 等で簡単にテスト可能です。
- DuckDB の一時 DB を使う場合は `":memory:"` を指定できます（例: init_audit_db(":memory:")）。

---

## ライセンス / 貢献

（ここにライセンス情報や貢献方法を記載してください。リポジトリのポリシーに従って追記してください。）

---

この README はコードベースの現在実装に基づき作成しています。追加の実行スクリプトや CLI、CI 設定がある場合は適宜 README を更新してください。