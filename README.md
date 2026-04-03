# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム兼リサーチ／自動売買支援ライブラリです。J-Quants／RSS／OpenAI など外部データを取り込み、ETL、データ品質チェック、ニュース NLP、マーケットレジーム判定、ファクター計算、監査ログなどのユーティリティを提供します。

主な用途
- J-Quants からの株価・財務・カレンダーの差分 ETL
- ニュース記事の収集と LLM を用いた銘柄センチメントスコアリング
- ETF とマクロニュースを用いた市場レジーム判定（bull/neutral/bear）
- ファクター（モメンタム / ボラティリティ / バリュー 等）の計算・探索
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査（シグナル→発注→約定）用のデータベーススキーマ初期化

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API/コマンド例）
- ディレクトリ構成

---

プロジェクト概要
- 設計方針の概略
  - ルックアヘッドバイアスに配慮（内部で datetime.today() 等を不用意に参照しない）
  - DuckDB をデータストアとして利用（軽量かつ高速な分析用データベース）
  - 外部 API 呼び出しはリトライやレート制御、フェイルセーフを備える
  - ETL は差分更新・バックフィルをサポートし品質チェックを実行
  - 監査ログは冪等・タイムスタンプ・UUID 連鎖でトレース可能にする

---

機能一覧
- データ取得・保存
  - J-Quants クライアント（fetch/save daily_quotes, financial_statements, market_calendar）
  - RSS ニュース収集（前処理・SSRF/サイズ対策・冪等保存）
- ETL
  - run_daily_etl: calendar / prices / financials の差分 ETL + 品質チェック
  - 個別 ETL ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- 品質チェック
  - 欠損データ、スパイク（急変）、重複、日付不整合の検出
- AI（OpenAI）連携
  - news_nlp.score_news: ニュースを LLM で銘柄別にセンチメント評価して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込む
  - LLM 呼び出しは JSON Mode を使い、429/タイムアウト/5xx のリトライ処理あり
- リサーチ
  - ファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査（Audit）
  - signal_events / order_requests / executions の DDL とインデックス
  - init_audit_schema / init_audit_db によるスキーマ初期化
- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルートの .git または pyproject.toml を基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
  - Settings クラス経由でアプリ設定にアクセス可能（例: settings.jquants_refresh_token）

---

セットアップ手順（開発環境の例）
1. 必要条件
   - Python 3.10+（本コードは型ヒントや union 型（|）を使用）
   - DuckDB, OpenAI SDK, defusedxml などのライブラリ

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux)
   - .venv\Scripts\activate (Windows)

3. パッケージインストール（例）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   ※ 実運用ではプロジェクトに requirements.txt / pyproject.toml を用意して pip install -e . 等で依存管理してください。

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を配置すると自動読み込みされます。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=（必須：J-Quants リフレッシュトークン）
     - OPENAI_API_KEY=（LLM 利用時に必須）
     - KABU_API_PASSWORD=（kabu API を利用する場合）
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - LINE_CHANNEL_ACCESS_TOKEN=（通知用、任意）
     - LINE_USER_ID=（任意）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - .env の構文はシェル形式（export 可）で、クォートやコメントも柔軟に扱えます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

使い方（主要 API とサンプル）
以下は簡単な Python インタラクティブ・スニペット例です。実行前に必要な環境変数を設定してください（特に JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY）。

共通インポート例
```python
from datetime import date
import duckdb
from kabusys.config import settings
```

1) DuckDB 接続（既定のパスを使用）
```python
conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL 実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのスコアリング（LLM を使って ai_scores に書き込む）
```python
from kabusys.ai.news_nlp import score_news
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か引数で指定
print("書き込み銘柄数:", n_written)
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数で解決
```

5) 監査 DB の初期化（独立した audit DB を作成して接続を返す）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# DB とスキーマが作成されます（UTC タイムゾーンを設定）
```

6) 監査スキーマのみ既存接続に適用
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

7) ファクター計算・リサーチ関数の呼び出し例
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
moms = calc_momentum(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
```

補足
- OpenAI クライアントは gpt-4o-mini（コード内で指定）を想定しています。API キーは OPENAI_API_KEY 環境変数に設定するか、各関数の api_key 引数で渡してください。
- J-Quants API は settings.jquants_refresh_token を用いて get_id_token() で ID トークンを取得します。

---

設定 / 環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY (LLM 機能利用時に必須)
- KABU_API_PASSWORD (kabu API を利用する場合)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (通知設定)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH（監視用ファイルパス）
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動読み込みを無効化可能

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                パッケージエントリ（version 等）
  - config.py                  環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py              ニュース → 銘柄センチメント（LLM）
    - regime_detector.py       ETF + マクロニュースによる市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        J-Quants API client（取得・保存ロジック）
    - pipeline.py              ETL（run_daily_etl 等）
    - etl.py                   ETLResult 再エクスポート
    - news_collector.py        RSS 取得・前処理・保存
    - calendar_management.py   市場カレンダー管理（営業日判定等）
    - quality.py               データ品質チェック
    - stats.py                 汎用統計ユーティリティ（z-score）
    - audit.py                 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py       モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py   将来リターン / IC / 統計サマリー 等
  - execution/                  （発注・約定関連モジュール想定：コード省略）
  - monitoring/                （監視・プロセスマネジメント想定：コード省略）

---

運用上の注意
- 外部 API の呼び出し（J-Quants, OpenAI）にはレート制御・リトライが組み込まれていますが、API 利用料金や制限は利用者側で把握してください。
- ETL は差分更新を基本としています。初回ロード時はデータ開始日（_MIN_DATA_DATE）が設定されています。
- LLM 呼び出しは JSON Mode を使用しレスポンスパースに堅牢性を持たせていますが、実運用ではモデルの挙動変化に注意してください。
- 監査ログは削除しない前提です。ディスクサイズの監視・バックアップポリシーを用意してください。
- settings.env の値チェック（KABUSYS_ENV, LOG_LEVEL）で不正値は例外になります。

---

開発・拡張
- テスト時は config の自動 .env ロードを無効化するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 呼び出しや外部接続部分はモック可能（内部呼び出し関数を patch する設計になっています）。
- DuckDB を使った SQL 部分は基本的に SQL クエリで表現されており、拡張は容易です。

---

問い合わせ / コントリビュート
- 本 README はコードコメント・ドキュメントに基づき生成しています。仕様変更の際は対応するモジュール（特に data/jquants_client.py、ai/*.py、data/pipeline.py）を参照・更新してください。

以上。必要であれば、README にサンプル .env.example、依存関係の pinning（requirements.txt）や簡易起動スクリプト（scripts/）のテンプレートを追加します。どれを追加しますか？