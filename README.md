# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants / ETF / NEWS 等のデータを取り込み、品質チェック・ファクター計算・ニュースNLP（OpenAI）・市場レジーム判定・監査ログなど、バックテスト／運用に必要な機能群を提供します。

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務、JPXカレンダー等を差分取得・保存（DuckDB）
  - 差分取得・バックフィル・ページネーション・レート制御・トークン自動更新対応
- データ品質チェック
  - 欠損値、スパイク（急変）、重複、日付不整合等を検出
- ニュース収集 / 前処理
  - RSS フィード取得・URL 正規化・SSRF 対策・記事ID生成・前処理
- ニュース NLP（OpenAI）
  - 銘柄ごと・時間ウィンドウごとの記事をまとめて LLM に送信しセンチメント（ai_score）を生成
  - レートリミット・リトライ・レスポンス検証あり
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを組み合わせて日次で 'bull' / 'neutral' / 'bear' を判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン・IC（情報係数）・統計サマリ等
- 監査ログ（Audit）
  - signal → order_request → execution までトレースできる監査テーブル定義・初期化
- 設定管理
  - 環境変数 / `.env` からの自動ロード（プロジェクトルート検出）
  - `KABUSYS_ENV` による環境切替（development / paper_trading / live）

---

## 必要条件（推奨）

- Python 3.10 以上（型注釈に union 型表記（A | B）を使用）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ

（パッケージは pip でインストール可能。プロジェクトに requirements.txt があればそちらを参照してください。）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - Python のプロジェクトルート（`pyproject.toml` / `.git` があるディレクトリ）がパッケージの自動 .env ロードの基準になります。

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   # 開発用にパッケージを編集しながら使う場合:
   pip install -e .
   ```

4. 環境変数（必須 / 任意）
   - 必須（最低限、ETL や J-Quants 関係を使う場合）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token で使用）
     - KABU_API_PASSWORD: kabuステーション API を使う場合
   - OpenAI（ニュース NLP / レジーム判定 を使う場合）
     - OPENAI_API_KEY: OpenAI API キー（関数呼び出し時に引数で渡すことも可）
   - オプション
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, 監視閾値（CPU/MEM/DISK）など
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   推奨: プロジェクトルートに `.env` を作成して管理。自動で `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データベース初期化（例: 監査DB）
   ```python
   >>> from kabusys.data.audit import init_audit_db
   >>> conn = init_audit_db("data/audit.duckdb")
   >>> # conn を使って監査テーブルが作成されます
   ```

---

## 使い方（代表的なコード例）

以下はライブラリ関数の一例的な呼び出し方法です。対象は DuckDB 接続オブジェクト（duckdb.connect() の戻り値）を渡します。

- 日次 ETL の実行（株価・財務・カレンダーの差分取得 + 品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア（OpenAI を使用）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # 環境変数 OPENAI_API_KEY が設定されていれば api_key を省略可能
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", written)
  ```

- 市場レジーム判定（LLM + ETF MA200）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を直接渡すか環境変数 OPENAI_API_KEY を設定
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査スキーマ初期化（個別 DB を使う場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS 取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  url = DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(url, source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- OpenAI 呼び出しは API 利用料金が発生します。API キー・呼び出し回数に注意してください。
- ETL / 保存処理は DuckDB のテーブルスキーマを前提としています。初回利用時には適切にスキーマを用意してください（プロジェクトに schema 初期化スクリプトがある想定）。

---

## 設定の自動読み込みについて

- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に自動で `.env` と `.env.local` を読み込みます。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - OS 環境変数は保護され `.env` による上書きが行われません（ただし .env.local は上書き可）。
- 自動ロードを無効化:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## KABUSYS の主要モジュール・ディレクトリ構成

（実際のリポジトリは src/kabusys 配下に配置されています。以下は主要ファイルと簡単な説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env のパース・自動読み込み・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースの LLM センチメント評価（score_news）
    - regime_detector.py   — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダーの管理・営業日判定
    - etl.py                — ETL 結果クラス再エクスポート
    - pipeline.py           — 日次 ETL パイプライン（run_daily_etl 等）
    - stats.py              — z-score 正規化など統計ユーティリティ
    - quality.py            — データ品質チェック群
    - audit.py              — 監査ログテーブル定義と初期化
    - jquants_client.py     — J-Quants API クライアント（fetch/save 関数）
    - news_collector.py     — RSS 収集 / 前処理 / 保存ロジック
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py— 将来リターン・IC・統計サマリ・ランク関数

---

## 運用上の注意 / ベストプラクティス

- ルックアヘッドバイアスに注意
  - ライブラリの多くの関数は date 引数を明示的に受け取り、内部で datetime.today() を直接参照しない設計になっています。バックテストでは必ず適切な target_date を渡してください。
- OpenAI の呼び出しは失敗時にフォールバック（0.0）をする実装が多いですが、重要な判断に使う場合は呼び出し結果を監査ログや運用アラートで確認してください。
- DuckDB ファイルのパス（DUCKDB_PATH）は settings.duckdb_path から取得してください。運用環境での適切なバックアップ・ファイルパーミッションを推奨します。
- `.env` に秘密情報（API トークン）を保存する際は、リポジトリに含めないよう `.gitignore` に追加してください。

---

## サポート / 貢献

- バグ報告・パッチは Pull Request を歓迎します。設計方針やユニットテストを尊重して変更してください。
- 大きな API 変更や互換性破壊を伴う改変は事前に Issue で議論してください。

---

この README はコードベースの公開インターフェースと主要ワークフローを中心にまとめています。詳細な API ドキュメント（各関数の引数・戻り値・例外等）は該当モジュールの docstring を参照してください。