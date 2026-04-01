# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買／リサーチユーティリティ群をまとめたライブラリです。J-Quants や RSS、OpenAI（LLM）を利用してデータ収集・品質チェック・ファクター計算・ニュースセンチメント判定・市場レジーム判定・監査ログ管理などを行うことを想定しています。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は以下です。

- J-Quants API を用いた株価・財務・上場情報・マーケットカレンダーの差分ETL
- RSS ベースのニュース収集とニュース本文の前処理
- OpenAI を用いたニュースセンチメント（銘柄別）とマクロセンチメント（市場レジーム）評価
- DuckDB を用いたデータ永続化、品質チェック、ファクター計算、リサーチ用ユーティリティ
- 監査ログ（signal → order_request → execution）を保存する監査スキーマの初期化と管理
- 簡易なシステム設定管理（.env 自動読み込み、環境判定、閾値設定等）

設計方針として、ルックアヘッドバイアスを避けるために内部で現在日時を安易に参照しない、外部 API 呼び出しに対してフェイルセーフ／リトライを実装する、DuckDB に対して冪等的な保存を行う、などが採用されています。

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダー、上場銘柄情報をページネーション対応で取得
  - 差分取得・バックフィル・保存（DuckDB への冪等保存）
  - ETL の統合エントリポイント（run_daily_etl）と結果 ETLResult

- データ品質チェック
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比閾値）
  - 主キー重複検出
  - 日付整合性チェック（未来日、非営業日のデータ検出）

- ニュース収集 / NLP
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去、gzip / サイズ上限）
  - ニュース前処理（URL 除去、空白正規化）
  - OpenAI を用いた銘柄別ニューススコアリング（score_news）
  - OpenAI を用いたマクロセンチメント + ETF MA200 による市場レジーム判定（score_regime）

- リサーチ / ファクター
  - モメンタム（1M/3M/6M、MA200乖離）
  - ボラティリティ/流動性（20日ATR、平均売買代金・出来高比）
  - バリュー（PER, ROE）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zscore 正規化

- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの DDL とインデックス定義
  - 監査DB初期化ユーティリティ（init_audit_db, init_audit_schema）

- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - settings オブジェクトから環境変数へアクセス（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
  - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD

---

## セットアップ手順

前提: Python 3.10+（typing 機能を多用しています）。実環境に合わせて仮想環境を作成してください。

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ...
   - cd <project>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要な依存パッケージをインストール
   - 依存関係ファイルはこのスニペット内に明記していませんが、主な依存は:
     - duckdb
     - openai (OpenAI の Python SDK)
     - defusedxml
     - その他標準ライブラリで賄われている部分もあります
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際の requirements.txt / pyproject.toml に基づいてインストールしてください（プロジェクト配布時に追加される想定）。

4. 環境変数設定
   - プロジェクトルートに .env を配置すると、起動時に自動で読み込まれます（.git または pyproject.toml がある親ディレクトリ基準で探します）。
   - 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数（最低限必要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news, score_regime を使う場合）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（注文モジュール利用時）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用 Slack（必要なら）
   - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH: デフォルト "data/monitoring.db"
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化（監査DB 例）
   - Python REPL またはスクリプトから:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - または既存の DuckDB 接続に対して init_audit_schema(conn) を呼ぶ。

---

## 使い方（主要な API/コマンド例）

以下はライブラリを直接 Python から利用する簡単な例です。関数は主に DuckDB 接続（duckdb.connect(...)）を受け取ります。

- DuckDB 接続の作成
  ```
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（デフォルトは今日）
  ```
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを計算して ai_scores テーブルへ保存
  ```
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数か第3引数で渡す
  print("written codes:", count)
  ```

- 市場レジーム判定
  ```
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存接続へ）
  ```
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- リサーチ系の利用例（ファクタ計算）
  ```
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

注意点:
- OpenAI API 呼び出しは gpt-4o-mini 等で JSON mode を利用します。API 利用量・レート制限に注意してください。
- J-Quants API 呼び出しには rate limiter とリトライが組み込まれています。認証には JQUANTS_REFRESH_TOKEN を使い get_id_token（モジュール内）で idToken を取得します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用のリフレッシュトークン
- OPENAI_API_KEY — OpenAI の API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD — kabu API 操作用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視用
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — =1 にすると .env の自動読み込みを無効化

---

## ディレクトリ構成（主要ファイルと責務）

- src/kabusys/
  - __init__.py — パッケージ定義、公開サブパッケージ一覧
  - config.py — .env 読み込み、settings オブジェクト（環境変数の取得・検証）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM により銘柄単位でスコア化（score_news）
    - regime_detector.py — ETF 1321 の ma200 と LLM マクロセンチメントを合成して市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得、保存ロジック）
    - pipeline.py — ETL の統合パイプライン（run_daily_etl 等）および ETLResult
    - etl.py — ETLResult の再エクスポート
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - calendar_management.py — マーケットカレンダー管理と営業日ロジック
    - news_collector.py — RSS 取得と前処理（SSRF 対策、ID 生成、保存）
    - audit.py — 監査ログ（DDL / 初期化 / インデックス）
  - research/
    - __init__.py
    - factor_research.py — モメンタム／ボラティリティ／バリュー等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランクユーティリティ
  - ai, data, research 以下にテスト対象の主要ロジック・ビジネスロジックが実装されています。

---

## 実運用／注意事項

- API キー・トークンは外部に漏れないように .env / シークレット管理にて厳重に管理してください。
- OpenAI API の呼び出し回数はコストがかかるため、バッチ数やチャンクサイズを運用に合わせて調整してください。
- J-Quants API のレート制限（120 req/min）を遵守するため、モジュール内でスロットリングが実装されていますが、ETL 等の運用スケジュールは設計に注意してください。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるためパラメータの空チェックが実装されています。DuckDB バージョン依存の振る舞いに注意してください。

---

もし README に追加したい内容（実行可能な CLI、systemd ユニット例、CI 設定、requirements.txt の内容、より詳細な使い方サンプルなど）があれば教えてください。README をその要望に合わせて拡張します。