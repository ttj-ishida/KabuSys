# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。J-Quants / kabuステーション 等の外部データを取り込み、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ管理などを提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants API から日次株価（OHLCV）、財務データ、JPX カレンダー取得
  - 差分取得・バックフィル・冪等保存（DuckDB への ON CONFLICT 処理）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue 型で問題を収集
- ニュース収集・NLP
  - RSS 取得・正規化・SSRF 対策（defusedxml、URL 正規化）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF MA200 を使った市場レジーム判定（score_regime）
- リサーチ用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルとインデックスの初期化
  - init_audit_schema / init_audit_db による冪等初期化
- 設定管理
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準）
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## 必要環境 / 依存

- Python 3.10 以上（typing の | 演算子などを利用）
- ライブラリ（代表）
  - duckdb
  - openai
  - defusedxml
- （ネットワークアクセス）J-Quants API、OpenAI API を利用する場合はそれぞれの認証情報が必要

インストール例:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
# またはプロジェクトに requirements.txt がある場合: pip install -r requirements.txt
# 開発中: pip install -e .
```

---

## 環境変数（主なもの）

以下は本プロジェクトで参照される主な環境変数の一覧です（.env を利用する想定）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API の base URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用途）のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動で .env を読み込まない

自動 .env ロードは、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を順に読み込む挙動です。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 (.env):
```env
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. Python をインストール（3.10+）
2. 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存をインストール
   - pip install duckdb openai defusedxml
   - 追加で必要なパッケージがあれば適宜インストール
4. リポジトリルートに `.env` を作成（.env.example を参照してコピー）
5. データディレクトリを作成（必要であれば）
   - mkdir -p data
6. DuckDB を使う場合、初回はスキーマや監査テーブルを初期化（下記参照）

---

## 使い方（代表的な例）

以下は最低限の利用例です。すべて Python API を直接呼び出す想定です。

- DuckDB 接続の作成（ファイルパスは settings.duckdb_path を参照できます）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースセンチメントのスコア取得（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、第3引数で渡す
count = score_news(conn, target_date=date(2026,3,20))
print("scored:", count)
```

- 市場レジームスコア計算（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算（研究）
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査用 DB を別ファイルで用意する場合
audit_conn = init_audit_db(settings.duckdb_path)  # または別パス
# あるいは既存の conn に対して init_audit_schema(conn) を呼ぶ
```

注意点:
- OpenAI を使う関数は api_key を引数で渡すこともできます（テストやキーを切り替えたい場合）。
- 内部では date.today() / datetime.today() を極力直接参照しておらず、関数呼び出し時に target_date を明示することが推奨されています（ルックアヘッドバイアス対策）。
- ETL・API 呼び出しはネットワークと API レート制限に依存します。J-Quants はレート制限があり、クライアント実装で制御されていますが、実行頻度は運用に合わせて調整してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 配下に実装がまとまっています。主なファイルと役割を列挙します。

- src/kabusys/__init__.py
  - パッケージのバージョン・公開モジュール定義
- src/kabusys/config.py
  - 環境変数・設定管理（.env 自動読み込み、Settings オブジェクト）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py — ニュースの NLP スコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save 関数）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult 型
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - news_collector.py — RSS 取得・前処理・保存
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログテーブルの DDL/初期化
- src/kabusys/research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum / value / volatility）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

（上記は主要実装のみ。実際のリポジトリには他にも補助モジュール・ユーティリティが含まれる可能性があります）

---

## 運用上の注意

- 認証情報（API キー等）は決して公開リポジトリにコミットしないでください。`.env` は .gitignore に追加することを推奨します。
- OpenAI / J-Quants など外部 API 利用時のレート制限や課金に注意してください。score_news / score_regime は OpenAI 呼び出しを行います。
- ETL 実行はディスク IO（DuckDB）やネットワークに依存します。運用ではログレベルの監視や失敗時の再実行戦略を用意してください。
- 自動 .env ロードはプロジェクトルート検出に .git または pyproject.toml を使います。パッケージ配布後や特定環境では KABUSYS_DISABLE_AUTO_ENV_LOAD により制御してください。

---

## 追加情報 / 参考

- 設計方針や細かな挙動（ルックアヘッドバイアス回避、エラーハンドリング、冪等性の考慮など）は各モジュールの docstring に詳細が記載されています。実装を変更する際はコメントや docstring を参照してください。
- さらに詳しい使用例や運用スクリプト（cron / Airflow 等）はプロジェクト固有の運用ドキュメントを参照してください。

---

不明点や README に追記してほしい点があれば教えてください。必要であればサンプル .env.example や運用スクリプト例も作成します。