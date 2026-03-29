# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）、市場レジーム判定などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム開発を支援するモジュール群です。主に以下を目的とします。

- J-Quants API を用いた株価・財務・市場カレンダー等の ETL
- RSS を用いたニュース収集と LLM を用いたニュースセンチメント評価
- ファクター計算・特徴量探索・統計ユーティリティ（研究用）
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- 監査ログ（シグナル → 発注 → 約定までのトレーサビリティ）
- データ品質チェック

設計上の特徴:
- Look-ahead bias に対する配慮（日付参照の明示化、DB クエリでの排他条件など）
- 冪等性（ETL 保存は ON CONFLICT DO UPDATE 等）
- フェイルセーフ（外部API失敗時は例外を投げずにフォールバックする箇所あり）
- DuckDB ベースのローカルデータ格納（デフォルトパスは data/kabusys.duckdb）

---

## 主な機能一覧

- data パッケージ
  - ETL: J-Quants からの daily quotes / financial statements / market calendar の取得 (kabusys.data.pipeline)
  - カレンダー管理（営業日判定・next/prev trading day 等）(kabusys.data.calendar_management)
  - J-Quants クライアント（認証・リトライ・ページネーション）(kabusys.data.jquants_client)
  - ニュース収集（RSS → raw_news テーブル）(kabusys.data.news_collector)
  - データ品質チェック (kabusys.data.quality)
  - 監査ログスキーマ初期化 / DB (kabusys.data.audit)
  - 統計ユーティリティ (z-score 正規化等) (kabusys.data.stats)
- ai パッケージ
  - ニュース NLP スコアリング（gpt-4o-mini を利用）(kabusys.ai.news_nlp)
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM スコアを合成）(kabusys.ai.regime_detector)
- research パッケージ
  - ファクター計算（Momentum / Volatility / Value）(kabusys.research.factor_research)
  - 特徴量探索・IC 計算 (kabusys.research.feature_exploration)
- その他
  - 環境設定管理（.env 自動ロード、必須変数チェック）(kabusys.config)
  - パッケージメタデータ (kabusys.__init__)

---

## セットアップ手順

1. リポジトリをクローン／配置

   git リポジトリルート（.git または pyproject.toml があるディレクトリ）がある位置を基に .env 自動読み込みを行います。

2. Python 環境を準備（例: Python 3.10+ を推奨）

3. 必要な依存パッケージをインストール（プロジェクト側で requirements が用意されている前提がないため代表的なものを記載）

   pip install duckdb openai defusedxml

   （必要に応じて追加パッケージをインストールしてください）

4. パッケージを開発モードでインストール（ローカル開発）

   python -m pip install -e .

5. 環境変数の準備

   プロジェクトルートに `.env`（および必要なら `.env.local`）を配置します。自動読み込みはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabuAPI ベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（省略時: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時: INFO）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に使用）

   .env の自動読み込みルール:
   - プロジェクトルート (.git または pyproject.toml があるディレクトリ) を探索して `.env` と `.env.local` を読み込みます
   - 読み込みは OS の環境変数を保護（既存の環境変数は上書きされない）形で行われます
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途）

6. データベース用ディレクトリの作成（必要に応じて）

   デフォルトでは `data/` 下を想定しているので、必要なら作成します。

---

## 使い方（簡易サンプル）

以下は最小限の使用例です。実際はログ設定や例外処理、API キーの管理等を行ってください。

- DuckDB 接続を作成して日次 ETL を実行（J-Quants からデータ取得）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP スコアリングを実行（OpenAI API 必須）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} ai_scores")

- 市場レジーム判定を実行（OpenAI API 必須）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DuckDB の初期化

  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit_kabusys.duckdb")
  # conn をアプリの監査ログ書き込みに利用

- 研究用ファクター計算（例: Momentum）

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(recs))

注意点:
- LLM を呼ぶ処理（news_nlp / regime_detector）は OpenAI API（gpt-4o-mini 等）を使用します。OPENAI_API_KEY を設定してください。
- ETL は J-Quants API のレート制限を尊重する設計です。ID トークン自動リフレッシュやリトライロジックを内包しています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数・設定管理（.env 自動ロード・必須チェック）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントスコアリング（OpenAI 呼び出し・バッチ処理）
  - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース LLM）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py — J-Quants API クライアント（取得・保存用ユーティリティ）
  - news_collector.py — RSS 取得・正規化・raw_news 保存
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログスキーマ初期化・DB ユーティリティ
  - etl.py — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- monitoring/ (パッケージ名として __all__ に存在しますが個別ファイルは本リストに含まれません)
  - （監視・アラート関連モジュールを想定）

各モジュールは docstring と詳細な処理フロー/設計方針を備えており、DuckDB 接続を引数に受け取って副作用（DB 書き込み）を行う形が多くなっています。

---

## 実運用上の注意・設計ポリシー

- Look-ahead bias 対策: 内部実装は datetime.today() などを直接参照しない設計の箇所が多く、バックテスト時は明示的に日時を渡して使用してください。
- 冪等性: ETL の保存処理は ON CONFLICT DO UPDATE 等で重複を避けますが、外部操作や別プロセスからの書き込みに注意してください。
- 外部 API エラー: ネットワーク・API エラー時はリトライやフォールバック（スコア 0.0 など）で継続する設計です。重大なエラーはログに記録されます。
- セキュリティ: news_collector では SSRF 対策や XML パースの安全化（defusedxml）を行っています。RSS ソースの設定は慎重に行ってください。

---

## トラブルシュート

- .env が読み込まれない場合
  - プロジェクトルートが特定できない場合は自動ロードをスキップします（.git または pyproject.toml を基準）。
  - 自動ロードを無効化している可能性: KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- OpenAI / J-Quants の認証エラー
  - 必須の環境変数が足りない場合は config.Settings のプロパティが ValueError を投げます。ログと例外を確認してください。
- DuckDB への書き込みエラー
  - パーミッションやパスの存在確認、または競合トランザクションに留意してください。

---

必要であれば README を拡張して、CI / テスト実行方法、実運用のデプロイ手順、具体的な .env.example（サンプル）や schema 初期化スクリプト例などを追記できます。どの項目を詳しく追記するか指示をください。