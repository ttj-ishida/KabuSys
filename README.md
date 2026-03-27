# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ

---

## プロジェクト概要

KabuSys は日本株のデータ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、リサーチ用ファクター計算、そして取引監査ログ管理までを包含する、バックテスト／自動売買プラットフォーム向けの共用ライブラリ群です。  
DuckDB をデータストアとして利用し、OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析や市場レジーム判定などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを排除する（内部で datetime.today()/date.today() を不要にする設計）
- DuckDB を中心とした SQL + Python の実装
- API 呼び出しにはリトライ / レート制御 / フェイルセーフを備える
- ETL / 品質チェックは部分失敗を許容して問題を集約する

---

## 機能一覧

- 環境設定管理
  - .env の自動読み込み（プロジェクトルート検出）／無効化フラグ対応
- データ取得（J-Quants）・保存
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPXカレンダー取得
  - ページネーション・認証リフレッシュ・レート制御・リトライ対応
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル対応
  - ETL 結果を ETLResult で集約
- データ品質チェック
  - 欠損（OHLC）・スパイク（前日比）・重複・日付不整合チェック（market_calendar 照合）
- ニュース収集
  - RSS フィード収集（SSRF 対策・gzip 対応・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存設計
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント集約（gpt-4o-mini + JSON Mode）
  - チャンクバッチ送信、レスポンス検証、スコアクリップ
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離 と マクロニュースセンチメントを合成して daily レジームを判定
  - OpenAI 呼び出しに対するリトライ・フォールバックあり
- リサーチ用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - init_audit_schema / init_audit_db による冪等初期化

---

## 必要条件（主なパッケージ）

- Python 3.10+
- duckdb
- openai
- defusedxml

（実際の requirements.txt はプロジェクトに合わせてください）

---

## セットアップ手順

1. リポジトリを取得（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.git または pyproject.toml のある親ディレクトリをプロジェクトルートと見なします）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（代表）：
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack チャネル ID
   - OPENAI_API_KEY — OpenAI API キー（score_news / regime などで利用）

   任意：
   - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

5. データベース初期化（監査用 DB の例）
   Python REPL やスクリプト内で：
   ```python
   import kabusys
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")
   # これで監査テーブルが作成されます
   ```

---

## 使い方（主要ユースケース）

- DuckDB 接続作成（共通）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメント計算（1 日分）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  num_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {num_written}")
  ```

- 市場レジーム判定（1 日分）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存接続へ追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算（研究目的）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentums = calc_momentum(conn, target_date=date(2026,3,20))
  values = calc_value(conn, target_date=date(2026,3,20))
  vols = calc_volatility(conn, target_date=date(2026,3,20))
  ```

注意点：
- OpenAI を使う関数（score_news / score_regime 等）は引数 `api_key` を受け取ります。未指定時は環境変数 `OPENAI_API_KEY` を参照します。
- ETL や news scoring は API 呼び出し失敗時にフェイルセーフとしてスキップやデフォルト値を使う設計です。ログを参照してください。
- 自動 .env 読み込みはプロジェクトルート検出に基づきます。テストなどで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py
  - 環境変数・設定（settings）
- ai/
  - __init__.py
  - news_nlp.py         — ニュースの NLP スコアリング（OpenAI 呼び出し、チャンク処理）
  - regime_detector.py  — 市場レジーム判定（ETF 1321 MA + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（fetch / save / auth / rate limit）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETL 公開インターフェース（ETLResult 再エクスポート）
  - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
  - news_collector.py      — RSS 収集（SSRF 対策、正規化）
  - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py               — 汎用統計（Zスコア正規化）
  - audit.py               — 監査ログ（監査テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py     — モメンタム／バリュー／ボラティリティ計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等

その他:
- data/ (デフォルトのデータ格納先; settings.duckdb_path の親ディレクトリ)
- .env.example（プロジェクトにあれば参考に .env を作成）

---

## ロギング・環境

- 環境変数 `LOG_LEVEL` でログレベルを制御（INFO／DEBUG 等）。settings.log_level を通じて取得します。
- `KABUSYS_ENV` により実行モードを切り替え（development / paper_trading / live）。settings.is_live / is_paper / is_dev が利用可能です。

---

## 開発・テスト時のヒント

- OpenAI 呼び出し箇所は内部で `_call_openai_api` のような関数に切り出されているため、unittest.mock.patch で簡単にモック化できます。
- J-Quants クライアントはトークンの自動リフレッシュやレート制御を備えています。テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い .env の自動読み込みを止めて個別に環境を設定してください。

---

README は以上です。必要であれば、利用シナリオ別の具体的なサンプルスクリプトや .env.example のテンプレートも作成します。どの内容を追加希望か教えてください。