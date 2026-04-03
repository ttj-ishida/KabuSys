# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。J-Quants からの時系列データ取得、ニュース収集・NLP スコアリング、ファクター計算、ETL パイプライン、監査ログスキーマなどを含み、戦略実装や自動売買実行の下支えをします。

主な設計方針:
- ルックアヘッドバイアス対策（内部で date.today() を直接参照しない等）
- DuckDB を中心としたローカル DB 管理（冪等保存・ON CONFLICT 処理）
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフ実装
- 監査ログでシグナル→発注→約定までトレース可能

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（主要）
- 使い方（代表的な呼び出し例）
- ディレクトリ構成（主要ファイル）

---

プロジェクト概要
- 名称: KabuSys
- 目的: 日本株のデータプラットフォームと研究・自動売買補助ツール群の提供
- コア技術: Python / DuckDB / J-Quants API / OpenAI（ニュース NLP） / RSS ニュース収集
- 主な利用ケース:
  - 日次 ETL（株価・財務・カレンダー）
  - ニュースを用いた銘柄別 AI スコアリング
  - 市場レジーム判定（ETF とマクロニュースの組合せ）
  - ファクター計算・特徴量探索（リサーチ用途）
  - 監査テーブル（シグナル→オーダー→約定のトレーサビリティ）

---

機能一覧
- data/
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch / save 系関数（株価・財務・カレンダー・上場情報）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - ニュース収集: RSS フィードの取得・前処理・raw_news への保存（SSRF 対策等を実装）
  - 品質チェック: 欠損 / スパイク / 重複 / 日付不整合チェック
  - 監査ログ: 監査スキーマ初期化・専用 DB 初期化（init_audit_schema, init_audit_db）
  - 汎用統計ユーティリティ: zscore_normalize 等
- research/
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量解析: calc_forward_returns, calc_ic, factor_summary, rank
- ai/
  - ニュース NLP: score_news（銘柄別センチメントを ai_scores に保存）
  - レジーム判定: score_regime（ETF の MA とマクロニュース LLM の混合で市場レジームを判定）
- config
  - 環境変数管理: 自動 .env ロード（.env / .env.local）と Settings API

---

セットアップ手順

前提
- Python 3.10+ を推奨（型アノテーションに `X | None` を使用）
- システムにネットワーク接続（J-Quants / OpenAI を利用する場合）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml

   実際のプロジェクトでは開発依存・その他パッケージが追加される可能性があります。requirements.txt がある場合はそれを利用してください。

3. ソース配置
   - 本 README に対応するリポジトリをクローンまたはソースを配置し、プロジェクトルートに移動します。

4. 環境変数設定
   - 必須: JQUANTS_REFRESH_TOKEN（J-Quants のリフレッシュトークン）
   - OpenAI を使う場合: OPENAI_API_KEY
   - その他は下記「環境変数（主要）」参照
   - 簡易に .env を作る例:
     ```
     # .env
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxx...
     KABU_API_PASSWORD=your_kabus_api_password
     KABUSYS_ENV=development
     ```
   - config モジュールはプロジェクトルートの .env を自動読み込みします（.git または pyproject.toml をルート判定に使用）。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. データベースパスの確認 / 作成
   - デフォルト DuckDB パス: data/kabusys.duckdb
   - 監視用 SQLite: data/monitoring.db
   - 監査用 DB は init_audit_db で初期化できます（親ディレクトリが存在しない場合は自動作成されます）。

---

環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン（ETL 用）
- KABU_API_PASSWORD (必須 for kabu api): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY (必須 for AI 機能): OpenAI API キー（score_news / score_regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意): LINE 通知に使う場合
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視 DB（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 監視系の設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: environment ('development'|'paper_trading'|'live')（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

注: Settings API を通して上記値にプログラムからアクセスできます:
```
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

使い方（代表的な呼び出し例）

基本: DuckDB 接続を作って各機能を呼ぶ想定です。

1) DuckDB 接続
```
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL 実行（株価・財務・カレンダーの差分取得）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュース NLP スコアリング（ai_scores テーブルへ書き込み）
```
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

4) 市場レジーム判定（market_regime テーブルへ書き込み）
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ DB 初期化（監査用 DuckDB を作る）
```
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # :memory: も可
```

6) 監査スキーマだけ既存接続に追加
```
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

7) ファクター計算・リサーチ
```
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

注意点:
- OpenAI を使う関数は api_key 引数を受け取ります。環境変数 OPENAI_API_KEY が設定されていれば省略可能です。
- API 呼び出し失敗時はフェイルセーフで処理を継続する設計の箇所が多くあります（ログに WARNING を出力してスコアを 0 にする等）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン制約があることを考慮して実装されています。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュース NLP スコアリング
    - regime_detector.py            -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch/save）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETL 便宜的公開（ETLResult）
    - calendar_management.py        -- 市場カレンダー管理
    - news_collector.py             -- RSS ニュース収集
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 統計ユーティリティ（zscore）
    - audit.py                      -- 監査ログスキーマ（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py        -- 将来リターン・IC・summary 等
  - research/... その他の研究ユーティリティ

主要なテーブル（コード内で参照・作成される想定）
- raw_prices / prices_daily
- raw_financials
- market_calendar
- raw_news / news_symbols / ai_scores
- market_regime
- signal_events, order_requests, executions (監査用)

---

運用のヒント・注意事項
- 本パッケージは実際の発注（ブローカー送信）モジュールを含んでいません。実取引に利用する場合は別途約定処理・リスク管理・二重送信防止の実装・法令遵守を必須としてください。
- OpenAI / J-Quants の API 呼び出しはレート制限やコストが発生します。テスト時はモックや少ないバッチでの検証を推奨します。
- 自動 .env ロードはプロジェクトルート検出ロジック（.git または pyproject.toml）に依存します。CI / テスト等で挙動を制御するには KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。
- DuckDB のバージョン互換性に依存する箇所（executemany の挙動等）があるため、使用する DuckDB のバージョンに注意してください。

---

貢献・拡張
- 新しいニュースソースの追加、OpenAI モデルの切替、ETL のスケジューリング（cron / Airflow 等）や監視（プロセス監視・アラート）などが典型的な拡張ポイントです。
- テストは外部 API 呼び出しをモックして行うことを推奨します（コード内に unittest.mock で差し替え可能なポイントが設けられています）。

---

連絡／ドキュメント
- コード内の docstring とモジュール冒頭コメントが主な設計メモです。各関数には入力・出力・例外と設計の意図が明記されていますので、まずはソースを参照してください。

以上が README.md の日本語版（概要・導入・使用例・構成）です。必要であれば、セットアップ用の requirements.txt、.env.example、サンプルスクリプト（etl_runner.py など）を追加で作成します。どれが必要か教えてください。