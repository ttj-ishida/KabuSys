# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ KabuSys のリポジトリ向け README（日本語）。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究（ファクター計算）および監査ログ管理のための Python モジュール群です。  
主に J-Quants API と RSS ニュースを取り込み、DuckDB を中心としたローカル DB に保存、AI（OpenAI）でニュースセンチメント評価や市場レジーム判定を行うことを想定しています。

設計方針のハイライト:
- ルックアヘッドバイアスを避ける（内部で現在時刻を直接参照しない設計）
- ETL / データ品質チェック / 再実行しやすい冪等処理
- 外部 API 呼び出しはリトライ・レート制御を実装
- ニュース収集では SSRF 等のセキュリティ対策を考慮

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants から日足（OHLCV）・財務データ・上場銘柄・市場カレンダーの差分取得（ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT を想定した実装）
  - ETL の統合実行（run_daily_etl）と結果型（ETLResult）
- データ品質管理
  - 欠損・重複・スパイク・日付整合性チェック（quality モジュール）
- ニュース処理
  - RSS フィード取得（SSRF 対策、gzip 対応、サイズ制限）
  - ニュース前処理・記事ID正規化・銘柄との紐付け
  - OpenAI を利用した銘柄ごとのニュースセンチメントスコアリング（ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離 + マクロニュース（LLM）を合成して日次で 'bull'/'neutral'/'bear' を判定（ai.regime_detector.score_regime）
- 研究ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC 計算、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定 の追跡用テーブル群（audit.init_audit_schema / init_audit_db）

---

## 前提条件 / 依存関係

最低限の依存（主要パッケージ）:
- Python 3.10+（typing の Union 記法や型注釈に合わせた想定）
- duckdb
- openai
- defusedxml

インストール時に必要なパッケージは pyproject.toml / requirements.txt に依存しますが、上記を手動で用意しておくとよいです。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

3. インストール
   - 開発時（編集しながら使う）:
     ```
     pip install -e .
     ```
   - あるいは必要パッケージを個別にインストール:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（必須・任意を含む）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード（発注系を使う場合）
     - KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN (必須) — Slack 通知を使う場合
     - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
     - DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH (任意) — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL (任意) — DEBUG/INFO/…（デフォルト: INFO）
     - OPENAI_API_KEY (必須 for AI calls) — OpenAI API キー（score_news / score_regime で未指定時に参照）

   - .env の例（.env.example を参考に作成してください）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な例）

下記は Python REPL やスクリプトからの利用例です。DuckDB 接続を渡して各処理を実行します。

- DuckDB に接続する
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

- ニュースのセンチメントスコア付与（OpenAI 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を明示的に渡すか、OPENAI_API_KEY を環境変数でセット
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB を初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで監査ログ用テーブル群が作成されます
  ```

- ファクター計算例（研究用）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  ```

注意点:
- OpenAI 呼び出しを行う関数は API キーの指定が必須です（api_key 引数 または OPENAI_API_KEY 環境変数）。
- ETL / ニュース / レジーム処理はいずれもルックアヘッドバイアスに配慮して実装されています（target_date 未満のデータのみ参照等）。

---

## 主要モジュール構成（ディレクトリ構成）

以下はソースの主要ファイルと簡単な役割です（src/kabusys 以下）。

- kabusys/
  - __init__.py — パッケージ定義（version 等）
  - config.py — 環境変数 / 設定の読み込みロジック（.env 自動ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの NLP スコアリング（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - pipeline.py — ETL パイプラインのエントリおよび個別 ETL ジョブ
    - jquants_client.py — J-Quants API クライアント（取得＋保存用関数）
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - news_collector.py — RSS からのニュース収集・前処理
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログ（テーブル DDL / 初期化）
    - etl.py — ETLResult エクスポート
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリューの計算
    - feature_exploration.py — 将来リターン・IC・要約統計など
  - research 以外に strategy / execution / monitoring などの公開名が __all__ にある箇所もありますが、本リポジトリ提供のコードでは上記が主要です。

---

## 注意事項 / 運用上のヒント

- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を基準）から探されます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- OpenAI の呼び出しは課金が発生します。バッチサイズやリトライの設定はコード内で定義されていますが、運用時はキーの権限とコストに注意してください。
- J-Quants API はレート制限があります（実装は 120 req/min を想定）。大量一括取得時は RateLimiter の仕様に従ってください。
- DuckDB のバージョン差異（executemany の仕様等）に注意してください。コード内に互換性考慮のコメントがあります。
- ニュース収集時は RSS のサイズ制限、gzip、SSRF 対策を行っていますが、未知のソース追加時は十分に検証してください。

---

必要なら、README を元に具体的なコマンド例（systemd ジョブ、cron、Dockerfile、CI 用スクリプト）や API 使用例（kabuステーション発注フロー等）も別途作成します。どの部分を補足しましょうか？