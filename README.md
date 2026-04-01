# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコア、ファクター計算、監査ログ（トレーサビリティ）、マーケットカレンダー管理など、トレーディングシステム実装に必要な機能群を提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「DB（DuckDB）中心の処理」「外部 API 呼び出しの堅牢化（リトライ・レート制御等）」です。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定/読み込み
  - .env / .env.local を自動読み込み（OS 環境変数を優先）。読み込み無効化オプションあり。
- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー等）
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 市場カレンダー管理（営業日判定・前後営業日検索）
  - ニュース収集（RSS → raw_news）
  - 監査ログスキーマ初期化 / 監査 DB（audit）
- AI（kabusys.ai）
  - ニュース NLP（銘柄ごとのセンチメントスコアを ai_scores に保存する score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成する score_regime）
  - OpenAI（gpt-4o-mini）を用いた JSON mode 呼び出し、リトライ・フォールバック実装
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン計算、IC、統計サマリー、ランク変換）
- 汎用ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - 各種 DB 保存処理（冪等化）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に PEP 604 の `X | Y` を使用）。
- システムに pip と virtualenv 等がインストールされていること。

1. レポジトリをクローン（例）
   - git clone <repo-url>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 本コードで使用している主要パッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   - パッケージを開発モードでインストールする場合（プロジェクトに setup/pyproject があれば）:
     - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を作成してください。
   - 自動読み込みの仕様：OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 認証に使用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注系）
     - SLACK_BOT_TOKEN: Slack 通知用 bot token（通知機能を使う場合）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
   - 任意・デフォルトあり:
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: デフォルト db ファイル path（data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite path（data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / ...（デフォルト INFO）

5. データディレクトリ作成（必要に応じて）
   - settings.duckdb_path の親ディレクトリなどを作成しておくと便利です:
     - mkdir -p data

---

## 使い方（主な呼び出し例）

以下は Python スクリプト / REPL から利用する基本例です。DuckDB の接続はモジュール関数が想定する DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を渡します。

- 設定オブジェクト参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB に接続して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア生成（OpenAI API キー必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は省略可能
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

- 市場レジーム評価（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # ディレクトリを自動作成して接続を返す
```

- RSS フィード取得（ニュース収集の一部を単体で使う場合）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- AI 系関数は OpenAI の JSON mode を利用します。API の失敗時はフェイルセーフ（多くの場合 0 戻り）で処理を継続する設計ですが、API キー未設定だと ValueError を投げます。
- ETL / 保存処理は冪等保存（ON CONFLICT DO UPDATE）を行うため再実行に耐えます。
- 日付操作はルックアヘッドバイアスを避けるため、内部で date.today() / datetime.today() を直接参照しない実装方針になっています（外部から target_date を渡すことが推奨されます）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル群（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                           -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                        -- ニュース NLP（score_news）
    - regime_detector.py                 -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                  -- J-Quants API クライアント・保存関数
    - pipeline.py                        -- ETL パイプラインのエントリ（run_daily_etl 等）
    - etl.py                             -- ETL 結果型再エクスポート等
    - news_collector.py                  -- RSS 収集・前処理
    - calendar_management.py             -- 市場カレンダー管理（is_trading_day 等）
    - quality.py                         -- 品質チェック（missing/spike/duplicates/...）
    - stats.py                           -- 統計ユーティリティ（zscore_normalize）
    - audit.py                           -- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py                 -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py             -- 将来リターン/IC/summary/rank
  - research/... (他ユーティリティ)

補足:
- コードは DuckDB 接続を第一に受け取りデータ参照・変更を行う設計です。DB コネクションは呼び出し元で管理してください。
- news_collector は SSRF 対策、レスポンスサイズ制限、XML パースの安全化（defusedxml）など安全面の実装が組み込まれています。

---

## 運用上の注意・トラブルシューティング

- 環境変数が足りない場合（settings のプロパティで _require を通すもの）は ValueError が発生します。CI/デプロイ時は .env を適切に設定してください。
- J-Quants API のレート制限（120 req/min）をモジュール内で固定間隔レートリミッタにより制御しますが、大量同時実行は避けてください。
- OpenAI 呼び出しは JSON mode を使い、リトライ・パース失敗時はスコアを 0 にフォールバックすることで上位処理の継続性を確保します。API の課金やレートに注意してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン差があるため、コード側で空リストチェックを行っています。DuckDB バージョンを上げた場合も互換性を確認してください。

---

この README はコードベースの主要な利用ポイントをまとめたものです。詳細な API 仕様や運用手順は各モジュールの docstring を参照してください。追加で必要な情報（例: .env.example のテンプレート、CI 実行例、運用スクリプトのサンプル）があれば作成しますので教えてください。