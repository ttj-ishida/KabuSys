# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ集です。  
ETL（J-Quants）→ データ品質チェック → ニュースNLP（OpenAI）→ 市場レジーム判定 → 研究/ファクター計算 → 監査ログ までをカバーします。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやリサーチ基盤で必要となる以下の機能群を提供します。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への冪等保存（ETL）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を使ったニュースセンチメント / マクロセンチメント評価（JSON Mode を利用）
- 市場レジーム判定（ETF MA + マクロセンチメントの合成）
- ファクター計算・特徴量探索・統計ユーティリティ
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）
- 環境変数 / .env 管理ユーティリティ

設計上の重点：
- ルックアヘッドバイアス防止（バックテストでの日付参照を配慮）
- 冪等性（DB 保存は ON CONFLICT / 主キーで上書き）
- フェイルセーフ（外部 API 失敗時は完全停止せず安全側にフォールバック）
- DuckDB を中心に軽量・高速に処理

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（is_trading_day / next_trading_day / get_trading_days）
  - ニュース収集（fetch_rss, preprocess_text, news_collector）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数/.env 自動読み込み、Settings オブジェクト（settings）による集中参照
- そのほか：strategy / execution / monitoring（システム全体で利用する名前空間）

---

## 必要条件 / 依存関係

- 推奨 Python バージョン: 3.10+
  - （ソースは typing の省略形や pathlib 等を利用）
- 必要な主要ライブラリ（代表例）:
  - duckdb
  - openai
  - defusedxml
- その他（標準ライブラリ以外）: requests 等が使われていれば別途必要になる可能性があります。

インストールはプロジェクトの pyproject.toml / requirements.txt に従ってください。簡易的には開発環境で:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .            # pyproject.toml がある想定
# または
pip install -r requirements.txt
```

---

## 環境変数（.env）

config.Settings により設定を参照します。主なキー：

- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime で未指定時に参照）
- KABU_API_PASSWORD：kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL：kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN：Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID：Slack 通知チャンネル（必須）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV：環境 (development / paper_trading / live)（デフォルト development）
- LOG_LEVEL：ログレベル (DEBUG/INFO/...)（デフォルト INFO）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を起点に .env → .env.local を読み込みます。
- 優先順位: OS 環境 > .env.local > .env
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みをスキップ

.env は次のような書式をサポートします:
- export KEY=val、KEY="quoted value"、コメント行（#）等
- クォート内のエスケープや inline コメントの扱いに配慮しています

参考: .env.example を作成しておくことを推奨します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 依存パッケージをインストール
4. .env を用意（.env.example を参照）
5. DuckDB 用のフォルダを作成（必要なら）

例:

```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -e .
# .env をプロジェクトルートに作成（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等を設定）
mkdir -p data
```

---

## 使い方（代表的なユースケース）

以下は簡単な Python スニペット例です。実際はログやエラーハンドリングを追加してください。

- DuckDB に接続して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しなければ今日が対象（ETL は内部で営業日に調整）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成（OpenAI API キーは OPENAI_API_KEY 環境変数または api_key 引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジームをスコアリング

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化して接続を得る

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへアクセスできます
```

- RSS フィードをフェッチする（ニュース収集のロジック呼び出し例）

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

---

## 簡単な開発・デバッグのヒント

- 環境変数の自動読み込みを止めたいテストや一時環境では、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- OpenAI 呼び出しは内部でリトライや失敗時のフォールバック（0.0）を行うため、API の一時障害により ETL 全体が止まりにくい設計です。
- DuckDB の executemany は空リストを受け付けないバージョンもあるため、実装側で空リストをチェックしてから呼び出しています（互換性保持のため）。

---

## ディレクトリ構成

主要ファイル・モジュールの概要（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースセンチメント -> ai_scores 書込ロジック
    - regime_detector.py    # ETF MA + マクロセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント（fetch / save）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py# マーケットカレンダー管理・営業日ロジック
    - news_collector.py     # RSS 取得・前処理・保存ユーティリティ
    - quality.py            # データ品質チェック（QualityIssue）
    - stats.py              # 統計ユーティリティ（zscore_normalize）
    - etl.py                # ETLResult 再エクスポート
    - audit.py              # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    # モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py# 将来リターン・IC・サマリー等
  - ai/, data/, research/ など他の補助モジュール

（上記は本リポジトリに含まれる代表的なモジュール一覧です。実際のリポジトリで README を最新版に合わせて更新してください。）

---

## ライセンス / 貢献

この README はコードベースの概要ドキュメントです。ライセンスやコントリビューションガイドラインはリポジトリ上の LICENSE / CONTRIBUTING.md を参照してください。

---

必要であれば、README に次を追記できます：
- .env.example のサンプル
- 詳細な API 使用例（各関数の引数説明）
- 実運用のデプロイ手順（systemd / Cron / Airflow 連携例）
- ユニットテストの実行方法

追記・フォーマット調整が必要なら指示してください。