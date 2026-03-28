# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ部分）。  
データ取得・ETL、ニュース NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買やリサーチを行うための内部ライブラリ群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）と DuckDB への保存（ETL）
- RSS ニュース収集と前処理、OpenAI を用いたニュースセンチメント推定（銘柄別 ai_score）
- マクロニュース＋ETF（1321）200日移動平均乖離を合成した「市場レジーム判定」
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティなど）と統計ユーティリティ
- 監査ログ（シグナル→発注→約定）用のテーブル定義と初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、バックテストでのルックアヘッドバイアスを避けるために date.today()/datetime.today() を不用意に参照しない実装が心がけられています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得 + 保存 save_*）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS の取得・前処理・保存）
  - データ品質チェック（missing_data / spike / duplicates / date_consistency）
  - 監査ログ（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとのニュースセンチメント算出）
  - レジーム判定（score_regime: マクロ + ETF MA200 乖離で市場レジームを日次判定）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・評価（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数管理（.env の自動読み込み、Settings オブジェクト経由で設定取得）

---

## セットアップ手順

前提
- Python 3.10+ を推奨（型注釈に `|` 形式などを使用）
- DuckDB、OpenAI SDK、defusedxml 等の依存

1. リポジトリをチェックアウト／クローン

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ pyproject / requirements がある場合はそちらに従ってください。

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数を準備
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数（例）:

```
# .env の例
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

- Settings は `kabusys.config.settings` から取得できます。

---

## 使い方（主な API）

以下は代表的な呼び出し方の例です。実行前に環境変数や DB パスを適切に設定してください。

1) DuckDB 接続の作成（例）:

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL の実行

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定 or None（今日）を使用
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（銘柄別）を算出して ai_scores に書き込む

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # APIキーを引数か環境変数で
print(f"書き込み銘柄数: {n_written}")
```

4) 市場レジーム判定（market_regime テーブルへ書き込み）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ（監査用 DB の初期化）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 必要に応じて同一接続へテーブルを作成
```

6) ファクター計算（研究用）

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
factors_z = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

注意点
- OpenAI 呼び出しを含む機能（score_news, score_regime）は API キー（OPENAI_API_KEY）を必要とします。api_key 引数で注入可能。
- DuckDB の executemany は空リストを受け付けないバージョンの差異に注意している実装になっています。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabu API パスワード（必要時）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用（必要に応じて）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development, paper_trading, live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル・モジュール説明）

- kabusys/
  - __init__.py
  - config.py
    - Settings オブジェクト（環境変数管理、.env 自動読み込みロジック）
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None): ニュースを集約して OpenAI でスコア化、ai_scores に書き込み
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None): ETF(1321) MA200 乖離 + マクロニュースで market_regime 判定
  - data/
    - __init__.py
    - calendar_management.py
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
    - etl.py
      - ETLResult（再エクスポート）
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl / 各種差分更新ロジック
    - stats.py
      - zscore_normalize
    - quality.py
      - 各種データ品質チェックと run_all_checks
    - audit.py
      - 監査ログテーブル DDL と init_audit_schema / init_audit_db
    - jquants_client.py
      - J-Quants API クライアント（fetch / save 関数群、認証・レートリミット・リトライ）
    - news_collector.py
      - RSS 取得・前処理・SSRF対策・記事ID生成など
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - ai/, data/, research/ 以下はそれぞれのユーティリティ群を保持

---

## 注意事項 / 実運用メモ

- OpenAI 呼び出しは課金対象かつレイテンシとエラーの考慮が必要です。API のレート・コストを考慮してバッチ運用を行ってください。
- J-Quants API はレート制限があるためモジュール内に RateLimiter とリトライ実装を含みます。大量データ取得時は時間を見て運用してください。
- DuckDB の SQL / executemany の挙動はバージョン差異があるため、互換性に配慮した実装になっていますが、実際の運用環境での動作確認を推奨します。
- 監査ログは削除を想定していません。テーブル設計・データ保持ポリシーは運用規程に沿って管理してください。
- テストのしやすさを考慮し、外部 API 呼び出し部分（OpenAI, urllib など）をモック可能な構造にしています。ユニットテストでは該当関数を patch して検証してください。

---

何か特定の使い方（例: ETL スケジューリング、バックテスト用のデータ取り込み、OpenAI プロンプトのカスタマイズなど）について README に追記したい項目があれば教えてください。