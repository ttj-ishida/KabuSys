# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）など、トレーディングシステムに必要な基盤機能を提供します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検査・ヘルパー
- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー等の取得（ページネーション対応）
  - レートリミット管理、トークン自動リフレッシュ、リトライ（バックオフ）
  - DuckDB への冪等保存（ON CONFLICT 相当の処理）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新 / バックフィルの自動計算
  - ETL 結果を表す `ETLResult`（品質問題やエラーを集約）
- データ品質チェック
  - 欠損・スパイク（急騰/急落）・重複・日付不整合（未来日付 / 非営業日データ）
  - 問題は `QualityIssue` リストで返却
- マーケットカレンダー管理
  - 営業日判定（DB 優先、未登録は曜日ベースのフォールバック）
  - next/prev/get_trading_days/is_sq_day 等のユーティリティ
  - JPX カレンダーの差分更新ジョブ
- ニュース収集
  - RSS フィード収集（SSRF 対策・gzip 制限・トラッキングパラメータ除去）
  - 記事前処理・冪等保存・銘柄紐付け
- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM に投げ、センチメント（ai_scores）を取得
  - JSON Mode を使った結果検証、チャンク・バッチ処理、リトライ（429/ネットワーク/5xx）
- 市場レジーム判定
  - ETF 1321 の MA200 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して
    market_regime テーブルへ冪等書き込み（bull/neutral/bear 判定）
- リサーチ（factor / feature exploration）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events, order_requests, executions などの監査スキーマを提供
  - init_audit_db により DuckDB を初期化（UTC タイムスタンプ固定）

---

## 前提 / 推奨環境

- Python 3.10+
  - （Union 型 `X | Y` を使用しているため 3.10 以上が必要）
- 推奨パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

※ 実行時に必要なパッケージは利用する機能によって異なります（例：ニュース収集は defusedxml、LLM 呼び出しは openai）。

---

## 必要な環境変数

主に以下を設定してください（.env/.env.local または OS 環境変数）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API（kabuステーション）用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI（ニュース NLP / レジーム判定）用 API キー（score_news / score_regime 実行時に必要）
- DUCKDB_PATH: DuckDB のファイルパス（省略可、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（省略可、デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、default=development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、default=INFO）

自動 .env ロードについて:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）を検出して `.env` → `.env.local` の順で自動ロードします。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン / 作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .
5. 環境変数を用意
   - .env/.env.local を作成して必要なキーを設定する（.env.example を参照）
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
6. DuckDB のスキーマ初期化（必要に応じて）
   - スキーマ初期化関数は別モジュールにある想定（例: data.schema.init_schema()）
   - 監査DB を初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な API / サンプル）

以下は各主要機能の簡単な利用例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY）を設定してください。

- DuckDB へ接続して日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（指定日分のニュースをスコアリング）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n_written}")
  ```

  - score_news は OPENAI_API_KEY を環境変数から取得。api_key 引数で明示的に渡すことも可能。

- 市場レジーム判定:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（例: モメンタム）:
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は dict のリスト: [{"date":..., "code":..., "mom_1m":..., ...}, ...]
  ```

---

## 注意点 / 設計上のポイント

- Look-ahead バイアス防止
  - 多くのモジュールは datetime.today() や date.today() に直接依存せず、呼び出し元が target_date を渡す設計になっています。
- 冪等性
  - J-Quants から取得したデータの保存は冪等（INSERT ... ON CONFLICT DO UPDATE）を行います。
- フェイルセーフ
  - LLM 呼び出しや外部 API 失敗時は、致命的に止めずフォールバック値（例: macro_sentiment=0.0）で継続する設計です。
- テスト容易性
  - 外部呼び出し（OpenAI 呼び出しや HTTP URLopen など）は内部関数をモックしやすいように分離されています。

---

## ディレクトリ構成

（主要ファイル / モジュールの概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM ベースセンチメントスコアリング
    - regime_detector.py — ETF MA200 とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — JPX カレンダー管理・判定ユーティリティ
    - news_collector.py  — RSS 収集・前処理・保存
    - quality.py         — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py           — 汎用統計ユーティリティ（zscore_normalize 等）
    - etl.py             — ETLResult 再エクスポート
    - audit.py           — 監査スキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー、rank 等
  - research/*, ai/* などは研究・分析・自動売買戦略で利用するユーティリティ群

---

## トラブルシューティング / よくある質問

- .env が読み込まれない
  - パッケージは .git または pyproject.toml のある親ディレクトリをプロジェクトルートとみなして .env を探します。CWD に依存しません。
  - 自動ロードを無効にしている場合（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）やプロジェクトルートが見つからない場合は手動で環境変数を設定してください。
- OpenAI で JSON パースエラーが出る
  - モジュールは LLM レスポンスのパース失敗時にフォールバック動作（スコア 0 やスキップ）します。必要なら API キーやモデル、プロンプトの調整を行ってください。
- DuckDB への書き込みでエラーが出る
  - 接続している DuckDB のスキーマが期待される形で存在するか確認してください。スキーマ初期化（監査用）は `init_audit_db` を利用できます。ETL 用のスキーマ初期化は別途提供されているはずのスキーマ初期化関数を呼んでください。

---

必要であれば、README に含める具体的な .env.example のテンプレートや、セットアップ用のスクリプト例（docker-compose / systemd unit / cron ジョブ）も追加で作成できます。どの情報を追記したいか教えてください。