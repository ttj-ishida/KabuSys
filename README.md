# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants／RSS）、ETL、データ品質チェック、リサーチ（ファクター計算）、AI を使ったニュースセンチメント・市場レジーム判定、監査ログ（トレーサビリティ）などを含みます。

---

## 主な特徴

- データ取得
  - J-Quants API 経由での株価（OHLCV）、財務データ、上場情報、JPX カレンダー取得（ページネーション＆リトライ対応）
  - RSS からのニュース収集（SSRF / サイズ / トラッキング除去対策付き）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - DuckDB への冪等保存（ON CONFLICT による上書き）
- データ品質管理
  - 各種チェック関数群と QualityIssue で問題を収集・報告
- リサーチ機能
  - モメンタム / バリュー / ボラティリティなどのファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリ、Zスコア正規化
- AI（OpenAI）連携
  - ニュースごとのセンチメント評価（gpt-4o-mini）と銘柄別 ai_scores 登録
  - ETF（1321）200日移動平均乖離 + マクロニュースセンチメントから市場レジーム（bull/neutral/bear）判定
  - レートリミット／リトライ／レスポンス検証を考慮
- 監査ログ/トレーサビリティ
  - signal_events / order_requests / executions テーブルでシグナル→発注→約定を完全トレース
  - init_audit_schema / init_audit_db により DB 初期化可能

---

## 要件

- Python 3.10+
- ライブラリ（概要）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで実装されているユーティリティも多く使用）

実際のインストールは下記セットアップ手順参照。

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone ... && cd your-repo

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - 必要なパッケージをインストール（例）
     - pip install duckdb openai defusedxml

   - 開発用にパッケージとしてインストールする場合:
     - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置けます（config モジュールが自動ロードします。後述の優先順位を参照）。
   - 必須環境変数例:
     - JQUANTS_REFRESH_TOKEN (J-Quants リフレッシュトークン)
     - KABU_API_PASSWORD (kabuステーション API パスワード)
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
     - OPENAI_API_KEY (OpenAI 呼び出しで未指定の場合に参照)
   - 任意 / デフォルト値:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - KABU_API_BASE_URL: http://localhost:18080/kabusapi（デフォルト）
   - 自動 .env ロード
     - 優先順位: OS 環境変数 > .env.local > .env
     - 無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードをスキップ

5. データベース初期化（監査ログ用の例）
   - Python REPL / スクリプトで:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
     - ※ 親ディレクトリが無ければ自動作成します

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（ETL で使用）
  - KABU_API_PASSWORD: kabuステーション API 用パスワード
  - SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
  - SLACK_CHANNEL_ID: 通知先チャンネル ID
- AI 関連
  - OPENAI_API_KEY: OpenAI を使用する関数（news_nlp.score_news, regime_detector.score_regime など）が参照
- システム設定（オプション）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: ログレベル（デフォルト INFO）
  - DUCKDB_PATH, SQLITE_PATH, KABU_API_BASE_URL
- 自動読み込み制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを停止

---

## 使い方（例）

以下は最小限の使用例です。DuckDB への接続を作成し、ETL や AI スコアリング等を呼び出します。

- DuckDB 接続作成例
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL 実行（株価・財務・カレンダー・品質チェック）
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースセンチメント（ai_score）を作成
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - # OPENAI_API_KEY が環境変数にあるか、api_key 引数で指定
  - written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  - print(f"書き込み銘柄数: {written}")

- 市場レジーム判定
  - from datetime import date
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ初期化（既存 DB に監査スキーマを追加）
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

注：
- AI 系関数（score_news / score_regime）は OpenAI のレスポンスに依存します。API キーが不要な場合でも明示的に api_key を渡すことでテスト時のモックが容易になります。
- ETL / API 呼び出しはネットワークや外部 API に依存するため、実運用ではリトライやログ監視を行ってください。

---

## ディレクトリ構成（主なファイル）

（パッケージは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメント（OpenAI）および関連ユーティリティ
    - regime_detector.py   — 市場レジーム判定（MA200 + マクロセンチメント合成）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理（営業日判定、next/prev 等）
    - pipeline.py            — ETL パイプラインと run_daily_etl
    - etl.py                 — ETLResult 再エクスポート
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存関数
    - news_collector.py      — RSS 収集（SSRF 対策、前処理、保存）
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - quality.py             — データ品質チェック群（欠損・スパイク・重複等）
    - audit.py               — 監査ログ（シグナル／発注／約定）DDL と初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility ファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等

---

## 開発・テストに関するメモ

- config モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` / `.env.local` を自動ロードします。テスト時に自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しや外部 API 呼び出し部分はモジュール内の _call_openai_api / _urlopen 等をモック（patch）してテストしやすい設計になっています。
- DuckDB に対する executemany の空リスト渡しはバージョンによって例外になることがあるため、実装側で事前チェックを行っています（空パラメータは送らない）。

---

## 貢献や問い合わせ

バグ報告、改善提案や質問はリポジトリの Issue に記載してください。機密情報（API トークン等）は直接共有しないでください。

---

以上が本プロジェクトの README です。必要であれば項目ごとのサンプルスクリプトや .env.example のテンプレートも作成します。どの部分を詳しく書きたいか教えてください。