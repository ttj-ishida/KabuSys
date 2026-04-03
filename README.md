# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP（OpenAI）、ファクター計算、マーケットカレンダー管理、監査ログ／発注トレーサビリティなどの機能を提供します。

主な用途例：
- J-Quants からの日次データ ETL -> DuckDB 保存
- RSS ニュース収集と OpenAI を用いた銘柄センチメント算出
- マーケットレジーム判定（ETF + マクロ記事の組合せ）
- 研究用ファクター計算・特徴量探索
- 発注フローの監査ログ（DuckDB）初期化

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出） / KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能
  - settings オブジェクト経由で各種設定（J-Quants トークン、OpenAI キー、DB パス、監視閾値など）を提供

- データ ETL（kabusys.data.pipeline）
  - J-Quants から差分取得（株価 / 財務 / カレンダー）
  - バックフィル、ページネーション、リトライとレート制御
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 対策、サイズ制限、URL 正規化）
  - raw_news / news_symbols への冪等保存想定

- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI（gpt-4o-mini 等）で算出して ai_scores に保存する処理ロジック
  - regime_detector.score_regime: ETF（1321）の200日移動平均乖離とマクロ記事の LLM センチメントを合成して市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ保存

- 研究（kabusys.research）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ
  - data.stats の zscore 正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル DDL とインデックスを提供
  - init_audit_db で監査専用 DuckDB を初期化

- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証トークン管理（refresh -> id_token）
  - fetch/save のユーティリティ（daily_quotes, financial_statements, market_calendar）
  - レートリミット、リトライ、401 自動リフレッシュ対応

---

## セットアップ

前提
- Python 3.10+（型アノテーションの union 演算子などを使用）
- DuckDB、OpenAI SDK 等の依存ライブラリが必要

例（venv を作って pip インストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発中にパッケージを編集する場合:
pip install -e .
```

必須環境変数（.env または OS 環境変数で設定）
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（発注を使う場合）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime を使う場合）

任意（デフォルト値あり）
- KABUSYS_ENV : development | paper_trading | live（デフォルト development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH など（設定モジュール参照）

自動 .env 読み込みについて
- パッケージは起点ファイル場所から親ディレクトリを探索し `.git` または `pyproject.toml` を見つけたルートにある `.env` / `.env.local` を自動で読み込みます。
- 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方（代表的な例）

以下は最小限の実行例です。実際の ETL や AI 呼び出しには各種テーブル定義や DB スキーマが前提になります。

1) DuckDB 接続の用意
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行（デフォルトで today）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニューススコア算出（OpenAI API キーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026,3,20))
print("書き込み銘柄数:", written)
```

4) 市場レジーム算出（OpenAI API キーが必要）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

5) 監査用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db は UTC タイムゾーン固定と DDL 実行を行う
```

6) J-Quants 直接呼び出し（例: 株価取得）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使う
records = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,31))
```

注意点:
- AI 呼び出し（OpenAI）は API のレート／課金に注意して利用してください。
- 各書き込み先テーブル（raw_prices, ai_scores, market_regime 等）は事前に適切なスキーマが作られていることが前提です（ETL のドキュメントやスキーマ初期化ロジックを参照してください）。
- LLM 呼び出しや外部 API は失敗時のフォールバック（0.0）や部分失敗許容の設計になっていますが、ログを確認してください。

---

## 主要モジュール / ディレクトリ構成

（リポジトリの src/kabusys 以下の主なファイル・説明）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings オブジェクト（settings）
  - ai/
    - __init__.py
    - news_nlp.py        : ニュース NLU / OpenAI を使った銘柄センチメント算出（score_news）
    - regime_detector.py : ETF MA とマクロ記事 LLM を組合せた市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  : J-Quants API クライアント（fetch/save, 認証, rate limit）
    - pipeline.py        : ETL パイプライン（run_daily_etl, 個別 ETL）
    - etl.py             : ETLResult 再エクスポート
    - news_collector.py  : RSS 取得・前処理・保存ロジック（SSRF 対策等）
    - calendar_management.py : マーケットカレンダー管理と is_trading_day 等ユーティリティ
    - quality.py         : データ品質チェック（欠損/スパイク/重複/日付不整合）
    - stats.py           : zscore_normalize 等統計ユーティリティ
    - audit.py           : 監査ログ（signal/order/execution）DDL と初期化処理
  - research/
    - __init__.py
    - factor_research.py : モメンタム/ボラ/バリュー等のファクター計算
    - feature_exploration.py : 将来リターン計算、IC、ファクターサマリ、rank
  - monitoring/ (パッケージ公開対象に列挙ありが実装は省略されているファイルもあります)

（上記は抜粋です。実際のファイル群はリポジトリを参照してください。）

---

## 開発・デバッグのヒント

- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml から検出します。テスト時に自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- OpenAI 呼び出し部分は内部で `_call_openai_api` として分離してあり、ユニットテストではモック差替えが容易です（例: unittest.mock.patch）。
- J-Quants クライアントはモジュールレベルで ID トークンをキャッシュします。ページネーションを跨ぐ際にトークン共有されます。
- DuckDB executemany は空リストを受け付けない場合がある点に注意（コード内でチェック済み）。

---

## ライセンス / 貢献

リポジトリに LICENSE ファイルがあればそれに従ってください。貢献は Pull Request と Issue を通じて受け付ける想定です（リポジトリの CONTRIBUTING.md があれば参照）。

---

必要があれば、README に含める具体的なテーブルスキーマ、例となる .env.example、あるいは DB 初期化スクリプトのテンプレートを追加で作成します。どれを優先しますか？