# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算、研究用ユーティリティ、監査ログ（オーダー・約定トレーサビリティ）などを含みます。

主な目的は、バックテスト／リサーチ用データ基盤および本番に繋がる監査可能な売買フローを提供することです。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（代表的なユースケースと例）
- ディレクトリ構成（主要ファイルの説明）
- 環境変数一覧
- 貢献・ライセンス（簡易）

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、ニュース収集・NLP（OpenAI を利用）、ファクター計算、ETL パイプライン、監査ログ（オーダー・約定のトレース）などを統合したライブラリです。  
設計上の重要ポイントは以下です。

- ルックアヘッドバイアスに配慮（date / datetime を明示的に引数で与える等）
- DuckDB をデータ格納・分析に利用
- J-Quants API 呼び出しはレートリミット・リトライ・トークンリフレッシュ等を実装
- OpenAI（gpt-4o-mini）を JSON Mode で利用し、ニュースのセンチメントや市場レジーム判定を行う
- ニュース収集は SSRF や XML Bomb 対策を実装
- 監査ログ（signal_events / order_requests / executions）でトレーサビリティを確保

---

## 機能一覧

- データ（data/）
  - J-Quants クライアント（fetch/save daily quotes, financials, market calendar）
  - ETL パイプライン（run_daily_etl, 個別 ETL ジョブ）
  - 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - ニュース収集（RSS の取得・正規化・保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ初期化/DB 操作（init_audit_db, init_audit_schema）

- AI（ai/）
  - ニュース NLP（銘柄ごとセンチメント算出: score_news）
  - 市場レジーム判定（ETF 1321 の MA とマクロセンチメントを合成: score_regime）

- Research（research/）
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化（data.stats 参照）

- 共通/設定
  - 環境変数・設定管理（kabusys.config.Settings）
  - 自動 .env ロード（プロジェクトルートにある .env / .env.local を読み込む機能、無効化可）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（型注釈に新しい構文を使用）
- DuckDB（Python パッケージとしてインストールされます）
- OpenAI API の利用には OpenAI の API キーが必要
- J-Quants のリフレッシュトークンが必要（ETL 用）

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要パッケージをインストール
   最低限必要な外部依存は以下です（プロジェクトに requirements.txt がない場合）:
   ```
   pip install duckdb openai defusedxml
   ```
   実運用ではロギングやスケジューリングのため追加パッケージが必要になる場合があります。

4. 環境変数（.env）を準備
   プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。  
   サンプル:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベースディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（代表例）

以下は代表的なユースケースの最小例です。実際にはロギング設定・例外処理・スケジューリングを行ってください。

- DuckDB コネクションを開いて ETL を実行する（日次 ETL）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースに対する銘柄別センチメント（OpenAI 必須）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロセンチメント合成）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用 DuckDB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作られる
  ```

- 設定値の参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意:
- AI 系関数は OpenAI API を使います。api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API を使う ETL は JQUANTS_REFRESH_TOKEN を必要とします。

---

## ディレクトリ構成（主要ファイル）

要点に絞ったツリー（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュースのセンチメントスコアリング
    - regime_detector.py  # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py            # ETL 管理（run_daily_etl など）
    - etl.py                 # ETLResult の再エクスポート
    - calendar_management.py # 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      # RSS 取得と前処理
    - quality.py             # データ品質チェック
    - stats.py               # 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py               # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     # Momentum / Volatility / Value の計算
    - feature_exploration.py # 将来リターン / IC / 統計サマリ
  - research パッケージは data.stats を参照して Z スコア正規化などを行います

各モジュールにはドキュメント文字列が充実しており、設計上の注意点（ルックアヘッドバイアス防止、トランザクション・冪等性、エラーハンドリング）や引数の説明が書かれています。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー（関数引数でも可）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視系）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとプロジェクトルートの .env 自動読み込みを無効化

注意: config.Settings は必須変数が不足した場合に ValueError を投げます。

---

## 開発・貢献

- テスト、型チェック、CI を通して品質を保ってください。プロジェクトには既定のテストコードは付属していませんが、モジュール毎にユニットテストを書きやすい設計になっています（外部 API 呼び出しは差し替え可能に設計）。
- Pull Request 前にローカルで lint / tests を実行してください。

---

## ライセンス

リポジトリにライセンスファイルがない場合は、適切なライセンスを追加してください（例: MIT/Apache-2.0 等）。商用利用や API キーの取り扱いは各サービスの利用規約に従ってください。

---

README は以上です。特定の使い方（例: CI ジョブ、cron による定期 ETL、kabu ステーションとの連携方法など）について詳しい例が欲しければ、用途に合わせたサンプルを追加で作成します。どのワークフローの例を希望しますか？