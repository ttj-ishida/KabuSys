# KabuSys

日本株の自動売買・データ基盤用ライブラリ群。  
ETL（J-Quants からのデータ取得）→ データ品質チェック → 研究用ファクター計算 → AI によるニュースセンチメント評価 → 市場レジーム判定 → 監査ログ（取引トレーサビリティ）までを想定したモジュール群を提供します。

主に DuckDB をバックエンドとしたデータプラットフォームと、OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定機能を含みます。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - `.env` / `.env.local` を自動読み込み（プロジェクトルートは `.git` または `pyproject.toml` を起点に検出）
  - 必須環境変数のラッパー `kabusys.config.settings`
- データ取得・ETL（J-Quants API）
  - 日次株価（OHLCV）、財務データ、マーケットカレンダー等の差分取得（ページネーション対応、レート制御、リトライ）
  - DuckDB への冪等保存（ON CONFLICT で更新）
  - 日次 ETL パイプライン `kabusys.data.pipeline.run_daily_etl`
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェック（`kabusys.data.quality`）
  - QualityIssue 型で詳細を取得
- カレンダー管理
  - JPX マーケットカレンダーの取得・保存／営業日判定ユーティリティ（next_trading_day 等）
- ニュース収集
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去・raw_news への冪等保存ロジック（`kabusys.data.news_collector`）
- 研究（Research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等
- AI（OpenAI）連携
  - ニュースごとの銘柄センチメント算出（`kabusys.ai.news_nlp.score_news`）
  - ETF の MA 乖離とマクロニュースを合成した市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
  - OpenAI 呼び出しはリトライやフォールバックを備え、応答パース失敗時はフェイルセーフで継続
- 監査（Audit / トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル DDL と初期化ユーティリティ（`kabusys.data.audit`）
  - 監査 DB の初期化補助（`init_audit_db` / `init_audit_schema`）

---

## 動作要件（参考）

- Python 3.10+
  - コード内で型ヒントに `|`（PEP 604）を使用しているため 3.10 以上を想定しています。
- 主要依存ライブラリ（抜粋）
  - duckdb
  - openai (OpenAI の Python SDK)
  - defusedxml
- ネットワークアクセス:
  - J-Quants API（データ取得）
  - OpenAI API（ニュース評価）
  - RSS ソース（ニュース収集）

※ 実際のプロジェクトでは pyproject.toml / requirements.txt を参照して依存をインストールしてください。

---

## 環境変数（主なもの）

自動ロード順序: OS 環境変数 > .env.local > .env  
自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系を統合する場合）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot Token
- SLACK_CHANNEL_ID — Slack チャネル ID

オプション / デフォルトあり:
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードの無効化
- KABUSYS_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 関連機能で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等に使用する SQLite のパス（デフォルト: data/monitoring.db）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそれに従ってください。）

4. 環境変数を用意
   - プロジェクトルートに `.env` を作成（`.env.example` を用意している場合はそれを参考に）
   - 例（簡易）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

   - 自動ロードを使いたくない場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB 用ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要なユースケース例）

以下は Python REPL / スクリプトからの簡単な使い方例です。DuckDB 接続には `duckdb.connect()` を利用します。

- DuckDB 接続の作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 監査ログ用 DB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL を実行（J-Quants から差分取得して保存・品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出（OpenAI 必須）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロ記事の LLM スコアを合成）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentums = calc_momentum(conn, date(2026, 3, 20))
  ```

- データ品質チェックの実行:
  ```python
  from kabusys.data.quality import run_all_checks
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

---

## 自動 .env ロードについて

- パッケージ読み込み時、プロジェクトルート（`.git` または `pyproject.toml` のあるディレクトリ）を起点に `.env` → `.env.local` の順で読み込みます。
- 既に OS 環境変数に存在するキーは上書きされません（`.env.local` は上書きを許可しますが OS 環境変数は保護されます）。
- 無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル・モジュールの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄単位にまとめて OpenAI に送りセンチメントを生成。`score_news`
    - regime_detector.py — ETF 1321 の MA と macro ニュースの LLM スコアを合成して市場レジームを判定。`score_regime`
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存のユーティリティ）
    - pipeline.py — 日次 ETL パイプライン、個別 ETL ジョブ（run_daily_etl 等）
    - etl.py — ETL 型の再エクスポート（ETLResult）
    - news_collector.py — RSS 取得・前処理・raw_news 保存
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - stats.py — z-score 正規化など共通統計ユーティリティ
    - quality.py — データ品質チェック
    - audit.py — 監査ログ DDL・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

---

## 注意事項 / ベストプラクティス

- OpenAI API キーはセキュアに管理してください（.env やシークレットストア）。スクリプトにハードコーディングしないでください。
- ETL 実行や AI 呼び出しはレート制限やコストに注意して運用してください。
- DuckDB はローカルファイルに対するロック・パーミッションに注意。複数プロセスでの同時書き込みは設計に依存します。
- 本ライブラリの関数群は「ルックアヘッドバイアス防止」を意識して実装されています。バックテストで使用する場合、データの世代順や取得時刻に注意してください。
- 監査テーブルは削除しない前提です。schema initialization は慎重に行ってください（`init_audit_schema` の transactional オプションあり）。

---

必要に応じて README に追記します（例: CI / デプロイ手順、pyproject のセットアップ、より詳細な .env.example、運用上の監視手順など）。何を追加しましょうか？