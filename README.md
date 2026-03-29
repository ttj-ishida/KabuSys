# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームのライブラリ群です。  
データ ETL、ニュース NLP（LLM）によるセンチメント評価、市場レジーム判定、研究用ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。

主な方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today()/date.today() を直接参照しない箇所が多い）。
- DuckDB を用いたローカルデータレイク設計（冪等保存、ON CONFLICT を利用）。
- 外部 API 呼び出しはリトライ・バックオフ・レート制御などの堅牢化処理を内蔵。
- OpenAI（gpt-4o-mini）を用いたニュース解析は JSON Mode を利用して結果を安全にパース。

---

## 機能一覧

- data
  - ETL パイプライン（J-Quants からの株価、財務、カレンダーの差分取得と保存）
  - ニュース収集（RSS → raw_news、news_symbols 連携）
  - カレンダー管理（営業日判定、next/prev_trading_day など）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - J-Quants API クライアント（レートリミット・再試行・トークンリフレッシュ対応）
  - 監査ログ（signal_events / order_requests / executions）の初期化・管理
  - 統計ユーティリティ（Z スコア正規化等）

- ai
  - ニュースセンチメント分析（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）: ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM を合成

- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- config
  - 環境変数読み込み（プロジェクトルートの `.env` / `.env.local` を自動ロード）
  - settings オブジェクトで必要設定を取得（必須チェックを含む）

---

## 必要条件

- Python 3.10+
- 必要な Python パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

実行環境によっては他に標準ライブラリのみで動作する箇所があります。プロジェクト配布時は requirements.txt を用意してください（本リポジトリでは例示のみ）。

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージをeditableでインストールできる場合:
# pip install -e .
```

---

## 環境変数（主なもの）

以下の環境変数は settings（kabusys.config.settings）から参照されます。`.env`／`.env.local` をプロジェクトルートに置くと自動読み込みされます（無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須:
- JQUANTS_REFRESH_TOKEN  
  - J-Quants のリフレッシュトークン（ETL の認証に使用）
- KABU_API_PASSWORD  
  - kabuステーション API のパスワード
- SLACK_BOT_TOKEN  
  - Slack 通知用ボットトークン
- SLACK_CHANNEL_ID  
  - Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: "http://localhost:18080/kabusapi")
- DUCKDB_PATH (デフォルト: "data/kabusys.duckdb")
- SQLITE_PATH (デフォルト: "data/monitoring.db")
- KABUSYS_ENV (有効値: "development", "paper_trading", "live"; デフォルト: "development")
- LOG_LEVEL (有効値: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"; デフォルト: "INFO")
- OPENAI_API_KEY (news_nlp / regime_detector の API 呼び出しに使用。関数呼び出し時に api_key 引数から注入可能)

注意:
- settings の必須値が未設定だと ValueError が発生します（例: settings.jquants_refresh_token）。
- 自動ロードは .env → .env.local の順で上書きされます（OS 環境変数が最優先）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンし仮想環境を作成
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   ```

2. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必要なキーを設定します。例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=secret
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     ```

3. DuckDB データベースを作る（必要に応じて）
   - 監査ログ用 DB 初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
     # conn は duckdb.DuckDBPyConnection
     ```

4. 必要テーブルの作成（schema 初期化等がある場合は別モジュールで用意）
   - audit.init_audit_schema は自動で必要なテーブルを作成します（init_audit_db で transactional=True の状態で呼ばれます）。

---

## 使い方（代表的な例）

以下は Python インタプリタやスクリプトから呼ぶ最小例です。適宜ロギング設定やパスを調整してください。

- ETL（日次パイプライン）を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（ai_score の計算）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  # api_key を明示することも可能:
  # score_news(conn, date(2026,3,20), api_key="sk-...")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化（ファイル作成＆スキーマ適用）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # テーブル作成まで行う
  ```

注意点:
- OpenAI 呼び出しはネットワークや API レートに依存します。API キーは環境変数 OPENAI_API_KEY に設定するか、関数に明示的に渡してください。
- ETL/AI モジュールは基本的に DuckDB 接続を引数として受けます。トランザクションの扱いやスコープは呼び出し側で管理できます。

---

## 実装上の設計メモ（運用上のポイント）

- 多くの箇所で「ルックアヘッドバイアス防止」が明示されています。バックテスト/運用の際は target_date を明示して使用してください。
- J-Quants クライアントはレート制御（120 req/min）・リトライ・トークン自動更新を備えています。get_id_token() / fetch_* / save_* の流れを使って安全に ETL が可能です。
- OpenAI 呼び出しは JSON モードで結果を受け取るため、レスポンスのパースと検証を厳密に行っています。API エラー時はフォールバックやスキップで継続する設計です（フェイルセーフ）。
- news_collector は SSRF / XML Bomb / 大容量応答対策（defusedxml, ホストチェック, MAX_RESPONSE_BYTES）を実装しています。

---

## ディレクトリ構成（主なファイル）

（プロジェクトルート: src/kabusys の下の主なモジュール）

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数読み込み・settings
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py        — ニュースの LLM ベーススコアリング（score_news）
  - regime_detector.py — ETF + マクロニュースで市場レジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント + DuckDB 保存処理
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult 再エクスポート
  - news_collector.py      — RSS 収集・前処理・保存
  - calendar_management.py — マーケットカレンダー管理 / 営業日判定
  - quality.py             — データ品質チェック
  - stats.py               — 統計ユーティリティ（zscore_normalize）
  - audit.py               — 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）
- src/kabusys/research/
  - __init__.py
  - factor_research.py     — momentum/volatility/value 等のファクター計算
  - feature_exploration.py — forward returns, IC, factor summary, rank

---

## よくある質問／トラブルシューティング

- .env を読み込まない  
  - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。
- OpenAI レスポンスのパースに失敗する  
  - モデル応答が JSON 形式ではない場合やタイムアウト時は、関数側でログ出力の上スコアを 0.0 にフォールバックします。API キーやレート制限を確認してください。
- DuckDB にアクセスできない／権限エラー  
  - 指定したパスの親ディレクトリが存在するか確認してください。init_audit_db は親ディレクトリが存在しない場合に自動作成します（ファイル接続時）。

---

この README はコードベースの概要と基本的な使い方をまとめたものです。詳細な API 仕様や運用手順は個別モジュール（kabusys.data.pipeline, kabusys.ai.news_nlp 等）のドキュメントコメントをご参照ください。必要であればサンプルスクリプトや CI / デプロイ手順の追記も対応します。