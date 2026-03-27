# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からの市場データ取得）、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログ（トレーサビリティ）などを含みます。

主な設計方針：
- ルックアヘッドバイアスを避ける（date の明示的取り扱い）
- DuckDB を中心としたローカル分析・保存
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（JSON Mode）をサポート
- 冪等性・健全性重視（ON CONFLICT、トランザクション、リトライ、ログ）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local から自動読み込み（必要に応じて無効化可能）
  - settings オブジェクト経由で設定取得（J-Quants、kabu API、Slack、DB パス等）
- Data / ETL
  - J-Quants API クライアント（差分取得、ページネーション、リトライ、レート制御）
  - ETL パイプライン（株価 / 財務 / カレンダーの差分取得と保存）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - マーケットカレンダー管理（営業日判定等）
  - ニュース収集（RSS）と前処理（SSRF 対策、サイズ制限、トラッキング削除）
  - 監査ログ（signal_events / order_requests / executions テーブル）と初期化ユーティリティ
- AI（ニュースNLP / 市場レジーム判定）
  - ニュースの銘柄別センチメント解析（OpenAI）
  - ETF（1321）の MA200 とマクロニュースから市場レジーム（bull/neutral/bear）判定
- Research（因子計算・特徴量探索）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 共通ユーティリティ
  - 統計ユーティリティ（Zスコア正規化 等）
  - DuckDB 操作ヘルパー

---

## セットアップ手順

想定 Python バージョン: 3.10 以上（typing の | 表記を使用）

1. リポジトリを取得（ここでは手動でソースを配置済みと仮定）

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   追加でログやテストに必要なパッケージがある場合は適宜追加してください。

4. 環境変数 / .env 設定  
   プロジェクトルート（pyproject.toml または .git があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。テストなどで自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   .env の最低例（実運用ではシークレットを適切に管理してください）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI (ニュースNLP / regime detector で使用)
   OPENAI_API_KEY=your_openai_api_key

   # kabuステーション（発注等に利用する設定）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack 通知（オプション）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # DB パス（デフォルトを上書きする場合）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境フラグ
   KABUSYS_ENV=development  # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

5. DuckDB 初期スキーマ（監査ログなど）を作成する場合:
   - 監査 DB を初期化して接続を得る簡単な例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db("data/audit.duckdb")
     # 以後 conn を使って監査テーブルへ記録が可能
     ```

---

## 使い方（主要 API の例）

以下は典型的な利用パターンの例です。実行は Python スクリプト内で行います。

1. Settings（環境変数読み取り）
   ```python
   from kabusys.config import settings

   print(settings.jquants_refresh_token)  # 必須: 未設定なら ValueError
   print(settings.duckdb_path)            # Path オブジェクト
   ```

2. 日次 ETL を実行する
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニュースセンチメント（銘柄別）をスコア化
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect(str(settings.duckdb_path))
   n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → 環境変数を使用
   print("written", n_written)
   ```

4. 市場レジーム（daily）
   ```python
   from kabusys.ai.regime_detector import score_regime
   import duckdb
   from datetime import date

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. ファクター計算（研究用途）
   ```python
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   import duckdb
   from datetime import date

   conn = duckdb.connect(str(settings.duckdb_path))
   momentum = calc_momentum(conn, date(2026, 3, 20))
   volatility = calc_volatility(conn, date(2026, 3, 20))
   value = calc_value(conn, date(2026, 3, 20))
   ```

6. 監査ログスキーマを既存 DuckDB に初期化
   ```python
   from kabusys.data.audit import init_audit_schema
   import duckdb

   conn = duckdb.connect(str(settings.duckdb_path))
   init_audit_schema(conn, transactional=True)
   ```

注意:
- OpenAI を使う関数（score_news, score_regime）は API キーを引数に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API へのアクセスは JQUANTS_REFRESH_TOKEN を必要とします（settings.jquants_refresh_token）。

---

## 環境/セキュリティ注意点

- シークレット（API トークン等）はソース管理しないこと。`.env` を .gitignore に入れて運用してください。
- news_collector は SSRF 対策やレスポンスサイズチェックなどを実装していますが、RSS ソースは信頼できるもののみ追加してください。
- 本リポジトリは実際の発注ロジックそのもの（実際のブローカー連携）を含む場合、live モードでの実行は十分な検証と安全策（サンドボックスでの試験）を行ってください。

---

## ディレクトリ構成

以下は主要モジュールと簡単な説明です（src/kabusys 以下）。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env の自動読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄ごとに集約して OpenAI でセンチメントを得る
    - regime_detector.py — ETF MA とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の公開
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - audit.py — 監査ログ（DDL、初期化ユーティリティ）
    - news_collector.py — RSS 収集・前処理・保存ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン、IC、rank、summary 等
  - ai、data、research 以下にあるユーティリティ群はそれぞれの責務に分かれています。

---

## テスト / 開発メモ

- 自動 .env 読み込みは、プロジェクトルート（.git または pyproject.toml がある階層）を基準に探します。CWD に依存しません。
- テスト中に .env 自動読み込みを抑止したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI / J-Quants のネットワーク呼び出しはリトライやバックオフ処理が実装されていますが、API 利用料やレートには注意してください。
- DuckDB の executemany はバージョン差による挙動の差があるため、空のパラメータでの executemany を避けるなど互換性処理を行っています。

---

## ライセンス / 貢献

この README ではライセンスファイルやコントリビューションポリシーの情報は含まれていません。実際のリポジトリに LICENSE / CONTRIBUTING を追加して運用してください。

---

必要であれば、各モジュール（ETL のより詳細な使い方、news_collector のカスタム RSS 追加手順、監査テーブルのサンプルクエリなど）についての具体的なドキュメントを作成します。どの項目を詳細化したいか教えてください。