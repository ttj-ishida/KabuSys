# KabuSys

日本株向けの自動売買 / 研究プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、データ品質チェック、特徴量（ファクター）計算、ニュースNLP（OpenAI を用いたセンチメント評価）、市場レジーム判定、監査ログ（発注〜約定トレーサビリティ）等の機能を提供します。

現バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API/例）
- 環境変数（.env）
- ディレクトリ構成

---

プロジェクト概要
- 日本株のデータパイプラインと研究機能を統合したライブラリ群。
- DuckDB をバックエンドに用いて、ETL（J-Quants API からの差分取得→保存）、品質チェック、ニュース収集・NLP による銘柄ごとの AI スコアリング、ETF ベースの市場レジーム判定、監査ログ（シグナル→発注→約定のトレーサビリティ）を実装。
- バックテストや本番運用の下地（データ管理・監査）を提供し、実際の発注層とは分離された設計。

機能一覧
- 環境・設定管理
  - .env の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック
- データ ETL（kabusys.data.pipeline）
  - J-Quants からの株価日足 / 財務 / カレンダー差分取得（ページネーション、レート制御、リトライ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL 結果の集約（ETLResult）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合（未来日、非営業日データ）を検出
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、範囲内の営業日取得
  - JPX カレンダー差分更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 対策、受信サイズ上限、URL 正規化）
  - raw_news / news_symbols への冪等保存設計
- ニュースNLP（kabusys.ai.news_nlp）
  - gpt-4o-mini を用いた銘柄ごとのセンチメントスコア算出（JSON mode）と ai_scores への保存
  - バッチ処理、トリミング、リトライ、レスポンスバリデーションを実装
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み70%）＋マクロニュース LLM センチメント（重み30%）で日次レジーム判定
  - 判定結果を market_regime テーブルへ冪等書き込み
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルを作成する初期化ユーティリティ
  - init_audit_schema / init_audit_db により監査 DB を準備
- 研究ユーティリティ（kabusys.research）
  - モメンタム / バリュー / ボラティリティ ファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化、統計サマリー

---

セットアップ手順（開発環境）
前提: Python 3.10+ を想定（typing の union 表記等を使用）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がない場合は主要依存を入れてください:
     - duckdb
     - openai
     - defusedxml
   例:
     pip install duckdb openai defusedxml

   （プロジェクトに setup.cfg / pyproject.toml があれば pip install -e .）

4. 環境変数を準備
   - プロジェクトルートに .env を置くと自動で読み込まれます（デフォルト）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB（データベース）用ディレクトリ作成
   - デフォルトの duckdb パス: data/kabusys.duckdb（config.py の settings.duckdb_path を参照）
   - 必要に応じてディレクトリ作成: mkdir -p data

注意:
- OpenAI（news_nlp / regime_detector）を使用するには環境変数 OPENAI_API_KEY を設定してください（関数引数として API キーを直接渡すことも可能）。
- J-Quants 用には JQUANTS_REFRESH_TOKEN を設定してください（jquants_client が id_token を取得します）。

---

環境変数（主なキー）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（既定: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（既定: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live"), 既定: development
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

例 .env（最小）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

使い方（主要 API と実行例）

- DuckDB 接続の作成例
  from pathlib import Path
  import duckdb
  db_path = str(Path("data/kabusys.duckdb"))
  conn = duckdb.connect(db_path)

- 日次 ETL の実行
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- 個別 ETL ジョブ（株価）
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  print(f"fetched={fetched}, saved={saved}")

- ニュースの AI スコアリング（銘柄ごと）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"ai_scores written: {n_written}")

- 市場レジーム判定
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))  # OpenAI API キーは env または api_key 引数で指定可能

- 監査 DB 初期化（監査用 DuckDB を新規作成）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events/order_requests/executions テーブルが作成されます

- J-Quants トークン取得（必要なら）
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # JQUANTS_REFRESH_TOKEN が環境変数にある前提

ログ出力
- LOG_LEVEL, KABUSYS_ENV に応じたログレベルで動作します。必要に応じて logging.basicConfig を設定してください。

テストとモック
- OpenAI やネットワーク呼び出しは関数単位で差し替え可能（モジュール内の _call_openai_api／_urlopen 等を patch してモック化）。
- ETL やニュース収集はネットワークに依存するため、ユニットテストでは外部呼出しをモックすることを推奨します。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、Settings クラス（環境変数アクセス）
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースの LLM センチメント（ai_scores）
    - regime_detector.py     # 市場レジーム判定（1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py # マーケットカレンダー管理（営業日判定等）
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - jquants_client.py      # J-Quants API クライアント（fetch/save）
    - news_collector.py      # RSS ニュース収集
    - quality.py             # データ品質チェック
    - stats.py               # 汎用統計ユーティリティ（zscore_normalize）
    - etl.py                 # ETL の公開インターフェース（ETLResult 再エクスポート）
    - audit.py               # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     # Momentum / Value / Volatility 等の計算
    - feature_exploration.py # 将来リターン, IC, 統計サマリー 等
  - (その他) strategy / execution / monitoring パッケージが __all__ に宣言されていますが、現行コードベースに含まれるモジュールの実装に従います。

各ファイルは docstring に設計意図と副作用（ルックアヘッド回避、冪等性、トランザクション処理、フェイルセーフの方針等）が明記されています。コードを読みながら、ETL の流れ・品質チェックの挙動・LLM 呼び出しのリトライ方針を把握してください。

---

運用上の注意
- Look-ahead バイアス防止のため、各モジュールは target_date 引数を明示的に受け取り、date.today() や datetime.today() に依存しない実装ポリシーが取られています。バックテスト等では必ず target_date を固定して呼び出してください。
- OpenAI 呼び出し（news_nlp / regime_detector）は API コストとレートに依存します。運用時はバッチ頻度やバッチサイズ（定数 _BATCH_SIZE 等）を要調整。
- J-Quants API はレート制限が厳しいため、jquants_client では固定間隔のレートリミッタとリトライを実装しています。認証トークンの自動リフレッシュもサポートします。
- 監査ログは削除せず永続化する設計です（監査要件に合わせた運用をしてください）。

---

貢献・開発
- バグ修正や改良提案はプルリクエストで歓迎します。ドキュメントはコードベースの docstring を第一に合わせて更新してください。
- 大きな機能追加や設計変更は Issue で事前に議論してください。

---

補足
- README に記載されていない細かな挙動は各モジュールの docstring を参照してください（各関数に詳細な設計方針・エラーハンドリング・返り値の仕様が書かれています）。

必要なら、README にサンプル .env.example、requirements.txt、または CLI ラッパーの使い方サンプルを追加で作成します。どの追加情報が欲しいか教えてください。