# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のライブラリです。  
DuckDB をデータ層に用い、J-Quants からのデータ収集、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、ETL パイプライン、監査ログ（トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

## 主な特徴
- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- ニュース収集（RSS）と OpenAI による銘柄別センチメントスコアリング
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを融合）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）
- 環境変数 / .env ベースの設定管理（自動読み込み対応）

---

## 機能一覧（抜粋）
- kabusys.data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch / save）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days）
  - ニュース収集 / 前処理（RSS の安全な取得、SSRF 対策）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログ初期化（init_audit_schema, init_audit_db）
- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースから銘柄ごとにセンチメントを算出して ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None): 市場レジームを判定して market_regime に保存
- kabusys.research
  - factor 計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量評価（calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.config
  - Settings クラスによる環境変数アクセス。自動で .env / .env.local をロード（プロジェクトルート検出）

---

## 動作要件（主な外部依存）
- Python 3.10+（型アノテーションに union | を利用）
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- その他標準ライブラリ（urllib, datetime, json など）

必要に応じて pyproject.toml や requirements.txt から依存を確認してください。

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 環境変数 / .env を用意する  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に自動で `.env` と `.env.local` が読み込まれます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必要に応じて）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必要に応じて）

   任意 / デフォルト
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. データベースディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

以降のサンプルでは Python スクリプトや REPL から実行する前提です。必要に応じてファイルに保存して cron / バッチで実行してください。

共通：DuckDB 接続と Settings 取得
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI が必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください
written_count = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {written_count}")
```

3) 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査用に別 DB にすることを推奨）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit_duckdb.db"))
# またはメイン DB に追加したい場合は既存 conn に対して init_audit_schema(conn)
```

5) ファクター計算・研究ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

---

## 設定（Settings）について
- `kabusys.config.settings` にアプリ設定がまとまっています。プロパティ経由で値にアクセスしてください（例: settings.jquants_refresh_token）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。`.env` → `.env.local` の順で読み込み、OS 環境変数が優先されます。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主なファイルと概要）
（package のルートは src/kabusys です）

- src/kabusys/
  - __init__.py                     - パッケージ初期化（__version__）
  - config.py                        - 環境変数 / .env ロード・Settings
  - ai/
    - __init__.py                    - ai モジュール公開関数
    - news_nlp.py                    - ニュース NLP スコアリング（score_news）
    - regime_detector.py             - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              - J-Quants API クライアント（fetch/save 等）
    - pipeline.py                    - ETL パイプライン（run_daily_etl 等）
    - etl.py                         - ETLResult の re-export
    - news_collector.py              - RSS ニュース収集（SSRF 対策等）
    - calendar_management.py         - 市場カレンダー管理（is_trading_day 等）
    - quality.py                     - データ品質チェック
    - stats.py                       - 統計ユーティリティ（zscore_normalize）
    - audit.py                       - 監査ログスキーマ初期化（init_audit_db 等）
  - research/
    - __init__.py
    - factor_research.py             - ファクター計算
    - feature_exploration.py         - 将来リターン、IC、統計サマリー
  - research/*.py                    - 研究用ユーティリティ群

---

## ロギング / 実運用の注意点
- ログレベルは環境変数 `LOG_LEVEL` で設定できます（設定は settings.log_level）。
- KABUSYS_ENV は運用モードを切り替えます（development / paper_trading / live）。発注や実口座アクセス時の安全チェックに利用してください。
- OpenAI の呼び出しと J-Quants API にはそれぞれレート制御／リトライの実装がありますが、実運用では API キー管理・コスト管理・テスト用のモックを適切に行ってください。
- DuckDB に対する大量挿入は executemany を利用しています。DuckDB のバージョン（0.10 等）による挙動差に注意してください（コード内で対処済みの箇所あり）。

---

## 開発 / テスト
- モジュールの一部（OpenAI 呼び出し等）はテストしやすいように内部呼び出しを差し替えられるよう設計されています（ユニットテストではモック化してください）。
- .env を使った設定読み込みに依存する場合、テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で環境を注入することが可能です。

---

## ライセンス・貢献
README に記載のない利用規約やライセンス情報はリポジトリのトップレベルにある LICENSE 等を参照してください。バグ報告や機能追加の提案は Issue / Pull Request を通じてお願いします。

---

必要であれば、README に含める .env.example の具体的なテンプレートや、デプロイ（systemd / Airflow / Cloud Run 等）サンプル、テストの実行方法（pytest）などを追加で作成します。どの情報を優先的に追加しますか？