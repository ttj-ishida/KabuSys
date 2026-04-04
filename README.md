# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL、データ品質チェック、ニュース収集と NLP による銘柄スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような機能群を持つモジュール群から構成されています。

- データ取得・ETL（J-Quants API からの株価・財務・カレンダー取得、DuckDB へ保存）
- ニュース収集（RSS → raw_news）
- ニュース NLP（OpenAI を用いたセンチメント/銘柄スコアリング）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアを合成）
- データ品質チェック（欠損・重複・スパイク・日付不整合検査）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用のスキーマ初期化ユーティリティ
- 環境変数管理（.env の自動ロード機能）

設計上の特徴：
- ルックアヘッドバイアスを防ぐ（内部で date.today() を直接参照しない箇所がある等）
- DuckDB をデータストアに利用（ローカル／インメモリ対応）
- OpenAI（gpt-4o-mini 想定）との連携機能あり（API 呼び出しはリトライ・フォールバックあり）
- ETL・品質チェックはステップ単位で堅牢にエラーハンドリング

---

## 主な機能一覧

- kabusys.config: .env ファイルまたは環境変数から設定を読み込み、Settings オブジェクトを提供
- kabusys.data.jquants_client:
  - J-Quants API からのデータ取得（株価・財務・カレンダー）
  - DuckDB への冪等保存関数（save_daily_quotes 等）
- kabusys.data.pipeline:
  - run_daily_etl: 日次 ETL の統合実行（カレンダー → 株価 → 財務 → 品質チェック）
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- kabusys.data.news_collector:
  - RSS 収集、前処理、raw_news への保存
- kabusys.data.quality:
  - 欠損・重複・スパイク・日付不整合の検出
- kabusys.ai.news_nlp:
  - ニュースを銘柄ごとに集約して OpenAI に投げ、ai_scores テーブルへ書き込む（score_news）
- kabusys.ai.regime_detector:
  - ETF（1321）の 200 日 MA 乖離とマクロニュース LLM スコアを合成して market_regime テーブルへ書き込む（score_regime）
- kabusys.research:
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン・IC 計算・統計サマリー等のユーティリティ
- kabusys.data.audit:
  - 監査ログ用スキーマの初期化（init_audit_schema / init_audit_db）

---

## 動作要件（推奨）

- Python 3.10 以上（PEP 604 の union 型などを使用）
- DuckDB
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全対策）
- 標準ライブラリの urllib を利用（追加 HTTP ライブラリ不要）

推奨インストール（requirements.txt を用意する想定）:
- duckdb
- openai
- defusedxml

例:
```
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／コードを配置
2. Python 仮想環境を作成・有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
     - KABU_API_PASSWORD: kabuステーション連携用パスワード（使用する場合）
   - 任意:
     - KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL

   例 `.env`（必須値は適宜設定してください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベースの準備
   - DuckDB ファイル（デフォルトは data/kabusys.duckdb）を使用します。必要に応じてディレクトリを作成してください。
   - 監査ログ用 DB を別に用意する場合は kabusys.data.audit.init_audit_db を使用できます（引数にパス文字列）。

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL での使用例です。

- Settings を参照する
```
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続と日次 ETL 実行
```
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコア（AI）を実行
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で env の OPENAI_API_KEY を使用
print(f"scored {count} codes")
```

- 市場レジームスコアを算出
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ（Audit）スキーマの初期化
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
```

- ファクター計算 / リサーチユーティリティ
```
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

注意点:
- score_news / score_regime は OpenAI API キー（OPENAI_API_KEY または api_key 引数）が必要です。API 呼び出しの失敗時はフォールバック動作（0.0 スコア等）がありますが、API キーが未設定の場合は ValueError を発生させます。
- ETL 実行や DB 書き込みはトランザクション制御を行っていますが、DuckDB のバージョン依存の振る舞いに注意してください（コード内に互換性考慮の実装あり）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY (score_news / regime_detector に必要)
- KABU_API_PASSWORD (kabu API 使用時)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB 用、デフォルト: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（検証済み値）
- LOG_LEVEL: DEBUG/INFO/etc
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化

設定は .env / .env.local に記述できます（config モジュールが自動でプロジェクトルートから読み込みます）。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下に主要モジュールを配置しています。主要ファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                 # .env / 環境変数管理
  - ai/
    - __init__.py
    - news_nlp.py             # ニュース NLP スコアリング（score_news）
    - regime_detector.py      # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント + DuckDB保存
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - news_collector.py       # RSS 取得・前処理
    - quality.py              # データ品質チェック
    - calendar_management.py  # 市場カレンダー管理（営業日判定等）
    - audit.py                # 監査ログスキーマ初期化
    - stats.py                # 統計ユーティリティ（zscore_normalize 等）
    - etl.py                  # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py      # ファクター計算（momentum / value / volatility）
    - feature_exploration.py  # 将来リターン / IC / summary 等
  - ai/、research/、data/ 以下にさらに補助関数や内部ユーティリティが含まれます

---

## 開発者向けメモ

- .env 読み込みルール:
  - プロジェクトルートを .git または pyproject.toml から探索
  - 読み込み順序: OS 環境変数 > .env > .env.local（.env.local は override=True）
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- OpenAI 呼び出しや外部 API 呼び出しはリトライ・エラーハンドリングが組み込まれています。ユニットテストでは該当内部関数をモックすることを想定しています（例: news_nlp._call_openai_api をパッチする等）。
- DuckDB の executemany の挙動やバージョン差分に注意（コード内で互換性対策を実施）。

---

## 参考・補足

- 本 README はコードベースの主要 API と使い方を簡潔にまとめたものです。細かな実装や挙動は各モジュールの docstring / コメントを参照してください（コード内に設計方針・フォールバック・ログ戦略等の説明が記載されています）。
- セキュリティ: RSS の取得は SSRF を考慮した検査を行い、defusedxml を利用しています。外部キーや監査ログは削除を想定せずトレーサビリティを重視しています。

---

必要であれば、README に含める具体的な .env.example、requirements.txt のサンプル、またはよく使う CLI スクリプト（ETL を定期実行する systemd / cron の例）も作成します。どれを追加しましょうか？