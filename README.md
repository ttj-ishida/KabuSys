# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ（KabuSys）のリポジトリ用 README。  
このドキュメントはプロジェクトの概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API からの株価・財務・カレンダーデータの差分ETL（DuckDB を利用）
- RSS ニュース収集・前処理・銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 ai_score）およびマクロセンチメントによる市場レジーム判定
- 研究（ファクター算出、将来リターン、IC算出、統計ユーティリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化ユーティリティ
- J-Quants API クライアント（レートリミット、リトライ、トークン自動更新、冪等保存）

パッケージは CWD に依存しない .env 自動ロードや、Look-ahead バイアス対策を考慮した実装方針が取られています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（fetch / save 各種）
  - カレンダー管理（営業日の判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集 (RSS → raw_news の保存、SSRF 対策、URL 正規化)
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュースセンチメント評価（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI 呼び出しのリトライ・JSON モード対応
- research/
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、ランク化ユーティリティ
- config.py
  - 環境変数管理（.env/.env.local 自動読み込み、必須チェック、各種パス・閾値設定）
  - KABUSYS_ENV / LOG_LEVEL の検証
- その他
  - news_collector：RSS 収集、前処理、SSRF 防御、記事ID生成（正規化 URL の SHA-256）
  - jquants_client：レートリミット・リトライ・トークン管理・DuckDB への冪等保存

---

## セットアップ手順

前提:
- Python 3.10+（型シグネチャに union types 等があるため）
- ネットワークアクセス（J-Quants, OpenAI, RSS ソース 等）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージのインストール
   - 代表的な依存:
     - duckdb
     - openai
     - defusedxml
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - ない場合は手動で:
     - pip install duckdb openai defusedxml

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置して設定できます。パッケージは起動時に自動で .env を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（必須/推奨）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー
     - KABU_API_PASSWORD (必須) — kabu ステーション連携用パスワード
     - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
     - KABU_API_BASE_URL (オプション) — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH (オプション) — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH (オプション) — デフォルト: data/monitoring.db
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視用設定
     - KABUSYS_ENV — development / paper_trading / live のいずれか（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

6. DB 初期化（監査ログスキーマを使う場合）
   - 例: Python REPL やスクリプト内で
     - import duckdb
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")  # または ":memory:"

---

## 使い方（代表例）

以下はパッケージの主要機能を呼び出す際のミニマムな例です。

- DuckDB 接続を生成して ETL を実行する
  - 例:
    - import duckdb
    - from kabusys.config import settings
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect(str(settings.duckdb_path))
    - result = run_daily_etl(conn)  # target_date を指定することも可能
    - print(result.to_dict())

- News センチメントスコアを生成（OpenAI 必須）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect(str(settings.duckdb_path))
  - written = score_news(conn, date(2026, 3, 20))  # 対象日を指定
  - print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（ETF 1321 を用いる）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, date(2026, 3, 20))  # OpenAI API Key は環境変数または引数で指定可能

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")

- ファクター計算や研究用ヘルパー
  - from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  - mom = calc_momentum(conn, target_date)
  - vol = calc_volatility(conn, target_date)
  - val = calc_value(conn, target_date)
  - normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

注意点:
- AI 機能は OpenAI の JSON mode を利用する設計です。API レスポンスのパースは堅牢化されていますが、API キーが正しく設定されていることを確認してください。
- ETL / API 呼び出し部分はリトライやレートリミット制御が入っていますが、ネットワーク環境・API 権限が必要です。

---

## .env 自動読み込み挙動

- パッケージ初期化時にプロジェクトルート（__file__ の親階層から .git または pyproject.toml を探索）を特定できれば、以下の順で環境変数を読み込みます:
  1. OS 環境変数（既に設定されている値は保護されます）
  2. .env（プロジェクトルート）
  3. .env.local（.env.local は .env を上書き）
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須の環境変数は Settings クラスのプロパティアクセス時に _require により ValueError が投げられます。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュールを抜粋して示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュースセンチメント（銘柄別）処理、OpenAI API 呼び出し・バッチ処理
    - regime_detector.py  # マクロ + ETF MA200 乖離を用いた市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py         # ETL パイプライン（run_daily_etl 他）
    - jquants_client.py   # J-Quants API クライアント（fetch/save）
    - calendar_management.py  # マーケットカレンダー管理、営業日判定
    - news_collector.py   # RSS 収集・前処理・SSRF 対策
    - quality.py          # データ品質チェック
    - stats.py            # zscore_normalize 等統計ユーティリティ
    - audit.py            # 監査ログスキーマ初期化
    - etl.py              # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py    # momentum/value/volatility の計算
    - feature_exploration.py# forward returns, IC, factor summary, rank

（上記は主要ファイルの一覧で、実際にはさらに細かい実装が含まれます）

---

## 運用上の注意 / ベストプラクティス

- Look-ahead バイアス対策:
  - 内部関数は datetime.today() や date.today() を直接参照せず、呼び出し側が target_date を指定することでテスト・バックテストに適した設計になっています。バッチ実行時も target_date を明示することを推奨します。
- トークン管理:
  - J-Quants の ID トークンはモジュール内でキャッシュされ、401 が返った場合はリフレッシュして1回リトライします。
- DuckDB との互換性:
  - 実装は DuckDB の仕様（executemany の空配列制約など）を考慮しています。DuckDB のバージョンにより挙動が異なる点に留意してください。
- セキュリティ:
  - news_collector は SSRF 対策・XML 攻撃対策（defusedxml）を組み込んでいます。外部 URL サニタイズやトラッキングパラメータ除去を行います。

---

## 付録：主要な設定キー一覧（まとめ）

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (AI 機能利用時に必須)
- KABU_API_PASSWORD (kabu API 連携)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (監視/通知)
- DUCKDB_PATH（例: data/kabusys.duckdb）
- SQLITE_PATH（例: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

---

この README はコードベースのトップレベル説明と主要な操作例を意図しています。実運用向けには各機能（ETL スケジュール、OpenAI の使用量管理、ログ/監視の設定、バックテスト環境）に合わせた追加の運用ドキュメントを整備してください。質問やさらに詳しいサンプルが必要であれば教えてください。