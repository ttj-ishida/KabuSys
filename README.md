# KabuSys

日本株向けの自動売買／データ基盤ライブラリセットです。  
ETL、ニュース収集、AI を用いた記事センチメント評価、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）、J-Quants クライアント等を含むモジュール群を提供します。

主な想定利用ケース：
- データパイプライン（J-Quants → DuckDB）による日次差分取得と品質チェック
- RSS ニュース収集と銘柄紐付け
- OpenAI を用いたニュースの銘柄／マクロセンチメント評価（AI スコアリング）
- マーケットレジーム判定（ETF + マクロニュース合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 発注/約定までの監査ログ（監査テーブル初期化ユーティリティ）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得 + DuckDB への冪等保存）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days、calendar_update_job）
  - ニュース収集（RSS 取得、前処理、raw_news 保存のためのユーティリティ）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（監査用テーブル定義・初期化、init_audit_db / init_audit_schema）
  - 汎用統計ユーティリティ（zscore 正規化等）

- ai
  - ニュースセンチメントスコア（score_news）
  - 市場レジーム判定（score_regime）

- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索・評価（calc_forward_returns, calc_ic, factor_summary, rank）
  - zscore_normalize（data.stats からエクスポート）

- 設定管理
  - 環境変数 / .env 自動読み込み（kabusys.config.Settings）

---

## 前提 / 要件

- Python 3.10 以上（| 型指定 (X | Y) を使用しているため）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai（OpenAI Python SDK）
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

例（pip）:
```
pip install duckdb openai defusedxml
```

プロジェクトをパッケージとして扱う場合は requirements.txt を用意してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```
3. 環境変数設定
   - プロジェクトルートに `.env`（または開発用に `.env.local`）を置くと自動で読み込まれます（kabusys.config が .git または pyproject.toml を検出して読み込み）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   必要な主要環境変数（一例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、ETL 用）
   - OPENAI_API_KEY: OpenAI API キー（AI スコアリング実行時に必要）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（実行/発注機能と連携する場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: monitoring 用 sqlite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
   - LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

   .env の簡単な例（実運用では秘密情報を直書きしないでください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. データベース初期化（監査ログ用 DuckDB 例）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（例）

以下は代表的なユースケースの簡単なコード例です。すべて Python スクリプト内で実行します。

- 日次 ETL 実行（J-Quants からの差分取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（ファイルまたは ":memory:"）
conn = duckdb.connect("data/kabusys.duckdb")

# 今日を対象に ETL 実行（settings.jquants_refresh_token が必要）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースの銘柄センチメント評価（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数を返す
print("written:", written)
```

- マーケットレジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- RSS フィードの取得（ニュース収集ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url=url, source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

- 監査テーブル初期化（アプリの起動時等）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions 等が作成されます
```

備考：
- OpenAI 関連関数（score_news, score_regime）は OPENAI_API_KEY または api_key 引数が必要です。
- run_daily_etl 等は内部で settings.jquants_refresh_token を参照して J-Quants 用のトークン取得を行います（.env に設定してください）。
- DuckDB に対する書き込みは多くの場合冪等（ON CONFLICT DO UPDATE）で実装されています。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要モジュール配置（src/kabusys）を抜粋しています。

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数管理と Settings
  - ai/
    - __init__.py
    - news_nlp.py                   # 記事ごとの AI スコアリング
    - regime_detector.py            # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（取得 + 保存）
    - pipeline.py                   # ETL パイプライン実装（run_daily_etl 等）
    - etl.py                        # ETL 再エクスポート
    - calendar_management.py        # 市場カレンダー管理
    - news_collector.py             # RSS 取得・前処理
    - quality.py                    # 品質チェック
    - stats.py                      # 統計ユーティリティ（zscore_normalize）
    - audit.py                      # 監査テーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py            # ファクター計算（Momentum/Value/Volatility）
    - feature_exploration.py        # 将来リターン・IC・統計サマリ等

---

## 設計上の注意点 / ポイント

- Look-ahead Bias の防止を重視
  - AI スコアリングやレジーム判定、ETL の対象期間は明示的な target_date 引数で扱い、内部で date.today() を直接参照しない実装方針が採られています（バックテスト等で重要）。
- 冪等性
  - J-Quants の保存処理、ai_scores の更新、監査テーブルの初期化などは冪等（ON CONFLICT / INSERT … DO UPDATE 等）で実装されています。
- フェイルセーフ
  - OpenAI や外部 API の失敗時にはゼロスコアで継続したり、リトライ・ログ出力で安全サイドを保つ設計になっています。
- セキュリティ／堅牢性
  - news_collector では SSRF 防止、受信サイズ制限、XML パースに defusedxml を利用する等の対策があります。
- 環境変数ローディング
  - .env / .env.local を自動読み込みします（プロジェクトルート検出: .git または pyproject.toml を基準）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能。

---

## 開発 / テスト時のヒント

- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して外部 .env の影響を抑えると安定します。
- OpenAI や J-Quants の外部呼び出しを伴う関数は、モジュール内の _call_openai_api 等を unittest.mock.patch してモック化できます（既にその想定で設計されています）。
- DuckDB は ":memory:" を指定してインメモリ DB を使用可能です（テスト高速化に便利）。

---

## ライセンス / 貢献

この README はコードベースから自動的に抽出した情報を元に要約しています。実際のライセンス情報や貢献ルール（CONTRIBUTING.md）が別途ある場合はそちらを参照してください。

---

必要であれば、README にサンプル .env.example ファイルや requirements.txt、より詳細な API リファレンス（各関数の引数/戻り値/例外）、開発用の Makefile / tox / pre-commit 設定例を追加できます。どの情報を優先して追記しますか？