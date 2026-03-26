# KabuSys

KabuSys は日本株向けのデータ基盤・研究・AI評価・監査・ETL を統合した自動売買/リサーチ用ライブラリ群です。DuckDB をデータレイクとして使用し、J-Quants API や RSS ニュース、OpenAI を利用した NLP/レジーム判定、ETL・品質チェック、監査ログなどを含みます。

バージョン: 0.1.0

---

## 主要な機能（概要）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得して DuckDB に保存
  - 差分更新・バックフィル・ページネーション対応、トークン自動リフレッシュ、レート制御、冪等保存（ON CONFLICT）
- ニュース収集 / NLP
  - RSS 取得・前処理・raw_news への冪等保存
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF MA200 による市場レジーム判定（score_regime）
- リサーチ / ファクター
  - Momentum、Value、Volatility、Liquidity 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合検出（run_all_checks）
- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、夜間カレンダー更新ジョブ
- 監査ログ / トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブル初期化・管理（init_audit_schema / init_audit_db）
- 設定管理
  - .env または環境変数から設定を自動ロード（プロジェクトルート検出）
  - 必須設定の検証を提供（kabusys.config.settings）

---

## 前提 / 必要環境

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml

推奨: 仮想環境（venv / pipenv / poetry 等）を利用してください。

例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクト配布に requirements.txt / pyproject.toml がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリを取得
   - git clone ... （任意の方法でソースを取得）

2. 仮想環境を作成して依存をインストール
   - 例は上記を参照

3. 環境変数（.env）を用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード（使用する場合）
     - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（使用する場合）
     - SLACK_CHANNEL_ID: Slack チャネル ID（使用する場合）
     - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）を実行する場合に必要（score_* 関数へ直接渡すことも可）
   - 任意:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - KABUSYS_ENV (development / paper_trading / live) — 動作モード
     - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB データベース準備
   - デフォルトの path は settings.duckdb_path（`data/kabusys.duckdb`）。ディレクトリがない場合は作成してください（init 関数でも作成されます）。
   - 監査ログ専用 DB を初期化する場合:
     - python コード内で `kabusys.data.audit.init_audit_db(path)` を呼ぶと、ファイル親ディレクトリを自動作成してテーブルを作成します。

---

## 使い方（主要な例）

以下はライブラリをプログラムから利用する基本例です。各モジュールは DuckDB 接続を受け取って処理します。

1. 基本的な ETL（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2. ニュースのセンチメントスコア取得（OpenAI 必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # 実運用は OPENAI_API_KEY を渡す
```
- 注意: score_news の api_key 引数は OpenAI API キーです。None の場合は環境変数 OPENAI_API_KEY が使われます。

3. 市場レジーム判定（ETF 1321 の MA200 とマクロ記事の LLM スコアを合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # api_key は OpenAI のキー
```

4. 監査ログ DB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb 接続
```

5. J-Quants API の直接利用例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

6. マーケットカレンダー周り
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
is_td = is_trading_day(conn, date(2026,3,20))
next_td = next_trading_day(conn, date(2026,3,20))
```

---

## 設定の自動読み込みについて

- `kabusys.config` はプロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動で読み込みます（既存 OS 環境変数を上書きしない挙動等に配慮）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。
- settings オブジェクト（kabusys.config.settings）から各種設定値にアクセスできます（必須項目が未設定の場合は ValueError）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード、settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントを OpenAI で評価し ai_scores に書き込む
    - regime_detector.py — マクロ + ETF MA200 を合成して market_regime を判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 等）
    - pipeline.py — ETL パイプライン、run_daily_etl 等
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — JPX カレンダー管理 / 営業日判定 / calendar_update_job
    - news_collector.py — RSS 取得・前処理・raw_news 保存
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログテーブル定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — momentum / value / volatility のファクター計算
    - feature_exploration.py — forward returns / IC / factor_summary / rank
  - ai, data, research の各モジュールは相互に利用され、ETL / 研究 / 発注フローを構成

---

## 推奨ワークフロー（簡易）

1. .env を準備して必要な API キーを設定
2. DuckDB を用意（settings.duckdb_path）
3. ETL を定期実行（cron / Airflow 等）で run_daily_etl を呼ぶ
4. raw_news を収集し（news_collector.fetch_rss + 保存処理） ai_scores を作成
5. score_regime / score_news を日次で実行して研究用データを生成
6. 監査ログ（audit DB）を初期化して発注フローを統合

---

## 注意点 / 設計上の方針

- ルックアヘッドバイアス防止：日次処理は内部で datetime.today()/date.today() を勝手に参照しないよう設計されています（target_date を明示的に渡すことを推奨）。
- 冪等性：ETL と保存処理は基本的に冪等（ON CONFLICT / DELETE→INSERT 等）です。
- フェイルセーフ：外部 API（OpenAI / J-Quants）失敗時は処理を継続する設計が多く、必要に応じてログ／警告を出します。
- テスト：OpenAI 呼び出し関数等は差し替え可能（モックしやすい実装）になっています。

---

## ライセンス / 貢献

（プロジェクトのライセンス・コントリビューションガイドがある場合はここに追記してください）

---

README に載せるサンプルや補足が必要であれば、実行例（ETL の CLI 化、Dockerfile、GitHub Actions での定期実行など）も追加で作成できます。どの部分を優先して詳細化しましょうか？