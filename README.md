# KabuSys

日本株向けの自動売買・データ基盤ライブラリ KabuSys の README。  
このリポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、リサーチ（ファクター計算）、監査ログ等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の運用システム向けに設計された Python ライブラリ群です。主な目的は以下です。

- J-Quants API からの差分データ取得（株価・財務・カレンダー）
- DuckDB を用いたデータ保存と品質チェック
- RSS ベースのニュース収集と OpenAI を用いた記事・銘柄ごとの NLP スコアリング
- マーケットレジーム判定（ETF + マクロニュースの合成）
- リサーチ用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 発注・約定までを追跡する監査ログスキーマ（冪等・トレーサビリティ対応）

設計上の特徴：
- ルックアヘッドバイアスを避ける（内部実装で date.today() を直接参照しない等）
- 冪等性を重視（DuckDB への保存は ON CONFLICT DO UPDATE / DO NOTHING）
- API 呼び出しに対するリトライ／レート制御／フォールバックを備える

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、トークン管理、レート制御）
  - 市場カレンダー管理（営業日判定・next/prev_trading_day）
  - ニュース収集（RSS -> raw_news、SSRF 対策、正規化）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ初期化（監査テーブル / インデックス定義、init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - ニュース NLP（score_news: OpenAI で銘柄ごとにセンチメント算出）
  - レジーム判定（score_regime: ETF 200MA とマクロニュースを合成）
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config
  - 環境設定読み込み（.env 自動読み込み機能、必須環境変数チェック）

---

## 要件（依存パッケージ）

最低限必要な Python パッケージ（抜粋）：
- Python 3.9+（型注釈で | を使用しているため 3.10 推奨）
- duckdb
- openai (OpenAI Python SDK v1 互換)
- defusedxml

実行環境により追加の標準ライブラリ（urllib, json, datetime など）を使用します。

---

## セットアップ手順

1. リポジトリをクローンします。
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）。
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存関係をインストール（プロジェクトに requirements.txt / pyproject.toml がある想定）。
   ```
   pip install -e ".[dev]"   # パッケージ化されている場合の例
   # または最低限:
   pip install duckdb openai defusedxml
   ```

4. 環境変数を用意する
   - プロジェクトルートに `.env` （と任意で `.env.local`）を置くと、モジュール読み込み時に自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（必須 / 任意）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token（ETL で必要）
   - KABU_API_PASSWORD (必須) — kabu API パスワード（実行環境により使用）
   - OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー（score_news / score_regime）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意、通知用）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主な利用例）

以下は Python から直接モジュールを呼び出す例です。各関数は DuckDB 接続を受け取るため、スクリプトや ETL ジョブから容易に利用できます。

- DuckDB 接続の作成（ファイル DB を使用する例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（カレンダー・株価・財務・品質チェックを順次実行）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作成してテーブルを初期化）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/monitoring_audit.duckdb")
  ```

- リサーチ用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- score_news / score_regime は OpenAI の呼び出しを行うため、API キーが必要です。API 呼び出し失敗時のフェイルセーフが組まれており、例外発生時に 0 を返す・スキップする挙動が設計されています（ログで警告が出ます）。
- ETL は部分失敗に強く、個別ステップが失敗しても他が続行されます。結果は ETLResult オブジェクトで確認できます。

---

## 環境変数の自動読み込み挙動

- config.Settings はモジュール読み込み時にプロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` の順で自動読み込みします。
- OS 環境変数 > `.env.local` > `.env` の優先度です。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須変数が参照された場合は、未設定だと ValueError が発生します（例: JQUANTS_REFRESH_TOKEN）。

---

## ディレクトリ構成

（主要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング
    - regime_detector.py            — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API client (fetch/save)
    - pipeline.py                   — ETL パイプライン（run_daily_etl など）
    - etl.py                        — ETL 公開インターフェース (ETLResult)
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py             — RSS ニュース収集
    - quality.py                    — データ品質チェック
    - stats.py                      — 汎用統計ユーティリティ
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py        — forward returns / IC / summary / rank

---

## 実運用上の注意

- API レート制限やコストに注意して OpenAI / J-Quants の呼び出しを行ってください。ライブラリはレート制御・リトライを組み込んでいますが、設定に応じた運用が必要です。
- DuckDB のスキーマやテーブルが期待どおりに存在することを事前に確認してください。ETL は既存テーブルを前提とする箇所があります。
- セキュリティ：news_collector は SSRF 対策や XML パースの安全化（defusedxml）を行っていますが、受信する RSS のソースは信頼できるものに限定することを推奨します。
- 本ライブラリ内の多くの関数は「ルックアヘッドバイアス」を避ける設計がなされていますが、バックテストやプロダクションでの利用時にはデータの取得時刻や保存時刻（fetched_at）に注意してください。

---

## 付記 / コントリビュート

- ドキュメントや型注釈、テストを追加することで品質向上に貢献できます。
- バグ報告・機能要望は issue を投げてください。

---

以上。必要があれば README にサンプル .env.example、CI / テスト実行方法、詳細なスキーマ定義（DDL）を追記します。どの項目を詳しく追加したいか教えてください。