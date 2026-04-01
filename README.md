# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（リサーチ・ETL・NLP・監査ログを含む）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要な以下の機能群をまとめた Python パッケージです。

- データ ETL（J-Quants からの株価・財務・カレンダー取得）と品質チェック
- ニュース収集・NLP による銘柄別センチメント評価（OpenAI）
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 各種ユーティリティ（カレンダー管理、統計ユーティリティ等）

設計上のポイント:
- Look-ahead バイアスを避けるため、内部で日付取得（date.today()/datetime.today()）を乱用しない設計
- DuckDB を主要な永続化手段として利用
- 冪等性（ON CONFLICT / idempotent 保存）と堅牢なリトライロジックを重視
- 外部 API 呼び出し（J-Quants / OpenAI）にはレート制御・バックオフ・フォールバックを実装

---

## 主な機能一覧

- data (ETL / quality / jquants client / news collector / calendar management / audit)
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - データ品質チェック (missing_data / spikes / duplicates / date consistency)
  - J-Quants API クライアント（トークンリフレッシュ・レート制御・ページネーション）
  - RSS ニュース収集（SSRF 対策、トラッキング除去、前処理）
  - 監査ログ初期化（signal_events / order_requests / executions テーブル）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM スコアを合成して market_regime を保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- utils
  - data.stats.zscore_normalize: クロスセクションでの Z スコア正規化
- config
  - Settings クラス: 環境変数・.env 管理（自動読み込み機構あり）

---

## 必要要件

- Python 3.10+
  - （型ヒントで `X | None` を利用しているため Python 3.10 以降を推奨）
- 必要な Python パッケージ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース）

※ 実行環境に応じて追加のパッケージが必要になる場合があります。

---

## セットアップ手順

1. ソースをクローン／配置
   - 例: git clone / 配布アーカイブ展開

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（data.jquants_client で使用）
   - OPENAI_API_KEY: OpenAI を使う機能（ai.news_nlp / ai.regime_detector）を使う場合
   - KABU_API_PASSWORD: kabuステーション API を使う場合
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を行う場合
   - DUCKDB_PATH: （任意）DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: （任意）監視DBパス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV / LOG_LEVEL 等も設定可能（詳細は config.Settings のプロパティを参照）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

6. DuckDB スキーマ（監査ログなど）の初期化（任意）
   - Python で init_audit_db / init_audit_schema を呼ぶことで監査テーブルを作成できます。

---

## 使い方（代表的な例）

以下は主要な呼び出し例です。実行前に必ず上記の環境変数を設定してください。

- DuckDB 接続を作る（ファイル DB）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアを生成して ai_scores に保存する（OpenAI API 必須）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {n_written}")
  ```

- 市場レジームスコアを計算して market_regime に保存する
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn に対して監査ログを記録する処理を実装していく
  ```

- ファクター計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  factors = calc_momentum(conn, target_date=date(2026,3,20))
  # factors は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
  ```

注意点:
- AI 系の関数は OpenAI API を呼ぶため実行環境に API キーが必要です。api_key 引数で明示的に与えることも可能。
- ETL / DB 書き込みは冪等性を意識した実装になっていますが、本番運用前に小規模なテストを行ってください。

---

## 環境設定の詳細（config.Settings）

config.Settings は以下の環境変数を利用します（主要なもの）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須 if Slack)
- SLACK_CHANNEL_ID (必須 if Slack)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT （監視閾値）
- KABUSYS_ENV (development / paper_trading / live)（default: development）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)（default: INFO）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）で `.env` と `.env.local` を順に読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化できます（テスト等で利用）。

---

## 主要ディレクトリ構成

（パッケージは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLU / ai_scores 書込み
    - regime_detector.py      — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + 保存ロジック
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL 結果クラス再エクスポート
    - calendar_management.py  — 市場カレンダー管理 / 営業日判定
    - news_collector.py       — RSS 収集・前処理
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                — 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py  — 将来リターン / IC / summary / rank
  - research/... (その他ユーティリティ)

---

## 運用上の注意

- API 呼び出し（J-Quants / OpenAI）にはそれぞれレート制限があり、コード内で制御しています。過度な同時呼び出しは避けてください。
- ETL・品質チェックは失敗時でも他ステップを継続する設計ですが、エラーや品質上の警告はログに集約されます。運用側でのモニタリング・アラート設定を推奨します。
- ニュース収集は外部 RSS に依存します。ソースの可用性やフォーマット変化に注意してください。
- 監査ログは削除を前提にしていません。ディスク容量やアーカイブ方針を検討してください。

---

## 参考（主な公開 API）

- config.settings: 全アプリ設定の取得
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes / get_id_token
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)

---

必要に応じて README にチュートリアルや CLI の使い方、開発向けセットアップ（pre-commit / linters / tests）の追加を行えます。特定の項目（例: ETL スケジュール設定、監視アラート設定、サンプル .env.example）を追加したい場合はご指示ください。