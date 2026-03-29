# KabuSys

日本株向けの自動売買 / データ基盤ユーティリティ群です。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含むモジュール群を提供します。

## 主要特徴
- データ取得（J-Quants API）と差分ETL（DuckDB保存、冪等保存）
- ニュース収集（RSS）と前処理、銘柄紐付け
- ニュースのLLMベースセンチメントスコアリング（gpt-4o-mini、JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（信号→発注→約定のトレース可能なスキーマ）と初期化ユーティリティ
- 環境変数からの設定読み込み（.env / .env.local の自動読み込みを含む）

---

## 機能一覧（モジュールマップ）
- kabusys.config
  - 環境変数/設定管理（自動 .env ロード、必須チェック）
- kabusys.data
  - jquants_client: J-Quants API 呼出し・保存（rate-limit・リトライ・トークン自動更新）
  - pipeline / etl: 日次 ETL（価格・財務・カレンダー）を差分で実行
  - news_collector: RSS 収集・前処理（SSRF対策、サイズ制限）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ定義・初期化（DuckDB）
  - stats: z-score 正規化等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースの LLM センチメント付与・ai_scores への保存
  - regime_detector.score_regime: ETF MA200 とマクロニュースを合成した市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: 将来リターン計算、IC、統計サマリー等

---

## 動作要件
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
（プロジェクトの setup/pyproject に依存関係が記載されている想定です。pip install -r requirements.txt 等で導入してください）

---

## セットアップ手順（例）
1. リポジトリをクローン、インストール（開発時）
   - git clone ...
   - cd <repo>
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -U pip
   - pip install -e .        # パッケージとしてインストール（setup/pyproject がある前提）
   - または必要なパッケージを個別にインストール:
     - pip install duckdb openai defusedxml

2. 環境変数設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD（kabuステーション用パスワード）
     - SLACK_BOT_TOKEN（Slack 通知用 Bot トークン）
     - SLACK_CHANNEL_ID（通知先チャンネルID）
     - OPENAI_API_KEY（OpenAI 呼出しに必要）
   - 任意:
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG / INFO / …、デフォルト INFO）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
   - 自動 .env ロードはデフォルトで有効。無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

3. データベースの準備（監査DBの初期化例）
   - Python REPL やスクリプトから:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - DuckDB のパス親ディレクトリは自動作成されます。

---

## 使い方・主要API例

- 日次ETL を実行して価格・財務・カレンダーを取得・保存する
  - 例（Python）:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースのスコアリング（OpenAI が必要）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {n_written} symbols")

- 市場レジーム判定
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))  # OpenAI API key は環境変数か引数で指定

- 研究用ファクター計算
  - 例:
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    momentum = calc_momentum(conn, target_date=date(2026,3,20))
    # momentum は dict のリスト

- カレンダー/営業日ユーティリティ
  - is_trading_day(conn, date_obj)
  - next_trading_day(conn, date_obj)
  - get_trading_days(conn, start_date, end_date)

- データ品質チェック
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=date(2026,3,20))

---

## 環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
  - KABU_API_PASSWORD: kabu API のパスワード
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
  - OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp / regime_detector）
- オプション
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視DBパス（default: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env 自動ロードを無効化

注意: kabusys.config はプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みします。パッケージ配布後も期待通りに動作するよう、__file__ から探索します。

---

## 推奨ワークフロー（簡易）
1. .env を用意して必須トークンを設定
2. DuckDB を用意（デフォルトパスを使用するか、settings.duckdb_path を上書き）
3. 初回: 監査スキーマ初期化（init_audit_db）
4. run_daily_etl をスケジューラー（夜間バッチ）で定期実行
5. ニュース収集・スコアリング → シグナル生成 → 発注（発注部分は別モジュールで実装想定）

---

## ディレクトリ構成（主要ファイル）
プロジェクトルートに src/kabusys 以下が存在します。主な構成は以下の通り：

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
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py (ETLResult re-export in etl.py)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (パッケージに含まれる想定の監視関連モジュール)
    - strategy/ (戦略レイヤー: このコードベースではインターフェース想定)
    - execution/ (約定/ブローカ接続: 実装想定)

（上記はコードベースからの抜粋です。実際のリポジトリでは追加ファイルやドキュメントがある場合があります）

---

## 開発上の注意点 / 設計方針（抜粋）
- ルックアヘッドバイアス回避: 日付処理は target_date ベースで行い、datetime.today()/date.today() を内部ロジックで直接参照しない設計の関数が多くあります。
- DuckDB を中心としたローカルデータ基盤（冪等性を重視した INSERT/UPDATE）
- 外部API呼出し（OpenAI / J-Quants）はリトライ・バックオフ・フェイルセーフ（失敗時は0寄せ等）を組み込んでいます
- セキュリティ: RSS取得は SSRF 対策、XML処理に defusedxml を使用など安全側を考慮

---

## サポート / 貢献
- バグ報告や機能追加は issue を立ててください。PR はテスト付きで歓迎します。
- 外部APIキーやシークレットはソースに埋め込まず、必ず環境変数またはシークレット管理で扱ってください。

---

README はこのコードベースの概要と基本的な使い方をまとめたものです。実運用に当たっては pyproject.toml / setup.py、CI、実行用スクリプト（ETL の cron/airflow など）、および発注/ブローカー接続部分の実装を別途行ってください。