# KabuSys

日本株向けのデータプラットフォーム兼自動売買ライブラリ。  
J-Quants・RSS・OpenAI 等を組み合わせてデータ取得（ETL）・品質チェック・ニュース NLU・市場レジーム判定・研究用ファクター計算・監査ログ管理を行うモジュール群を提供します。

## 主な特徴
- J-Quants API を用いた株価・財務・カレンダーの差分取得（ページネーション・レート制御・リトライ付き）
- DuckDB を中心としたローカル DB 保存（冪等保存、ON CONFLICT）
- データ品質チェック（欠損、重複、スパイク、日付整合性）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去、記事ID生成）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）スコアリング
- ETF（1321）200日移動平均とマクロニュースの融合による市場レジーム判定（bull/neutral/bear）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 監査ログ（signal / order_request / executions）スキーマ初期化支援（トレーサビリティ）

---

## 機能一覧（抜粋）
- 環境/設定管理: kabusys.config
  - .env の自動読み込み（プロジェクトルート検出）、必須環境変数チェック
- データ収集/ETL: kabusys.data.pipeline, jquants_client, news_collector
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- データ品質: kabusys.data.quality
  - check_missing_data, check_duplicates, check_spike, check_date_consistency, run_all_checks
- ニュースNLP: kabusys.ai.news_nlp
  - score_news (銘柄別 ai_scores へ書込)
- 市場レジーム判定: kabusys.ai.regime_detector
  - score_regime (market_regime テーブルへ書込)
- 研究（Research）: kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- 監査ログスキーマ: kabusys.data.audit
  - init_audit_schema, init_audit_db
- ユーティリティ: kabusys.data.stats（zscore_normalize）、calendar_management（営業日ロジック）

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. パッケージ依存をインストール
   - 本リポジトリに requirements.txt がない場合は主要依存をインストールしてください（例）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 開発モードでインストール（プロジェクトのルートに setup.cfg/pyproject.toml がある想定）
   ```bash
   pip install -e .
   ```

3. 環境変数設定 (.env)
   - プロジェクトルート（.git または pyproject.toml を含む階層）を基準に `.env` と `.env.local` の自動読み込みを行います。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知用（必要な場合）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時も引数で渡せます）
   - データベースパス（デフォルト値）:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db

   例 `.env`（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要ユースケース）

- DuckDB 接続作成（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略すると今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア取得（銘柄別）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーを env に設定するか、api_key 引数で渡す
  num_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written: {num_written}")
  ```

- 市場レジーム判定（ETF 1321 + マクロニュース）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB を初期化（監査専用 DB を作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn は初期化済み DuckDB 接続
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 設定参照
  ```python
  from kabusys.config import settings

  print(settings.duckdb_path)
  print(settings.is_live, settings.log_level)
  ```

---

## 自動 .env ロード仕様（重要）
- 起点: このモジュールのファイル位置から親ディレクトリをさかのぼり、`.git` または `pyproject.toml` を発見した位置をプロジェクトルートとみなします。
- 読込順:
  1. OS 環境変数（最優先）
  2. .env.local（存在する場合は OS を上書きしない形で読み込み）
  3. .env（さらに未設定キーのみセット）
- 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると自動ロードをスキップします（テスト用）。

---

## ディレクトリ構成（主要ファイル）
（リポジトリ内 `src/kabusys` 配下を抜粋）

- src/kabusys/
  - __init__.py (パッケージ定義、公開サブパッケージ)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメント取得・ai_scores 書込)
    - regime_detector.py (市場レジーム判定・market_regime 書込)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント, 保存関数)
    - pipeline.py (ETL パイプライン / ETLResult)
    - etl.py (ETLResult エクスポート)
    - news_collector.py (RSS 収集・前処理)
    - quality.py (データ品質チェック)
    - stats.py (統計ユーティリティ: zscore_normalize)
    - calendar_management.py (市場カレンダー / 営業日ロジック)
    - audit.py (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py (モメンタム/ボラティリティ/バリュー計算)
    - feature_exploration.py (将来リターン, IC, 統計サマリー)
  - monitoring/ (フォルダ名が __all__ にあるが個別ファイルはここで管理される想定)
  - execution/, strategy/, monitoring/ など（実運用の発注・戦略・監視ロジック用）

---

## 注意点 / 運用上のポイント
- OpenAI 呼び出し: API 呼び出しが失敗した場合、各モジュールはフェイルセーフとしてスコアを 0.0 にフォールバックする等の設計がなされていますが、API キーは必須です（関数引数で明示的に渡すことも可能）。
- Look-ahead バイアス対策: 多くの処理で date 引数を外部から与え、内部で datetime.today() 等を参照しない実装になっています。バックテストで使う場合は対象日以前のデータのみが DB に入っていることを確認してください。
- ETL は部分失敗時でも他処理は継続する設計（結果は ETLResult で集約）。品質チェックの重大度に応じて呼び出し側で停止判断を行ってください。
- news_collector は SSRF 対策や受信サイズ制限を実装しています。外部 RSS を使う場合は許可ホスト・スキームに注意してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、空チェックが組み込まれています。

---

## サポート / 開発
- PR/Issue を通してバグ報告や機能要望をお願いします。
- ユニットテストは各モジュールの外部依存（ネットワーク、API）をモックして実行することを推奨します（コード内から差し替え可能な内部関数が用意されています）。

---

README は以上です。必要であれば README に
- .env.example の完全サンプル
- 初期スキーマ作成用 SQL やスクリプト例
- CI / デプロイ手順（systemd / cron）などを追加します。どの情報を追加希望か教えてください。