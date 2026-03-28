# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP、ファクター計算、監査ログ、研究ユーティリティ、LLM を用いた市場レジーム判定などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやデータプラットフォーム向けに設計された Python モジュール群です。主な目的は次の通りです。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）を安全かつ冪等に取得・保存
- RSS ニュース収集と前処理、記事→銘柄紐付け
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント / マクロセンチメント評価
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログテーブル（シグナル→発注→約定のトレーサビリティ）
- kabuステーション等への発注層とモニタリング（パッケージ構成に含まれるエクスポート）

コードベースは Look-ahead バイアス防止や堅牢なエラーハンドリング、冪等性、API レート制御、SSRF や XML 関連の安全対策を設計方針にして実装されています。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・トークン管理・レート制御）
  - pipeline: 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF・GZIP・XML 防御）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal_events, order_requests, executions）定義と初期化
  - stats: 共通統計ユーティリティ（Zスコア正規化）
- ai/
  - news_nlp: ニュースを銘柄単位で LLM に送って ai_scores へ書き込む処理
  - regime_detector: ETF(1321) の MA200 乖離とマクロセンチメントの合成による市場レジーム判定
- research/
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン相関）、統計サマリー等
- config: 環境変数の自動読み込み・設定管理（.env, .env.local のサポート）
- その他: パッケージ公開用 __init__（version 情報等）

---

## 必要な環境変数

主に以下の環境変数が利用・要求されます。プロジェクトルートの `.env.example` を参考に `.env` を作成してください（自動ロード機能あり）。

必須（使用する機能に応じて必須）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client）
- OPENAI_API_KEY — OpenAI の API キー（ai/news_nlp, regime_detector）
- KABU_API_PASSWORD — kabu API のパスワード（execution 層）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（monitoring/通知）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルトあり:
- KABUSYS_ENV — 動作環境 (development | paper_trading | live)（default: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（default: data/monitoring.db）

テスト・CI で自動読み込みを無効にする:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

前提: Python 3.10+（PEP 604 の型構文などを使用）を推奨します。

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール  
   コードから必要となる主なパッケージ:
   - duckdb
   - openai
   - defusedxml

   例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt がある場合はそれを使用してください。）

4. .env ファイルを作成  
   プロジェクトルートに `.env`（および必要なら `.env.local`）を作成し、必要な環境変数を設定します。例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=secret
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データフォルダ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は主要機能の呼び出し例です。詳細は各モジュールの関数 docstring を参照してください。

- DuckDB 接続の作成（設定からパスを使用）
  ```python
  from kabusys.config import settings
  import duckdb

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（J-Quants から差分取得して保存・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定することも可
  print(result.to_dict())
  ```

- ニュースの LLM スコアリング（ai_scores へ書き込む）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（監査専用 DuckDB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  ```

- 研究用ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意:
- OpenAI を使う関数は環境変数 OPENAI_API_KEY または関数引数 api_key によりキーを解決します。キーが無いと ValueError を投げます。
- ETL / API 呼び出しはネットワーク・API 依存のため、実行には該当トークンが必要です。

---

## よくあるトラブルシューティング

- 環境変数未設定によるエラー:
  - ValueError: "環境変数 'JQUANTS_REFRESH_TOKEN' が設定されていません" などが出る場合、`.env` を作成するか環境変数を設定してください。
- 自動 .env 読み込みを無効化したい:
  - テスト時などは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し失敗時:
  - レート制限や一時的なネットワーク障害はリトライしますが、最終的にフェイルセーフとしてスコアを 0.0 にするなどの挙動があります。ログを確認してください。
- DuckDB executemany の空リスト:
  - 一部の関数は DuckDB のバージョン制約により executemany に空リストを渡さないよう設計されています。これに起因する問題があれば DuckDB のバージョン確認をしてください。

---

## ディレクトリ構成

主要ファイル / モジュール構成（src/kabusys）:

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
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research パッケージは data.stats を依存としてファクター実装を提供
- その他: strategy, execution, monitoring パッケージは __all__ に列挙（実装ファイルはこのコードベース内で分割されている想定）

（上記はソース構成の抜粋です。実際のリポジトリには追加サブモジュールや CLI / tests 等が存在する場合があります。）

---

## 開発・テストに関する注意

- 型注釈は Python 3.10+ の構文を使っています（Union 短縮記法等）。
- テスト時は外部 API 呼び出しをモックすることを推奨します（jquants_client._request、news_collector._urlopen、ai の _call_openai_api 等は差し替えポイントが用意されています）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を起点に行われます。CI などで意図せず読み込まれる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

README に記載のない詳細な使い方や、特定の機能（例: 発注実行 / kabu API 統合、Slack 通知の設定、バックテストの具体的な手順）については、該当モジュールの docstring / 関数コメントを参照してください。必要であれば、その部分のサンプルや手順を追加で作成します。