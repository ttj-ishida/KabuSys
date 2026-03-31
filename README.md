# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ（KabuSys）

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量（ファクター）計算、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログなどを一貫して提供する Python ライブラリです。  
DuckDB を内部データストアとして利用し、OpenAI（LLM）や J-Quants API を組み合わせた研究〜本番ワークフローを想定しています。

主な設計方針:
- ルックアヘッドバイアスの排除（内部で `date.today()` を直接参照しない等）
- ETL は差分更新・バックフィル対応で冪等に保存
- 外部 API 呼び出しはリトライ/バックオフ・レート制御を備える
- 品質チェックは全問題を収集して呼び出し元が判断できるようにする
- 監査ログ（トレース）を重視し、発注フローをUUIDチェーンで追跡可能にする

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、Settings オブジェクト）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・永続化
  - 財務データ取得・永続化
  - JPX カレンダー取得・永続化
  - レート制御、認証トークン自動リフレッシュ、リトライ
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - ETLResult 情報を返却
- ニュース収集（RSS）と前処理（SSRF対策・トラッキングパラメータ除去）
- ニュースNLP（OpenAI を用いた銘柄ごとのセンチメント付与）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの組合せ）
- 研究用機能（ファクター算出、将来リターン、IC、統計サマリ、Zスコア正規化）
- 監査ログ（signal_events / order_requests / executions テーブル）初期化ユーティリティ
- 汎用統計ユーティリティ（zscore_normalize 等）

---

## セットアップ手順

前提:
- Python 3.10+（型アノテーションの Union | を使用しているため）
- DuckDB が動作すること
- OpenAI API キー、J-Quants リフレッシュトークン等の外部 API 資格情報

1. リポジトリをクローン（例）
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # Linux / macOS
   .venv\Scripts\activate       # Windows
   ```

3. 必要パッケージをインストール（推奨パッケージ）
   - 必要な主要依存（実行に必要な最低限）
     - duckdb
     - openai
     - defusedxml
   - 例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 開発用に `pip install -e .`（パッケージとしてインストール）を選択しても可。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（上書き順: OS env > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（主要）環境変数（Settings で参照されているもの）:
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN — Slack 通知用（オプションだがモニタリングで使用）
   - SLACK_CHANNEL_ID — Slack チャンネル ID
   - OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector などで使用）

   任意の設定（デフォルト値あり）:
   - KABUSYS_ENV (development | paper_trading | live) — 実行環境
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
   - KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（監視用 sqlite path） 等

   例 .env の抜粋:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベース初期化（監査ログ）
   - 監査用 DB を別途初期化するには:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   - 既存 DuckDB 接続へ監査スキーマを追加する場合:
   ```python
   from kabusys.data.audit import init_audit_schema
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn)
   ```

---

## 使い方（主要な利用例）

以下は主要なモジュール関数の呼び出し例です。実行はアプリケーションの用途に合わせて組み合わせてください。

- DuckDB 接続を作成して日次 ETL を回す:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄スコア付与:
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で使う
print(f"scored {n} codes")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- ファクター計算（研究用）:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- 品質チェックを実行:
```python
from kabusys.data.quality import run_all_checks
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意点:
- OpenAI 呼び出しや外部ネットワーク呼び出しは環境・料金面でコストが掛かります。テスト時は各モジュールの内部呼び出し（例: `_call_openai_api`, `_urlopen`）をモックできます（ソースに差し替え想定）。
- ETL / API 呼び出しはリトライ・レート制御が組み込まれています。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの `src/kabusys` を起点に抜粋）

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス（環境変数読み込み、自動 .env ロード）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM を用いた銘柄ごとのセンチメント算出
    - regime_detector.py — ETF MA200 とマクロニュースから市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - quality.py         — データ品質チェック（欠損・スパイク等）
    - news_collector.py  — RSS 収集 / 前処理（SSRF 対策）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - audit.py           — 監査ログスキーマ / 初期化（signal/order/execution）
    - etl.py             — ETLResult の再エクスポート
    - stats.py           — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Value/Volatility 計算
    - feature_exploration.py  — forward returns / IC / summary / rank 等
  - ai、data、research 以外にも strategy / execution / monitoring などのパッケージが __all__ に含まれる想定（実装はコードベースに依存）

補足:
- 各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を引数に受け取り、DB テーブルに対してクエリを実行します。
- モジュール内の定数や挙動（例：ニュースの時間ウィンドウ、バッチサイズ、モデル名）はソースコードに記載されています。必要に応じて調整してください。

---

## 運用上の注意・ベストプラクティス

- 環境分離: 開発/ペーパー/ライブの環境（KABUSYS_ENV）に応じて設定・ログレベル等を分けてください。
- 認証情報の管理: J-Quants トークンや OpenAI キーは安全に管理し、Git リポジトリ等に公開しないでください。
- コスト管理: OpenAI の API 呼び出しはバッチ化されていますが、利用量に注意してください。ニューススコアやレジーム判定は実行頻度を制御してください。
- テスト: 外部依存（ネットワーク・API）が多いため、ユニットテストでは該当関数をモックしてください。ソース内に差し替え可能な内部ラッパー（例: `_call_openai_api`, `_urlopen`）が用意されています。
- データ品質: ETL 後は `run_all_checks` で品質問題がないか確認し、必要に応じて警告・アラートを出してください。

---

必要であれば、README に含めるサンプル .env.example、requirements.txt、CI/CD 用の実行手順（cron / systemd / Airflow などで ETL をスケジューリングする例）や、より詳細な API（各テーブルスキーマや出力フォーマット）を追加で作成できます。どの追加情報が必要か教えてください。