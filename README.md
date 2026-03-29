# KabuSys

日本株自動売買プラットフォームのライブラリ群。データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログなどを含むモジュール群を提供します。

主な設計方針は次のとおりです。
- ルックアヘッドバイアス回避（関数内で datetime.today()/date.today() に依存しない）
- DuckDB を用いたローカルデータプラットフォーム
- 外部 API 呼び出しにはリトライ / レート制御 / フェイルセーフを備える
- 冪等性を重視（DB 保存は ON CONFLICT での上書き 等）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート基準）
  - 必須環境変数チェックを行う Settings API

- データ取得 / ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得
  - 差分更新、ページネーション、認証トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）

- データ品質チェック
  - 欠損データ、主キー重複、スパイク（急騰/急落）、日付不整合チェック
  - QualityIssue 型で問題の詳細を返却

- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 対策、gzip対応、サイズ上限、URL 正規化）
  - raw_news への冪等保存、銘柄紐付けサポート

- ニュース NLP（OpenAI）
  - 銘柄毎ニュースの統合センチメント（gpt-4o-mini / JSON mode）
  - チャンク処理、リトライ、レスポンス検証、スコアクリップ

- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を混成
  - LLM を用いたマクロセンチメント（フェイルセーフで 0.0 にフォールバック）

- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）の算出、Zスコア正規化、統計サマリー

- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等の監査テーブル定義と初期化ユーティリティ
  - order_request_id を冪等キーとして二重発注を防止

---

## セットアップ手順

前提
- Python 3.10 以上推奨（typing の union と | を使用）
- 外部サービス利用には各種 API キーが必要（詳細は環境変数参照）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 依存パッケージをインストール  
   ※ requirements.txt はプロジェクトに合わせて用意してください。主要な依存例:
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定  
   プロジェクトルート（.git または pyproject.toml のある場所）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   必須（本番/運用で必要なもの）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack Bot トークン
   - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 時に利用）

   任意 / デフォルトあり
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment（development|paper_trading|live）
   - LOG_LEVEL: (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB 初期化（監査ログ用）
   Python から初期化関数を使えます（例は下記「使い方」を参照）。

---

## 使い方（主要な例）

以下はライブラリを使うための Python 例です。実行前に必要な環境変数を設定してください。

- DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しない場合は今日が対象（内部処理は営業日に調整される）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）スコアを生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査DB を初期化して接続を得る
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb.db")
# または ":memory:" を渡してインメモリ DB を初期化
```

- J-Quants API クライアントを直接呼ぶ（例: 上場情報取得）
```python
from kabusys.data.jquants_client import fetch_listed_info, get_id_token
# get_id_token() は settings.jquants_refresh_token を参照して id_token を取得します
listed = fetch_listed_info()
print(len(listed))
```

注意点
- OpenAI への呼び出しは gpt-4o-mini と JSON Mode を想定しています。レスポンスは JSON のバリデーションが行われ、失敗時はフェイルセーフとして 0.0（中立）などにフォールバックします。
- ETL / データ取得系は自動リトライ・レート制御を実装していますが、API 利用上限・課金等には注意してください。

---

## 自動 .env 読み込みの挙動

- 起点はモジュールのファイル位置（__file__）から親ディレクトリを上に辿り、`.git` または `pyproject.toml` のあるディレクトリをプロジェクトルートとみなします。
- 読み込み順序（優先度）:
  1. OS 環境変数（最優先）
  2. .env.local（上書き：override=True）
  3. .env（override=False）
- 自動ロードを無効にする場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なモジュールは `src/kabusys` 配下にあります。主なファイル/パッケージ:

- kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py               — ニュースセンチメント生成（score_news）
    - regime_detector.py        — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - etl.py                    — ETLResult の再エクスポート
    - quality.py                — データ品質チェック
    - news_collector.py         — RSS ニュース収集
    - calendar_management.py    — 市場カレンダー管理（営業日判定等）
    - stats.py                  — 統計ユーティリティ（zscore_normalize）
    - audit.py                  — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py        — Momentum / Value / Volatility 等
    - feature_exploration.py    — 将来リターン / IC / summary / rank

付記:
- 各モジュールは DuckDB 接続オブジェクトを引数として受け取り、SQL と Python を組み合わせて処理する設計です。
- AI 関連の関数は API キーの引数注入をサポートしており、テストでの差し替えが行いやすく実装されています（内部の _call_openai_api をモックする等）。

---

## 運用上の注意

- KABUSYS_ENV によって挙動（特に発注まわり）が分岐する想定です。利用可能な値: `development`, `paper_trading`, `live`。誤った値は設定エラーになります。
- 実際に発注するモジュール（execution 等、今回提示コードには発注実装は含まれていません）は、必ず paper_trading モードなどで事前検証してください。
- AI / 外部 API 呼び出しはコストが発生します。ローカルテストでは環境変数や API 呼び出しのモックを推奨します。
- DuckDB/SQLite のパスは settings で管理されます。バックアップ・権限・ローテーション等は運用で考慮してください。

---

README はここまでです。実装の詳細や追加のユーティリティ、CI / DB スキーマ定義（schema 初期化スクリプト等）が必要であれば続けて作成支援します。