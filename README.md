# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション / RSS / OpenAI（LLM）などを組み合わせ、データ収集（ETL）、品質チェック、ニュースNLP、レジーム判定、監査ログ、リサーチ用ファクター計算などを提供します。

主な目的は「データ基盤 + 研究（リサーチ） + 戦略用ユーティリティ」を一貫して提供し、バックテストや運用の基盤を支えることです。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXマーケットカレンダー
  - レート制御・リトライ・トークン自動リフレッシュ対応
- ETLパイプライン
  - 差分取得、バックフィル、品質チェック（欠損・重複・スパイク・日付整合）
  - 日次ETLのエントリポイント `run_daily_etl`
- ニュース収集
  - RSS 取得、URL 正規化、前処理、raw_news への冪等保存、SSRF 対策、サイズ制限
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM（gpt-4o-mini）で評価し `ai_scores` に保存（`score_news`）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成、`score_regime`）
  - JSON Mode / 冪等・リトライ設計・フェイルセーフ
- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（`calc_momentum`, `calc_volatility`, `calc_value`）
  - 将来リターン計算、IC（スピアマン）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブル定義・初期化（冪等、UTC タイムスタンプ）
  - 監査DB 初期化ユーティリティ（`init_audit_db`）

---

## 要求環境・依存

- Python 3.10+
- 主な依存パッケージ（pipでインストール）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで動作する部分も多いです）

requirements.txt を用意する場合は上記を含めてください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... (省略)

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. インストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - または開発用にパッケージ化されていれば:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動読込されます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数（最小例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...  （LLM を使う機能で必須）
     - DUCKDB_PATH=data/kabusys.duckdb  （任意）
     - SQLITE_PATH=data/monitoring.db  （任意）
     - KABUSYS_ENV=development|paper_trading|live  （省略時 `development`）
     - LOG_LEVEL=INFO|DEBUG|...

   - .env のパースはコメント・クォート・export 形式に対応しています。

5. データベース初期化（監査DB 例）
   - Python REPLやスクリプトで：
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - これにより監査テーブルが作成されます（UTC タイムゾーン固定）。

---

## 使い方（代表的な例）

下記は最小限の利用例です。実運用ではログや例外処理・バックグラウンドスケジューラ等を組み合わせてください。

- DuckDB 接続の作成（ETL / AI / research の引数に渡す）
  - import duckdb, pathlib
  - conn = duckdb.connect(str(pathlib.Path("data/kabusys.duckdb")))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日（内部で営業日に調整）

- ニューススコア（LLM）を日次で実行して ai_scores に保存
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None->環境変数 OPENAI_API_KEY を参照

- 市場レジーム判定（MA200 + マクロセンチメント）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査DB 初期化（別 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- 研究用関数例
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - records = calc_momentum(conn, target_date=date(2026,3,20))
  - from kabusys.data.stats import zscore_normalize
  - normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])

注意点:
- LLM を呼ぶ関数は api_key を引数で注入できます（テスト容易性）。引数を None にすると環境変数 OPENAI_API_KEY を参照します。
- ETL / データ取得は J-Quants の認証トークン（refresh token）を `.env` に設定しておく必要があります。
- news_collector は RSS の SSRF 対策とサイズ制限が組み込まれています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabuステーション API ベースURL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネルID（必須）
- OPENAI_API_KEY        : OpenAI API キー（LLM 機能で必須）
- DUCKDB_PATH           : DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite ファイルパス（監視用など）
- KABUSYS_ENV           : 開発環境 (development|paper_trading|live)
- LOG_LEVEL             : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動ロードを無効化

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の読み込み・バリデーション（.env 自動ロード機能）
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py
      - ニュース記事を銘柄ごとに統合して LLM に投げ、ai_scores に保存する機能
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 他）
    - etl.py
      - ETL の公開インターフェース（ETLResult を再エクスポート）
    - news_collector.py
      - RSS 収集・前処理・保存（SSRF・サイズ制限・URL 正規化）
    - calendar_management.py
      - 市場カレンダー管理、営業日判定ユーティリティ
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py
      - momentum/value/volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン・IC・統計サマリー・rank 等

---

## 開発・運用メモ

- 設計方針の多くは「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗はスキップして継続）」を重視しています。バックテストや運用時はそれらを意識して利用してください。
- DuckDB を用いているためファイルベースで簡単にローカル実行できます。運用では永続ストレージや定期ジョブ（cron / Airflow / Prefect 等）でスケジュールしてください。
- OpenAI 呼び出しは JSON Mode を想定した厳密なレスポンス解析を行っていますが、現実のレスポンス取り扱いにはフェイルセーフがあるため、ログを監視して不整合を確認してください。
- news_collector の fetch_rss は defusedxml と SSRF 対策を実装しています。外部 RSS を増やす際はソースの信頼性と帯域に注意してください。

---

README はここまでです。必要であればセットアップの具体的なコマンド（requirements.txt の生成、systemd / cron のサンプル、CI 設定など）や、より詳細な API 使用例（引数や戻り値のサンプル）も追加できます。どの部分を詳しく記載しますか？