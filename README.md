# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants / RSS / OpenAI などの外部データを取り込み、ETL / データ品質チェック / ニュースセンチメント解析 / 市場レジーム判定 / 監査ログ（トレーサビリティ）等の機能を提供します。

主な設計方針は「ルックアヘッドバイアスを避ける」「冪等性」「フェイルセーフ（API失敗時は継続）」「DuckDB を中心とした軽量データ基盤」です。

---

## 主な機能

- データ取得・ETL
  - J-Quants から株価（日足）・財務データ・上場情報・マーケットカレンダーを差分取得して DuckDB に保存（冪等）
  - ETL 全体の実行エントリポイント（run_daily_etl）
- データ品質チェック
  - 欠損データ、スパイク（急騰/急落）、主キー重複、日付不整合のチェック（QualityIssue を返す）
- ニュース収集 / 前処理
  - RSS から記事を収集して正規化・保存（SSRF 対策、トラッキングパラメータ除去、Gzip 上限など）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM（gpt-4o-mini）で評価して ai_scores に保存（score_news）
  - マクロ経済記事の LLM センチメントと ETF MA 乖離を合成して市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算、IC（Spearman）、Z-score 正規化、統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等の監査テーブル定義・初期化（init_audit_schema / init_audit_db）
- その他ユーティリティ
  - マーケットカレンダー管理（営業日判定・次/前営業日取得・バッチ更新）
  - J-Quants API クライアント（認証、リトライ、レートリミット、ページネーション対応）

---

## 必須要件（概略）

- Python 3.10+
- 主要依存ライブラリ（本コードからの想定）
  - duckdb
  - openai
  - defusedxml

（実際のパッケージ依存はプロジェクトの packaging / requirements を確認してください）

---

## セットアップ手順

1. リポジトリをクローンし、開発環境を作成
   ```bash
   git clone <repo_url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. インストール
   - ソースを編集しながら使う場合:
     ```bash
     python -m pip install -e .
     ```
   - 必要なライブラリが個別にある場合は以下を追加インストール:
     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数の設定
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（既定で有効）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。
   - 必要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu API パスワード（必須）
     - KABU_API_BASE_URL — kabu API のベース URL（任意、デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime に渡せる）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   - サンプル `.env`（例）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL からの呼び出し例です。全ての関数は duckdb の接続オブジェクト（duckdb.connect(...) の戻り）を受け取ります。

- DuckDB に接続する
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")  # ファイルパスは settings.duckdb_path と整合させる
  ```

- 日次 ETL の実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコア化して ai_scores に書き込む（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームを判定して market_regime に書き込む（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化する（監査スキーマ作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # または既存接続にスキーマのみ追加:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn)
  ```

- 研究用ファクター計算の例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, date(2026, 3, 20))
  # zscore 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

エラーや API 呼び出し失敗時の挙動:
- ニュースや OpenAI 呼び出しで部分失敗があっても、設計上はフェイルセーフで処理を続行します（スコアを 0 にフォールバックする等）。
- J-Quants クライアントは 401 の場合トークンを自動更新し再試行します。レートリミットと指数バックオフを実装しています。

---

## 環境変数と設定（settings）

設定は `kabusys.config.Settings` から参照できます。主に以下のプロパティを提供します：

- jquants_refresh_token  (JQUANTS_REFRESH_TOKEN)
- kabu_api_password      (KABU_API_PASSWORD)
- kabu_api_base_url      (KABU_API_BASE_URL)
- slack_bot_token        (SLACK_BOT_TOKEN)
- slack_channel_id       (SLACK_CHANNEL_ID)
- duckdb_path            (DUCKDB_PATH)
- sqlite_path            (SQLITE_PATH)
- env                    (KABUSYS_ENV) — 有効値: development, paper_trading, live
- log_level              (LOG_LEVEL)
- is_live / is_paper / is_dev

自動で .env / .env.local を読み込む仕組みがあります（OS 環境変数を上書きしない挙動など）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

リポジトリは src/layout を採用しています。主要なモジュールと役割は次の通りです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定の読み込み・検証
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM ベースセンチメント（score_news）
    - regime_detector.py  — マクロセンチメント + ETF MA で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得/保存/認証/リトライ）
    - pipeline.py         — ETL エントリポイント（run_daily_etl 等）と ETLResult
    - etl.py              — ETLResult の再エクスポート
    - news_collector.py   — RSS 取得・前処理・保存
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - stats.py            — Z-score 等の統計ユーティリティ
    - quality.py          — 品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py            — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

---

## 開発上の注意点 / 設計ポリシー（抜粋）

- ルックアヘッドバイアス防止: 可能な限り datetime.today() / date.today() の直接参照を避け、呼び出し側が対象日を渡す方式を採用しています。
- 冪等性: ETL や保存処理は基本的に ON CONFLICT DO UPDATE / PRIMARY KEY により冪等で動作します。
- フェイルセーフ: 外部 API 呼び出し失敗時はスキップまたは 0 フォールバックして処理を続ける設計です（ログは残ります）。
- セキュリティ: RSS 収集では SSRF 対策、XML の防御（defusedxml）、応答サイズ制限などが組み込まれています。
- テスト容易性: API コール（OpenAI や HTTP）はモジュール内で差し替え可能な設計（関数を patch できるように）です。

---

## 追加情報 / 参考

- OpenAI の呼び出し箇所は gpt-4o-mini 等のモデルを想定しています。API キーは環境変数 `OPENAI_API_KEY` または関数引数で渡せます。
- J-Quants API の使用にはリフレッシュトークンが必要です（settings.jquants_refresh_token）。
- ローカルでの動作検証や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` として明示的に環境を管理することを推奨します。

---

README に含めるべき追加項目（要望があれば対応します）
- 実際の requirements.txt / pyproject.toml の依存一覧
- CI / テストの実行方法
- 運用時の cron / scheduler（ETL の定期実行）サンプル
- Slack 通知や発注フローのサンプルスクリプト

必要であれば上記を追記して README を拡張します。