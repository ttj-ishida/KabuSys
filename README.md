# KabuSys

日本株向けの自動売買／データプラットフォームライブラリ。データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのバックテスト／自動売買プラットフォームの基盤機能をまとめたパッケージです。主な目的は以下です。

- J-Quants API を用いた株価・財務・カレンダーの差分取得と DuckDB への保存（ETL）
- RSS からのニュース収集と前処理、OpenAI を用いたニュースセンチメント評価（銘柄毎の ai_score 生成）
- ニュース + 指標（ETF の MA200）を組み合わせた市場レジーム判定（bull / neutral / bear）
- 研究（research）向けのファクター計算・特徴探索ユーティリティ
- 監査ログ（signal → order_request → executions）を記録するスキーマ定義と初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計方針として、ルックアヘッドバイアス回避、冪等保存、堅牢な API リトライ、DB 優先のフォールバックなどを重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - ニュース収集（RSS -> raw_news）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores テーブルへ）
  - 市場レジーム判定（score_regime: ETF 1321 の MA200 突合 + マクロ記事センチメント）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数／.env 自動読み込み（プロジェクトルート検出）
  - Settings オブジェクトを通じた設定アクセス（settings）

その他：news_collector（安全な RSS 取得、SSRF 対策、トラッキング除去）、jquants_client（レート制御・リトライ・トークン自動リフレッシュ）など。

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | 記法、typing.Literal 等を使用）
- DuckDB を使います（ライブラリ依存）

1. リポジトリをチェックアウトし、開発モードでインストール（例）:
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install -e ".[all]"    # requirements が extras にまとまっている場合
   ```
   ※ requirements.txt / pyproject.toml の依存に従ってください。主要依存例:
   - duckdb
   - openai (OpenAI Python SDK v1)
   - defusedxml

2. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。必要な主要環境変数例:

   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  (任意)
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - KILL_FLAG_CLEAR_ON_START=0 or 1
   - CPU_THRESHOLD_PCT=90.0
   - MEMORY_THRESHOLD_PCT=85.0
   - DISK_THRESHOLD_PCT=90.0
   - KABUSYS_ENV=development | paper_trading | live
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

   (`.env.example` をプロジェクトルートに置くことが推奨されます)

3. データディレクトリ作成:
   ```
   mkdir -p data
   ```

4. DuckDB 初期化（監査 DB を使う場合）:
   Python REPL やスクリプトで:
   ```python
   import kabusys.data.audit as audit
   conn = audit.init_audit_db("data/audit.duckdb")  # ":memory:" も可
   # conn は duckdb 接続
   ```

---

## 使い方（代表的な例）

以下は主要な API を使う最小例です。すべて duckdb の接続を渡すことで動作します。

1) ETL（デイリー ETL）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントスコア生成
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written scores: {n_written}")
```
- api_key を省略すると環境変数 `OPENAI_API_KEY` を参照します。
- 記事がない場合は LLM 呼び出しをスキップして 0 を返します。
- 失敗時は部分的にスキップするフェイルセーフ設計です。

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数を利用
```
- ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM（重み 30%）を組合せます。
- API エラー時はマクロセンチメントを 0 として継続します。

4) 研究用途のファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# リスト形式で銘柄ごとのファクターデータが返る
```

5) データ品質チェック
```python
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

6) settings の参照例
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```
- `.env` 自動読み込みはパッケージインポート時に行われます（プロジェクトルートを自動探索）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

---

## ディレクトリ構成（主要モジュールの説明）

- src/kabusys/
  - __init__.py (パッケージ初期化、バージョン)
  - config.py
    - Settings: 環境変数管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py: ニュースを銘柄ごとに集約して OpenAI でスコア化、ai_scores へ格納
    - regime_detector.py: ETF 1321 の MA200 とマクロ記事で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py: J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py: ETL パイプライン（run_daily_etl 等）、ETLResult クラス
    - etl.py: ETLResult のエクスポート
    - news_collector.py: RSS 取得・前処理・raw_news 保存
    - calendar_management.py: market_calendar 管理・営業日判定・更新ジョブ
    - quality.py: データ品質チェック機能群
    - stats.py: zscore_normalize 等の統計ユーティリティ
    - audit.py: 監査ログテーブル定義と初期化関数
  - research/
    - __init__.py
    - factor_research.py: momentum/value/volatility 等のファクター計算
    - feature_exploration.py: 将来リターン、IC、統計サマリー、ランク関数
  - ai、research、data の下にさらに補助関数やユーティリティが含まれます。

---

## 注意事項 / 運用上のポイント

- OpenAI API を利用する機能（news_nlp, regime_detector）は API キーが必須です。api_key を引数で注入でき、テスト時はモック可能です。
- J-Quants API はレート制限があり、jquants_client は内部でスロットリングと指数バックオフを行います。認証はリフレッシュトークンベースです（settings.jquants_refresh_token）。
- ETL や API 操作は部分的に失敗しても他の処理を継続する設計になっています（フェイルセーフ）。エラー・品質問題は ETLResult に集約されます。
- ニュース収集は SSRF 対策、トラッキング除去、受信サイズ制限、defusedxml の使用など安全性に配慮しています。
- DuckDB の executemany はバージョンによって空リストの扱いが異なるため、実装は空チェックを行っています。
- 日付操作ではルックアヘッドバイアス回避のために内部で date.today() を不用意に参照しない設計になっています（多くの関数が target_date を明示的に受け取ります）。

---

## 開発 / テスト時のヒント

- settings の自動 .env 読み込みは、プロジェクトルート（.git または pyproject.toml）から行われます。テストで環境を固定したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから環境を注入してください。
- OpenAI 呼び出しはモジュール内の `_call_openai_api` を patch してモックできます（unittest.mock.patch）。
- ネットワーク I/O 周り（RSS, J-Quants, OpenAI）はモック可能なラッパー関数が用意されています。

---

## ライセンス / コントリビューション

（本テンプレートにはライセンス記載がありません。実運用時は適切なライセンスを追加してください）

---

この README はコードベースの主要機能と使い方を要約したものです。各モジュールの細かな実装やパラメータはソースコードの docstring / コメントをご参照ください。必要であれば導入手順や運用ガイドの詳細化（CI、デプロイ、監視、テスト方針など）も作成できます。