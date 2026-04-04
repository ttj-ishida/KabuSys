# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ、マーケットカレンダー管理など、戦略・研究・実運用に必要な機能群を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（サンプル）
- 環境変数（主要）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的とした Python ライブラリです。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL と保存（DuckDB）
- RSS ニュースの収集と前処理 / 銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリューなど）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査（信号→発注→約定）用スキーマ初期化ユーティリティ
- 市場カレンダー管理（JPX）と営業日ユーティリティ

設計方針として、バックテストでのルックアヘッドバイアスを避ける実装、DuckDB を利用した高速なローカル処理、外部 API 呼び出しの堅牢なリトライ・エラーハンドリングを重視しています。

---

## 機能一覧

主要モジュールと提供機能（抜粋）:

- kabusys.config
  - .env/.env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数取得補助（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API ラッパー（取得 + DuckDB 保存 + レート制御 + リトライ）
  - pipeline: 日次 ETL のエントリ（run_daily_etl 等）
  - news_collector: RSS 取得、前処理、raw_news への保存
  - news_nlp: OpenAI で銘柄別ニューススコアを算出（score_news）
  - regime_detector: マクロ + ETF MA で市場レジーム判定（score_regime）
  - quality: データ品質チェック（check_missing_data, check_spike, ...）
  - calendar_management: 営業日の判定／next/prev/get_trading_days、calendar_update_job
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.ai
  - score_news（ニュースセンチメント）, score_regime（市場レジーム）

---

## セットアップ手順

前提
- Python >= 3.10（typing の代替構文や型ヒントのため）
- pip が利用可能

インストール（開発環境での例）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 必要な外部パッケージ（主なもの）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください:
     ```
     pip install -e .
     ```

環境変数設定
- プロジェクトルート（.git または pyproject.toml のある場所）に `.env` または `.env.local` を置くと自動で読み込まれます。
- 自動ロードを無効化するには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  （または Windows の環境変数設定）

DuckDB
- デフォルトの DuckDB ファイルパスは `data/kabusys.duckdb`（settings.duckdb_path）
- 監査用 DB は `settings.sqlite_path` など別パスを使用可能

---

## 主要環境変数（例）

このプロジェクトで使う主な環境変数（.env に設定）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション等のパスワード
- KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: environment (development | paper_trading | live) - 有効な値: development, paper_trading, live
- LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

注意: settings オブジェクト（kabusys.config.settings）でこれらを安全に参照できます。必須変数未設定時は例外が投げられます。

---

## 簡単な使い方 / サンプル

以下はコードから主要処理を呼ぶ際の簡単な例です。実行前に .env を用意しておいてください。

1) DuckDB 接続を作成して ETL を実行（日次 ETL）

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 19))
print(result.to_dict())
```

2) ニュースセンチメントスコア（指定日）を生成

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 19))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

3) 市場レジーム（マクロ + ETF MA）を判定して保存

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19))
```

4) 監査テーブル初期化（監査DBを別途作る）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

5) 研究用ファクター計算の例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 19))
# records は各銘柄ごとの辞書のリスト
```

---

## 注意点 / 実運用での留意事項

- OpenAI 呼び出しは API エラー時にフォールバックやリトライロジックを持ちますが、API キー・料金には注意してください。
- J-Quants API はレート制限（120 req/min）を守るためモジュール側でスロットリングします。ID トークンの自動リフレッシュに対応しています。
- DuckDB の executemany はバージョン差分による挙動差があるため、空リストバインドを避ける実装がなされています。
- バックテストでは Look-ahead Bias に注意してください。関数の多くは target_date に対して過去データのみを参照するよう配慮されています（datetime.today() を直接参照しない設計）。

---

## ディレクトリ構成

リポジトリの主要ファイル / モジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュースNLP（score_news）
    - regime_detector.py             -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（fetch/save）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETLResult の再エクスポート
    - calendar_management.py         -- マーケットカレンダー管理
    - news_collector.py              -- RSS ニュース収集
    - quality.py                     -- データ品質チェック
    - stats.py                       -- zscore_normalize 等
    - audit.py                       -- 監査スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             -- ファクター計算
    - feature_exploration.py         -- 将来リターン / IC / 統計サマリー
  - ai/ (前述)
  - research/ (前述)

細かい実装や API 仕様は各モジュールの docstring を参照してください。

---

## 最後に

この README はコードベースの主要機能と簡単な使い方をまとめたものです。各モジュールには詳細な docstring と使用上の注意が含まれています。実運用を行う場合は、.env の保護、API キー管理、監視・アラート設定、そしてバックテストにおけるデータ整合性（Look-ahead の防止）に十分注意してください。

不明点があれば、どの機能についてさらに詳しく知りたいか教えてください。README の例や起動スクリプト、.env.example のテンプレートなども作成できます。