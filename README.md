# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants からのデータ取得、DuckDB を用いたETL・品質チェック、ニュースの NLP 評価、LLM を用いた市場レジーム判定、監査ログ/発注トレースのためのスキーマ等を提供します。

主な設計方針：
- Look-ahead bias を避ける（日付参照は明示的な引数で行う）
- DuckDB を中心に SQL + Python で効率的に処理
- API 呼び出しはレート制限・リトライ・フェイルセーフを組み込み
- DB 書き込みは冪等（ON CONFLICT / DELETE→INSERT 等）で安全に保存

---

## 機能一覧

- 環境設定
  - .env / 環境変数から設定を自動ロード（プロジェクトルート検出）
  - 必須値は Settings 経由で取得してバリデーション

- データ取得 / ETL（kabusys.data.jquants_client / pipeline）
  - J-Quants API から株価（日足）、財務データ、JPX カレンダーを取得
  - 差分取得・ページネーション・トークン自動リフレッシュ・リトライ
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- データ品質（kabusys.data.quality）
  - 欠損 / スパイク / 重複 / 日付不整合 のチェック
  - QualityIssue 型で詳細を返す

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、範囲内の営業日リスト取得
  - JPX カレンダーの差分更新ジョブを提供

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事を収集、前処理、raw_news に冪等保存
  - SSRF 対策、XML パースの安全化、トラッキングパラメータ除去

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア算出
  - バッチ処理・文字数制限・リトライ・レスポンス検証・スコアクリップ

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動）の MA200 乖離（70%）とマクロニュースセンチメント（30%）を合成
  - LLM 呼び出し（gpt-4o-mini）でマクロセンチメントを評価し market_regime テーブルへ書き込み

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の監査テーブル DDL と初期化
  - 監査 DB 初期化ユーティリティ（DuckDB ベース）

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - z-score 正規化などの統計ユーティリティ

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

（パッケージはプロジェクトの pyproject.toml / requirements.txt に従ってください。ここでは代表的な依存を挙げています。）

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （実プロジェクトでは pip install -e . や poetry/poetry install を使用してください）

4. 環境変数設定
   - ルートに `.env`（および必要なら `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みは、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須)：J-Quants のリフレッシュトークン
   - OPENAI_API_KEY (必須 for LLM 機能)：OpenAI API キー
   - KABU_API_PASSWORD：kabu API パスワード
   - KABU_API_BASE_URL (任意)：kabu API のベース URL (デフォルト http://localhost:18080/kabusapi)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID：LINE 通知用
   - DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH：監視 DB（デフォルト data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV：development / paper_trading / live
   - LOG_LEVEL：DEBUG/INFO/WARNING/ERROR/CRITICAL

   例 .env の一部:
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（サンプル）

以下はライブラリの主要機能を Python スクリプトから呼ぶ例です。DuckDB 接続は duckdb.connect(...) で用意します。

- 日次 ETL 実行（prices / financials / calendar を差分取得・保存）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（OpenAI を使用）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数にセットしておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジームスコア（MA200 + マクロニュース）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数または引数で
```

- 監査ログスキーマ初期化

```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続を返す
```

- カレンダー操作例

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

- ニュース収集（RSS 取得の一部）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

items = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for it in items[:5]:
    print(it["id"], it["datetime"], it["title"])
```

注意点：
- LLM を使う関数は OPENAI_API_KEY を必須とします（引数で上書き可）。
- ETL / DB 書き込みは冪等に作られているため複数回実行しても重複しません。
- 日付や対象データは明示的に渡す（内部で date.today() を参照しない関数が多い）ことでバックテストでの look-ahead を防ぎます。

---

## ディレクトリ構成

主要モジュールと説明（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - Settings: 環境変数読み込み・バリデーション、自動 .env ロード
  - ai/
    - __init__.py
    - news_nlp.py         : ニュースを LLM でスコアリング（ai_scores へ）
    - regime_detector.py  : 市場レジーム判定（ma200 + macro sentiment）
  - data/
    - __init__.py
    - jquants_client.py   : J-Quants API クライアント（取得 & 保存関数）
    - pipeline.py         : ETL パイプライン（run_daily_etl 等）
    - quality.py          : データ品質チェック
    - calendar_management.py : 市場カレンダー管理とアップデートジョブ
    - news_collector.py   : RSS 収集・前処理
    - stats.py            : 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py            : 監査ログ DDL / 初期化
    - etl.py              : ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py  : モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py : 将来リターン / IC / summary 等
  - ai/, data/, research/ ... （上記）

（実際のリポジトリにはさらに strategy / execution / monitoring などのパッケージが想定されています。 __all__ にそれらが含まれます）

---

## 開発・テスト時の補足

- 自動 .env ロードは、モジュールがインポートされた際にプロジェクトルートを探索して `.env` → `.env.local` を適用します。テストで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しやネットワーク依存の関数はモックしやすく設計されており、内部の _call_openai_api や _urlopen などを unittest.mock.patch で差し替えてテストできます。
- DuckDB を使ったテスト時は `:memory:` を渡してインメモリ DB を使えます（例: init_audit_db(":memory:")）。

---

## 既知の動作 / ポリシー

- LLM レスポンスや外部 API の失敗は基本的にフェイルセーフ（スコアは 0.0 にフォールバック、例外を抑制してログ出力）する設計です。必要に応じて呼び出し側でエラー判定をしてください。
- DB 書き込みは可能な限り冪等に実装していますが、トランザクション制御の有無や DuckDB のバージョン差異に依存する箇所があるため、本番運用前に十分な検証を行ってください。
- 監査ログ（audit）に関してはタイムゾーンを UTC に固定します（init_audit_schema が SET TimeZone='UTC' を実行）。

---

この README はコードベースの主要機能と使い方の概要を示しています。さらに詳しい API ドキュメントや実運用に関する設定（kabu API の挙動、証券会社連携、リスク制御など）は別途ドキュメント（Design doc / Operation guide）を参照してください。問題点や追加したい項目があれば教えてください。