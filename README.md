# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォームライブラリです。  
ETL（J-Quants 経由の株価・財務・マーケットカレンダー取得）、ニュース収集・NLP（OpenAI を利用した銘柄センチメント）、市場レジーム判定、リサーチ用ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）等の機能を提供します。

バージョン: 0.1.0

---

## 主要機能（抜粋）

- データ取得・ETL
  - J-Quants API からの株価日足・財務データ・上場情報・マーケットカレンダー取得（ページネーション・レート制御・自動リフレッシュ対応）
  - DuckDB への冪等保存（ON CONFLICT ベース）
  - 日次 ETL パイプライン（run_daily_etl）と個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース収集・前処理
  - RSS フィード取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP / AI
  - 銘柄単位のニュースセンチメント算出（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロ記事センチメントの合成）→ market_regime へ保存（score_regime）
  - OpenAI (gpt-4o-mini) を JSON mode で利用。エラー時はフェイルセーフ（スコア 0 など）
- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー、Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などのチェック（run_all_checks）
  - QualityIssue 型で詳細を返す
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等の監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env（.env.local 優先）または環境変数から設定を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクトで各種設定を参照可能（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY / KABU_API_PASSWORD / SLACK_* など）

---

## 必要条件

- Python 3.10+
- 主要依存（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS フィード, OpenAI）

（実際のプロジェクトでは requirements.txt や pyproject.toml を用意してください）

---

## セットアップ手順（ローカル開発向け）

1. 仮想環境を準備
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml からインストールしてください。

3. 環境変数 / .env ファイルを準備
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` または `.env.local` を配置すると自動ロードされます。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース用ディレクトリ作成
   - デフォルトでは `data/` 配下に duckdb ファイル等を作成します。必要に応じてディレクトリを作成してください。
     - DUCKDB_PATH のデフォルト: data/kabusys.duckdb
     - SQLITE_PATH のデフォルト: data/monitoring.db

---

## 使い方（簡易サンプル）

以下は主要な API 利用例です。いずれも duckdb の接続オブジェクト（duckdb.connect(...) の返り値）を使います。

- 日次 ETL の実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントの算出（OpenAI API キーが環境変数に必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み件数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（専用ファイル）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

- リサーチ系（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 設定参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"

注意: settings は .env / .env.local を自動ロードします。`.env.local` は既存環境変数を上書きします（OS 環境変数は保護されます）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）

（このコードベースに基づく想定構成）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - calendar_management.py
      - pipeline.py
      - etl.py
      - jquants_client.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py (ETLResult の定義)
      - etl.py (ETL 公開インターフェース)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
      - feature_exploration.py
      - factor_research.py
    - (その他) strategy/, execution/, monitoring/ などパッケージ参照あり（将来的な拡張想定）

---

## 実運用・注意点

- OpenAI 呼び出しは外部 API に依存するため、API レート制限やコストを考慮してください（モデル名: gpt-4o-mini を使用）。
- J-Quants API へのリクエストはレート制御・リトライ・401 リフレッシュが組み込まれていますが、ID トークンやリフレッシュトークンは適切に管理してください。
- DuckDB を DB として使用しています。大規模データの取り扱いや並列アクセスの要件がある場合は運用設計に注意してください。
- ニュース収集周りは SSRF / XML Bomb / 大容量レスポンス対策を実装していますが、追加のセキュリティポリシーが必要な場合は拡張してください。
- テストを書く際は OpenAI / HTTP 呼び出し箇所をモック（patch）して外部依存を切り離すことを推奨します（コード内でもテストしやすいようにコール箇所を抽象化しています）。

---

## 貢献

バグ報告、機能提案、PR を歓迎します。開発・デプロイ時は以下を考慮してください:
- 機密情報（API キー等）はリポジトリにコミットしないこと
- .env.example を用意して必要な環境変数を明示すること
- 単体テストで外部 API をモックすること

---

README の内容は該当コードベース（src/kabusys）を参照してまとめています。追加の要望（例: CI 設定、詳細な API 仕様、.env.example の作成など）があれば教えてください。