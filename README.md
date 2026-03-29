# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（内部ユーティリティ群）

簡単な説明:
- 株価・財務・ニュースの ETL、データ品質チェック、マーケットカレンダー管理
- ニュースの LLM ベースセンチメント解析（OpenAI）
- 市場レジーム判定（MA200 + マクロニュース）
- 研究用ファクター計算・前方リターン・IC 計算
- 監査ログ（signal → order → execution のトレーサビリティ）
- J-Quants API クライアント（取得・保存・レート制御・リトライ・トークンリフレッシュ）

設計上のポイント:
- Look-ahead バイアスに配慮（内部で date.today() 等を不用意に参照しない設計）
- DuckDB を中核 DB として利用、保存は冪等（ON CONFLICT 等）
- 外部 API 呼び出しにはリトライ・レート制御を実装
- セキュリティ考慮（RSS の SSRF 対策、XML パースの安全化 等）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを取得（fetch_*）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果を表す ETLResult

- データ品質管理
  - 欠損チェック / スパイク検出 / 重複チェック / 日付整合性チェック（quality.run_all_checks）

- ニュース収集・NLP（AI）
  - RSS 取得・前処理・raw_news への保存ロジック（news_collector）
  - LLM によるニュースセンチメント付与（ai.news_nlp.score_news）
  - 市場マクロセンチメントと MA200 を用いた市場レジーム判定（ai.regime_detector.score_regime）

- リサーチ用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブル定義・初期化（冪等）
  - init_audit_schema / init_audit_db

- 設定管理
  - 環境変数・.env 読み込みユーティリティ（kabusys.config）
  - 自動 .env ロード（プロジェクトルートを .git または pyproject.toml で探索）
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要な環境変数

必須（実行する機能に応じて必要なものを用意してください）:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（jquants_client.get_id_token で使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知を使う場合
- OPENAI_API_KEY : OpenAI を使う AI 機能（news_nlp / regime_detector）
- KABU_API_PASSWORD : kabuステーション API を使う場合

任意 / デフォルトあり:
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると自動 .env 読み込みを無効化
- KABUSYS が参照する DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）

.env の扱い:
- プロジェクトルートにある `.env` と `.env.local` を読み込む（OS 環境変数優先）
- 自動ロードされないようにする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定

---

## セットアップ手順

1. Python を用意（推奨: 3.10+）
2. リポジトリをチェックアウト
3. 依存パッケージ（例 — 必要なものを pip 等で追加してください）
   - duckdb
   - openai
   - defusedxml
   - そのほか urllib / datetime 等は標準ライブラリ
   例:
   ```
   python -m pip install duckdb openai defusedxml
   ```
   （requirements.txt がある場合はそちらを利用してください）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数に設定してください。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB ファイル/ データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下はライブラリを直接インポートして利用する最小の使用例です。実行前に必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する:
```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアを付与する（OpenAI API キーが必要）:
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} symbols")
```

- 市場レジームを判定して保存する（OpenAI API キーが必要）:
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する:
```
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへアクセス可能
```

- カレンダー系ユーティリティの使用例:
```
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect('data/kabusys.duckdb')
d = date(2026, 4, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI を用いる関数は network / API エラー時にフェイルセーフ（多くの場合 0 やスキップ）となる設計だが、API キーが未設定の場合は ValueError が発生します。
- ETL / 保存処理は冪等設計（ON CONFLICT）です。部分失敗時のロールバックやリトライ動作は各関数のドキュメントを参照してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル・モジュール構成:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（LLM）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS 収集 / 前処理
    - calendar_management.py — マーケットカレンダー管理
    - quality.py             — 品質チェック
    - stats.py               — 統計ユーティリティ（zscore 等）
    - audit.py               — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/regime_detector.py
  - ...（その他ユーティリティファイル）

この README は主要なモジュールと使い方の概要を示しています。各モジュールはモジュール内の docstring に詳細な設計方針・引数説明が含まれていますので、実装や拡張時はソース内ドキュメントを参照してください。

---

## 追加の注意事項 / ベストプラクティス

- テスト実行時に自動 .env ロードを無効化する:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しはテストしやすいように内部 API 呼び出し関数をモックできるように実装されています（unittest.mock.patch 等で差し替え可能）。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、モジュール側で空チェックが実装されています。
- 本ライブラリはバックテスト等での look-ahead を避ける設計になっています。バックテストで使用する場合は各関数の注記に従ってください（例: data 取得タイミング、fetched_at の扱い）。

---

必要であれば、この README をプロジェクトの README.md として調整（依存関係の詳細、導入ガイド、CI 設定例、実運用での注意点など）して拡張できます。特にどの点を詳しくしたいか教えてください。