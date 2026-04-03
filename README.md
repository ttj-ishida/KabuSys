# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（LLM を用いたセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注追跡）など、バックテスト／運用に必要な基盤機能を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時は安全側にフォールバック）」です。

---

## 機能一覧

- データ取得（J-Quants API 経由）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダー
  - レートリミット制御・リトライ・トークン自動リフレッシュ
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - run_daily_etl による市場カレンダー・株価・財務の差分取得・保存
  - 品質チェック（欠損・スパイク・重複・日付整合性）
  - ETLResult による結果集約
- ニュース収集（RSS）
  - RSS フィードフェッチ、前処理、raw_news への保存、銘柄紐付け
  - SSRF 対策、XML セーフパーサ、受信サイズ上限などセキュリティ対策
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを集約して LLM に投げ、銘柄別 ai_score を ai_scores テーブルへ書き込み
  - JSON mode + バッチ処理、リトライ、レスポンスバリデーション
- 市場レジーム判定（AI + テクニカル）
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して daily レジーム判定（bull/neutral/bear）
  - LLM 呼び出しは安全にリトライ／フォールバック
- 研究用ユーティリティ（research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ
  - zscore 正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルで戦略→シグナル→発注→約定のトレースを保持
  - init_audit_db で DuckDB にスキーマ初期化可能

---

## セットアップ手順

前提:
- Python 3.10+（ソースでは typing の Union | といった構文を使用）
- DuckDB と OpenAI クライアントを利用します

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - 開発中のパッケージとしてインストール:
     - pip install -e .
   - 必要な外部依存（例）:
     - pip install duckdb openai defusedxml
   - 実運用で追加する可能性のあるもの:
     - pytest（テスト）、coverage、その他監視用ライブラリなど

3. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置くと自動ロードされます（プロジェクトルートは .git または pyproject.toml を基準に探索）。
   - 自動ロードを一時的に抑止する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須設定（代表的な環境変数）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須：データ ETL に必要）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定に必要）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注機能を使う場合）
その他（任意）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB 用）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例 .env（実際は .env.example を参考にしてください）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要な利用例）

以下はライブラリをインポートして使う簡単な例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

1) DuckDB に接続する
- import duckdb
- conn = duckdb.connect(str(Path(os.environ.get("DUCKDB_PATH", "data/kabusys.duckdb"))))

2) 日次 ETL を回す
- from kabusys.data.pipeline import run_daily_etl
- result = run_daily_etl(conn, target_date)  # target_date は datetime.date
- print(result.to_dict())

3) ニュースの NLP スコア取得（AI 使用）
- from kabusys.ai.news_nlp import score_news
- n = score_news(conn, target_date, api_key="sk-...")  # api_key を省略すると環境変数 OPENAI_API_KEY を使用

4) 市場レジーム判定
- from kabusys.ai.regime_detector import score_regime
- score_regime(conn, target_date, api_key=None)  # OPENAI_API_KEY を使う場合は None

5) 監査ログ DB 初期化
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")

6) 研究用ファクター計算
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- momentum = calc_momentum(conn, target_date)
- volatility = calc_volatility(conn, target_date)
- value = calc_value(conn, target_date)

7) 設定アクセス
- from kabusys.config import settings
- settings.jquants_refresh_token
- settings.duckdb_path
- settings.env, settings.is_live など

注意点:
- ほとんどの関数は Look-ahead バイアスを避けるために内部で datetime.today() を参照しない設計になっています。必ず target_date を明示して呼ぶことを推奨します。
- OpenAI など外部 API 呼び出しはエラー時にフォールバックするよう作られているものの、APIキーとレート制限は運用側で管理してください。

---

## ディレクトリ構成（主なファイルと役割）

src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - 環境変数の自動ロード・設定オブジェクト（settings）
- ai/
  - __init__.py
  - news_nlp.py: ニュースを LLM でスコアリングして ai_scores に保存するロジック
  - regime_detector.py: ETF 1321 の MA とマクロニュースから市場レジームを判定
- data/
  - __init__.py
  - calendar_management.py: マーケットカレンダー周り（営業日判定、update job）
  - etl.py: ETL の公開インターフェース（ETLResult）
  - pipeline.py: ETL の実装（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - stats.py: z-score 正規化など統計ユーティリティ
  - quality.py: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit.py: 監査ログ（signal/order_request/execution）スキーマ初期化 / DB 初期化
  - jquants_client.py: J-Quants API クライアント（取得・保存関数・トークン管理・リトライ・レート制御）
  - news_collector.py: RSS 収集、前処理、raw_news への保存
- research/
  - __init__.py
  - factor_research.py: モメンタム/ボラティリティ/バリューの計算
  - feature_exploration.py: 将来リターン計算、IC/ランキング/統計サマリ
- monitoring, strategy, execution, etc.
  - パッケージ全体に付随するモジュールは将来的に含まれる想定（__all__ に定義あり）

ドキュメント生成やテストはプロジェクトルートに pyproject.toml / setup.cfg / requirements.txt が存在する想定です（このリポジトリ断片では省略）。

---

## 運用上の注意

- API キー管理：J-Quants と OpenAI のキーは厳重に管理してください。
- レート制限：J-Quants（120 req/min）や OpenAI のレートに注意。jquants_client は内部でスロットリングを行いますが、高頻度バッチは設計を検討してください。
- データ整合性：ETL はバックフィルや品質チェックを行いますが、初期データロードやスキーマ変更時は注意深く検証してください。
- テスト：AI 呼び出しやネットワーク I/O 部分はモック可能な設計です（モジュール内の呼び出し関数を patch してテストできます）。

---

README に記載の内容はコードベースの主要設計と利用方法の要約です。実装の詳細・API の戻り値仕様やスキーマについては各モジュールの docstring を参照してください。必要であれば README を拡張してサンプルスクリプト、Docker / systemd 起動例、CI 設定、具体的な .env.example を追加できます。