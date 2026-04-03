# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
EDV（ETL）、ニュースNLP、ファクター研究、監査ログ、カレンダー管理、J-Quants / kabuステーション クライアントなど、トレード・リサーチ・データ基盤に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主な特長（機能一覧）

- データETL
  - J-Quants API からの株価（OHLCV）・財務・カレンダーの差分取得と DuckDB への冪等保存
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 日次 ETL パイプライン（run_daily_etl）
- ニュース収集 / NLP
  - RSS 取得・前処理（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメントスコアリング（score_news）
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成した日次レジーム判定（score_regime）
- リサーチ支援
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC 計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査テーブルの初期化・管理（init_audit_schema / init_audit_db）
- 市場カレンダー管理
  - JPX カレンダーの取得・保存、営業日判定・前後営業日の取得ユーティリティ
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings 抽象（kabusys.config）

---

## 必要条件（推奨）

- Python 3.10+
- 必要パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

（プロジェクト用途により他パッケージが必要になる場合があります。setup/pyproject がある場合はそれに従ってください）

例（仮想環境でのインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# またはプロジェクトの pyproject / requirements.txt があればそちらを利用
```

---

## 環境変数 / .env

kabusys は起動時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: リソース監視閾値
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

簡単な `.env` の例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカルで動かす / 開発用）

1. リポジトリをクローンして移動
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトの requirements / pyproject を利用
   ```

4. `.env` を用意（上記参照）。プロジェクトルートに配置すると自動で読み込まれます。

5. DuckDB 用ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼び出す想定の使用例です。

- DuckDB 接続を用意して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使う場合:
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

# 当日分の ETL を実行（引数 target_date を指定して過去日を処理可）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（AI: OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key=None → OPENAI_API_KEY を参照
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査 DB を初期化（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

- 監査スキーマのみ既存接続に追加
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。API キーを環境変数 OPENAI_API_KEY に設定してください（または api_key 引数で明示）。
- ETL 系は J-Quants のトークンが必要です（JQUANTS_REFRESH_TOKEN を .env に設定）。

---

## よくある操作 / ヒント

- 自動 .env ロードを無効化したい（テストなど）:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

- ログレベルを変更する:
  ```bash
  export LOG_LEVEL=DEBUG
  ```

- DuckDB パスを変更する:
  ```bash
  export DUCKDB_PATH=/path/to/kabusys.duckdb
  ```

---

## ディレクトリ構成（コードの概観）

以下は主要モジュールと役割の一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・Settings 管理、.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約と OpenAI による銘柄別センチメント評価（score_news）
    - regime_detector.py
      - ETF MA200 乖離とマクロニュースを合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、データ取得・保存ロジック
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得 / 前処理 / raw_news への保存ロジック
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - calendar_management.py
      - 市場カレンダー管理（営業日判定、calendar_update_job）
    - audit.py
      - 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - ai/（上記）
  - research/（上記）
  - その他モジュール群（strategy / execution / monitoring 等は package export の対象になっているがここに含める）

---

## 開発・拡張のためのメモ

- DuckDB を前提に SQL と Python を組み合わせた実装が多く、テスト時は in-memory 接続（":memory:"）を使うと便利です。
- ニュース収集・OpenAI 呼び出し部分は外部依存があるため、ユニットテストでは該当関数を patch / mock する設計（既に各モジュールで差し替えを想定した内部関数名が使われています）。
- Look-ahead Bias を避けるため、多くの関数は内部で datetime.today() を参照しない設計になっています（target_date を明示する形）。

---

この README は現在のソースコードベース（src/kabusys）に基づいて作成しています。実際のリポジトリに pyproject.toml / setup.py / requirements.txt がある場合は、それに従って依存関係とインストール手順を調整してください。何か追加したい情報（CLI、サンプルデータ、運用手順など）があれば教えてください。