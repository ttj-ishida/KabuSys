# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants → DuckDB）・ニュース収集・LLM を用いたニュースセンチメント評価・市場レジーム判定・リサーチ用ファクター計算・監査ログ（発注→約定トレース）などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下を目的に設計された内部向けライブラリです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に永続化する ETL パイプライン
- RSS からニュースを収集して銘柄紐付けするニュースコレクタ
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価・市場レジーム判定（LLM 結果は JSON モードで取り扱い）
- リサーチ用途のファクター計算・特徴量探索ユーティリティ
- 監査ログ（signal → order_request → execution）の DuckDB テーブル定義・初期化機能
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の注力点：
- ルックアヘッドバイアス回避（内部で datetime.today() / date.today() を不用意に使わない）
- DuckDB を用いた高速かつ軽量なローカル DB
- 冪等性（ETL/保存処理は ON CONFLICT DO UPDATE 等で既存データを安全に上書き）
- 外部 API 呼び出しはリトライ・レート制御・バックオフを実装

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch / save / トークン管理 / レートリミット
- ニュース
  - RSS 収集（kabusys.data.news_collector）
  - ニュースセンチメント評価（kabusys.ai.news_nlp）
- AI
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（kabusys.ai.regime_detector）
- リサーチ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（kabusys.research）
  - 将来リターン計算・IC 計算・統計サマリー
- データ
  - カレンダー管理・品質チェック・監査ログ初期化（kabusys.data）
- 設定管理
  - 環境変数 / .env の自動読み込み（kabusys.config）

---

## 前提・依存関係

- Python 3.10+
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI など）

（必要に応じてプロジェクトの requirements.txt を用意してください。）

---

## セットアップ手順

1. 仮想環境を作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. パッケージをインストール
   - 開発時（editable install）
     ```bash
     pip install -e .
     ```
   - または最低限の依存を直接インストール
     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必要時）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用
   - DUCKDB_PATH: デフォルトの DuckDB 保存先（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   .env の例（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易例）

以下はライブラリをインポートして主要処理を呼ぶ例です。実運用ではログやエラーハンドリングを適切に追加してください。

- DuckDB 接続例（設定の DUCKDB_PATH を利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（OpenAI API キーが環境変数に設定されている前提）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み件数: {n_written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- リサーチ系関数（ファクター計算）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点：
- AI を使う関数は OpenAI API キーを引数で渡すこともできます（api_key パラメータ）。省略すると環境変数 OPENAI_API_KEY を参照します。
- 各 ETL / 保存処理は冪等的に設計されていますが、バックテスト用途では「事前に取得しておく日付範囲」を明示的に管理してください（Look-ahead バイアス対策）。

---

## ディレクトリ構成（抜粋）

src/kabusys パッケージの主要構成:

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの LLM センチメント評価
    - regime_detector.py    — ETF MA200 + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント + DuckDB 保存
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - news_collector.py     — RSS 収集と raw_news 保存
    - calendar_management.py— マーケットカレンダー管理／営業日判定
    - quality.py            — データ品質チェック
    - stats.py              — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py              — 監査ログ（signal/order_requests/executions）の初期化
    - etl.py                — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 等
    - feature_exploration.py— 将来リターン / IC / 統計サマリー

（上記は主要モジュールの抜粋です。実際のファイル一覧はリポジトリツリーを参照してください。）

---

## 実装上の注意・設計メモ

- 多くの関数は「Look-ahead Bias（先見バイアス）」に注意して実装されています。自動で現在時刻を参照する実装は避け、呼び出し側が target_date を渡す形を基本としています。
- J-Quants クライアントはレートリミット（120 req/min）を守る仕組みが組み込まれています。また 401 時はトークン自動リフレッシュを試行します。
- OpenAI への呼び出しは JSON モード（response_format）を使っています。レスポンスのパース/バリデーション・リトライは各モジュール側で実装済みです。
- DuckDB の executemany は空リストを受け付けないバージョンへの互換処理が各所でされています（空チェックを事前に行う等）。
- .env のパース実装はシェルライクなクォート・エスケープ・コメント処理に対応しています。OS 環境変数は常に優先されます。

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数が設定されていない
  - settings のプロパティが未設定の必須環境変数を参照すると例外になります。`.env` を作成するか、必要な環境変数を export してください。
- OpenAI 呼び出しで失敗する
  - OPENAI_API_KEY の設定、API 使用量制限、ネットワーク等を確認してください。モジュールはリトライとフォールバック（スコア=0）を行いますが、キーの未設定は例外になります。
- DuckDB テーブルがない / スキーマ不整合
  - 初回は適切なスキーマ作成処理（監査ログ用なら init_audit_schema）を実行してください。ETL は既定のテーブルが前提です。

---

## 貢献・ライセンス

この README はコードベースの概要説明を目的としています。実運用・公開用途にする場合は、ドキュメント（API リファレンス、運用手順、セキュリティポリシー）やテスト・CI を整備してください。ライセンスはリポジトリに従ってください。

---

必要があれば、README に含めるセットアップの詳細（systemd ジョブ、cron、Dockerfile、requirements.txt、.env.example の全項目など）を追記します。どの情報を追加しますか？