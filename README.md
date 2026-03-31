# KabuSys

日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注／約定トレース）など、トレードシステムに必要な基盤機能を提供します。

---

## 主な機能 (概要)

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル・ページネーション・リトライ・レート制御対応

- ニュース収集・NLP
  - RSS 取得、前処理、記事の冪等保存（raw_news）
  - OpenAI（gpt-4o-mini など）を使った銘柄別センチメント評価（ai_scores）

- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成し、日次で 'bull'/'neutral'/'bear' 判定を実行

- 研究 / ファクター計算
  - Momentum / Value / Volatility / Liquidity 等の定量ファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- データ品質チェック
  - 欠損、スパイク（急騰・急落）、主キー重複、日付不整合（未来日付・非営業日のデータ）を検出

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマの初期化ユーティリティ
  - 発注フローの UUID 連鎖による追跡を想定

- 設定管理
  - .env / 環境変数の自動ロード。必須変数チェック（Settings クラス）

---

## 依存関係（推奨）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリで多くを実装しているため、追加依存は比較的少ないです）

例（仮の requirements）:
pip install duckdb openai defusedxml

プロジェクトに requirements.txt を用意している場合はそれを使用してください。

---

## セットアップ手順

1. リポジトリをクローン（またはソースを取得）
   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数を設定
   環境変数は .env または .env.local、または OS の環境変数で設定できます。
   パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）にある
   .env ファイルが自動で読み込まれます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   重要な環境変数（本プロジェクト内で参照される代表例）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI 呼び出しに使用する API キー（AI モジュール利用時に必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: sqlite (監視用)（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
   - KABUSYS_ENV: environment ('development' | 'paper_trading' | 'live')（デフォルト: development）
   - LOG_LEVEL: ログレベル ('DEBUG','INFO','WARNING','ERROR','CRITICAL')（デフォルト: INFO）

   例 .env（簡略）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

5. データディレクトリ等を作成
   mkdir -p data

6. 監査用 DB の初期化（任意）
   Python REPL またはスクリプトで:
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   conn.close()

---

## 使い方（主要なユースケース）

以下はライブラリを直接インポートして使う例です。CLI ラッパーは実装されていないため、スクリプトや Cron / ワーカーで呼び出す想定です。

- 日次 ETL の実行（株価 / 財務 / カレンダーの差分取得）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースの AI スコア付与（銘柄別センチメント）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で指定
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（ma200 + マクロニュース）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査スキーマの初期化（既存の DuckDB 接続に対して）
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)

- 研究用ファクター計算（例: モメンタム）
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は [{"date":..., "code":"XXXX", "mom_1m":..., ...}, ...]

注意:
- AI 関連機能（score_news, score_regime）は OpenAI API キー（OPENAI_API_KEY）が必要です。
- ETL は J-Quants の認証トークン（JQUANTS_REFRESH_TOKEN）を必要とします。

---

## 推奨運用上の注意

- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を探索）から読み込まれます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI 呼び出し部分はリトライ／フォールバック等を備えていますが、API 料金に注意してバッチ頻度を制御してください。
- DuckDB への大量挿入は executemany を使用しています。ETL のストレージ容量やバックアップ戦略を用意してください。
- 監査ログは削除しない前提で設計されています。データサイズの管理（アーカイブ等）を検討してください。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                : 環境変数 / 設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py            : ニュース NLP（銘柄別スコア生成）
    - regime_detector.py     : 市場レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（取得 / 保存）
    - pipeline.py            : ETL パイプライン（run_daily_etl 等）
    - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      : RSS ニュース収集・保存
    - quality.py             : データ品質チェック
    - stats.py               : 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py               : 監査ログ（テーブル作成 / 初期化）
    - etl.py                 : ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     : ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py : 将来リターン / IC / 統計サマリー 等
  - (その他: strategy, execution, monitoring 等のモジュールが想定される)

---

## 開発 / テスト

- 自動 .env ロードや OpenAI の呼び出しなどはテスト用に差し替え可能（モック可能）。モジュール内の小さな関数（例: _call_openai_api や _urlopen）を unittest.mock でパッチしてテストする設計になっています。
- データベースは :memory: や一時ファイルで容易にテスト可能（init_audit_db は ":memory:" を受け取れます）。

---

## ライセンス / 貢献

この README の先頭のリポジトリに付随する LICENSE を参照してください。貢献やバグ報告は Issue / Pull Request を通じてお願いします。

---

お問い合わせや追加のドキュメント（API リファレンス、ETL スケジュール例、データスキーマ定義等）が必要であれば教えてください。README に追記します。