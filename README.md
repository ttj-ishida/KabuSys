# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL、ニュース収集、LLM を用いたニュースセンチメント、マーケットレジーム判定、研究用ファクター計算、監査ログなどを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 要件
- セットアップ手順
- 環境変数（.env）と自動ロード
- 使い方（代表的な API）
- ディレクトリ構成
- 開発ノート / 注意事項

---

## プロジェクト概要

KabuSys は日本株のデータ基盤と自動売買のための共通ライブラリ群です。J-Quants API や RSS を用いたニュース収集、DuckDB によるデータ格納、OpenAI を用いたニュースセンチメント・市場レジーム判定、ファクター計算、品質チェック、監査ログなどを包括的に提供します。

設計方針の一部:
- ルックアヘッドバイアスを避ける（関数内部で date.today() を不用意に参照しない設計）
- ETL は差分更新かつ冪等（ON CONFLICT / UPDATE）で安全に実行
- 外部 API 呼び出しはリトライ・レート制御を実装しフェイルセーフを採用

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価（OHLCV）/ 財務 / 上場情報 / カレンダー取得（ページネーション対応、トークン自動リフレッシュ、レート制御）
  - 日次 ETL（run_daily_etl）でカレンダー→株価→財務→品質チェックを順に実行
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue）
- ニュース収集
  - RSS から記事収集・前処理・raw_news への保存
  - SSRF 対策、サイズ上限、トラッキング除去などの防御実装
- NLP（OpenAI）
  - ニュースを銘柄別に集約して LLM でセンチメント（score_news）
  - マクロニュース + ETF MA を使ったマーケットレジーム判定（score_regime）
- 研究用ユーティリティ
  - Momentum / Value / Volatility 等ファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- 監査ログ（オーダー / シグナルのトレーサビリティ）
  - signal_events, order_requests, executions などの監査テーブル初期化ユーティリティ

---

## 要件

- Python 3.10 以上（型アノテーションで | 演算子等を使用）
- 推奨パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging など）

（プロジェクトに requirements.txt があればそれを使用してください。なければ上記パッケージをインストールしてください）

例:
```
python -m pip install "duckdb" "openai" "defusedxml"
```

また、開発インストール:
```
pip install -e .
```
（setup/pyproject に依存します）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install -r requirements.txt   # あれば
   # または最低限:
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（詳細は下記）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN （J-Quants のリフレッシュトークン）
     - KABU_API_PASSWORD （kabuステーション API パスワード）
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化（監査ログなど）
   - 監査ログ専用 DB を作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存接続に監査スキーマのみ追加:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 環境変数と自動ロード

- パッケージは起動時にプロジェクトルート（.git または pyproject.toml を探索）を探し、見つかれば `.env` → `.env.local` の順で自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数を設定:
  ```
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 環境変数は `kabusys.config.settings` から参照できます。必須変数は呼び出し時に ValueError を投げます。

主要設定プロパティ例:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url
- settings.slack_bot_token / slack_channel_id
- settings.duckdb_path / sqlite_path
- settings.env / settings.is_live / settings.is_paper / settings.is_dev

---

## 使い方（代表的な API）

以下は簡単な利用例です。すべての API は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る設計が多いです。

- 日次 ETL 実行（デフォルトは今日）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API キーが環境変数 OPENAI_API_KEY に必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を明示しても可
print(f"scored {n} symbols")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- RSS フィード取得（ニュース収集ヘルパ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
```

注意:
- score_news / score_regime は OpenAI を呼び出すため API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY）。
- 多くの処理は「与えられた target_date を基準に過去データのみを参照する」設計で、バックテストでのルックアヘッドを防止します。

---

## ディレクトリ構成（主要ファイル）

（ルートは `src/kabusys` と想定）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（score_news）
    - regime_detector.py     # マーケットレジーム（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETL 結果クラス再エクスポート
    - news_collector.py     # RSS 収集（fetch_rss 等）
    - calendar_management.py# 市場カレンダー管理（is_trading_day 等）
    - quality.py            # データ品質チェック（check_missing_data 等）
    - stats.py              # 汎用統計（zscore_normalize 等）
    - audit.py              # 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py    # Momentum / Value / Volatility 等
    - feature_exploration.py# forward returns / IC / rank / summary
  - ai/ (上記)
  - research/ (上記)

各モジュールはドキュメント文字列と詳細なログ出力を備えており、DuckDB 経由でのデータ操作を前提に実装されています。

---

## 開発ノート / 注意事項

- OpenAI (gpt-4o-mini) や J-Quants API の呼び出しはレート制御・リトライを実装していますが、実環境では API コスト・制限に注意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に動作します。テスト時などで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB のバージョン差異により executemany の空リストなどでエラーが出る場合があります（pipeline/news_nlp 等で対応済み）。
- 監査テーブルは削除しない前提（トレーサビリティ）です。データ移行・スキーマ変更時は注意してください。
- ルックアヘッドバイアスに配慮した設計のため、関数は target_date 引数を明示的に受け取り内部で現在日付を勝手に参照しません。バックテストでは target_date の扱いを厳密にしてください。

---

README に載っていない細かな挙動や追加ユーティリティは各モジュールの docstring を参照してください。具体的な実行スクリプトや CI / デプロイ手順はプロジェクトの運用ポリシーに合わせて追加してください。