# KabuSys

KabuSys は日本株の自動売買・データ基盤・リサーチ用ライブラリ群です。J-Quants / kabuステーション / OpenAI 等と連携して、データの ETL、品質チェック、ニュース NLP による銘柄スコアリング、市場レジーム判定、監査ログ（発注トレース）などを提供します。

主な設計方針は以下の通りです。
- ルックアヘッドバイアスを避ける（内部で date.today() を無秩序に参照しない）
- DuckDB をデータ層に利用し、SQL + Python で処理を実装
- 外部 API 呼び出しはリトライ / レート制御を実装して堅牢化
- 各処理は冪等（idempotent）を意識した保存ロジック

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価日足 / 財務 / 上場情報 / JPX カレンダーを差分取得して DuckDB に保存
  - ETL の品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL の統合実行（run_daily_etl）
- ニュース収集 / NLP
  - RSS からニュースを収集し raw_news に保存（SSRF 対策・正規化・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコアリング（score_news）
  - マクロニュースと ETF（1321）の MA200 乖離を統合した市場レジーム判定（score_regime）
- 研究（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー等
  - Z スコア正規化ユーティリティ
- カレンダー管理
  - market_calendar テーブルを用いた営業日判定・前後営業日の取得など
  - J-Quants からのカレンダー差分更新ジョブ
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までのトレーサビリティ用テーブル定義・初期化（init_audit_schema / init_audit_db）
- ユーティリティ
  - 環境変数管理（自動 .env ロード・必須チェック）
  - J-Quants / OpenAI クライアントラッパ（レート制御・リトライ等）

---

## 必要条件（推奨）

- Python 3.10+（型ヒントに | を使用）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（AI 機能を使う場合）
- defusedxml（RSS パースの安全化）
- そのほか標準ライブラリ（urllib 等）

（実際のパッケージ依存はプロジェクトの packaging に依存します。requirements.txt / pyproject.toml があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージソースを入手）
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - その他プロジェクト依存がある場合は requirements.txt / pyproject.toml に従う
4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須環境変数（少なくとも実運用で必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
     - OPENAI_API_KEY — OpenAI を使う場合に必須（score_news / score_regime 等）
   - オプション（デフォルトあり）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...）
5. DuckDB データベースの作成・監査 DB 初期化（必要に応じて）
   - 監査用 DB を初期化する例は下記の「使い方」参照

例: .env の最低構成例
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（サンプル）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

1) DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

2) ニューススコアリング（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, date(2026, 3, 20))
```

4) 監査ログ用 DB 初期化（別ファイルで管理する場合）
```python
from pathlib import Path
import duckdb
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)  # テーブルとインデックスを作成して接続を返す
```

5) リサーチ用ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
# 結果は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
```

6) カレンダー管理
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI を使う関数は環境変数 OPENAI_API_KEY または api_key 引数で API キーを渡す必要があります。
- J-Quants API を使う関数は JQUANTS_REFRESH_TOKEN を設定しておくと get_id_token() で自動的にトークン取得できます。
- ETL は部分的に失敗しても他のステップを継続する設計です。戻り値の ETLResult を確認してください。

---

## 自動 .env のロード

kabusys.config モジュールは自動でプロジェクトルート（.git または pyproject.toml を探索）から `.env` および `.env.local` を読み込みます。優先順位は
OS 環境変数 > .env.local > .env です。

自動ロードを無効化する場合:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数が未設定の場合、Settings のプロパティ呼び出しで ValueError が発生します。

---

## ログと実行モード

- KABUSYS_ENV によって動作モードを切り替えられます（development / paper_trading / live）。
- LOG_LEVEL でログレベルを制御します（DEBUG/INFO/...）。
- 監視閾値（CPU/MEM/DISK）は環境変数で調整可能（CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT）。

---

## ディレクトリ構成（概略）

プロジェクト内部は `src/kabusys` 以下にモジュールが配置されています。主要ファイルは以下の通りです。

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py            # ニュースセンチメント（score_news）
  - regime_detector.py     # 市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - calendar_management.py
  - etl.py                 # ETL 結果型のエクスポート
  - pipeline.py            # ETL パイプライン（run_daily_etl 等）
  - stats.py               # 統計ユーティリティ（zscore_normalize 等）
  - quality.py             # データ品質チェック
  - audit.py               # 監査ログテーブル定義・初期化
  - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py      # RSS 収集・正規化・保存
- src/kabusys/research/
  - __init__.py
  - factor_research.py     # Momentum / Value / Volatility 等
  - feature_exploration.py # 将来リターン / IC / 統計サマリー等

（上記は重要なモジュールの抜粋です。実際のリポジトリにはさらにサブモジュール・テスト等があることがあります。）

---

## 開発・テスト

- 自動ロードされる .env を使う場合は `.env.example` を参考に必要な値を設定してください（リポジトリに .env.example がある想定）。
- 外部 API を使う箇所（OpenAI / J-Quants / RSS）についてはユニットテスト時にモックして実行する設計になっています（モジュール内関数を patch できるように実装されています）。
- DuckDB のインメモリ接続（":memory:"）を使うとテストが容易です。

---

もし README に追加したい「実行スクリプト」「デプロイ手順」「CI 設定」「より詳細な .env.example」などがあれば、コードベースや運用方針に合わせて追記します。必要な情報（例えば pyproject.toml / requirements.txt の有無、実運用サーバの起動方法など）を教えてください。