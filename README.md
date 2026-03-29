# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（発注→約定のトレーサビリティ）などの機能を提供します。

## 特徴（概要）
- J-Quants API 経由で株価・財務・カレンダー等を差分取得し DuckDB に保存する ETL パイプライン
- raw_news の RSS 収集と OpenAI（gpt-4o-mini）によるニュースセンチメント解析（銘柄ごと）
- ETF（1321）200日移動平均乖離とマクロニュースを統合した市場レジーム判定（bull / neutral / bear）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）のためのスキーマ初期化ユーティリティ
- DuckDB を中心とした軽量で再現性あるデータ基盤設計

---

## 機能一覧（主なモジュール）
- `kabusys.config`
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）と設定取得（`settings`）
- `kabusys.data`
  - `jquants_client`：J-Quants API クライアント（取得/保存関数、認証、レートリミット、リトライ）
  - `pipeline` / `etl`：差分 ETL（市場カレンダー・株価・財務）の実行と `ETLResult` 集約
  - `news_collector`：RSS 収集と raw_news 保存（SSRF・サイズ制限・正規化対応）
  - `quality`：データ品質チェック（欠損／スパイク／重複／日付整合性）
  - `calendar_management`：営業日判定・next/prev_trading_day・カレンダー更新ジョブ
  - `audit`：監査ログ用スキーマの生成・初期化（監査テーブル・インデックス）
  - `stats`：共通統計ユーティリティ（Zスコア正規化等）
- `kabusys.ai`
  - `news_nlp.score_news`：銘柄ごとのニュースセンチメントを算出し `ai_scores` に書き込み
  - `regime_detector.score_regime`：ETF 1321 の MA 乖離 + マクロセンチメントによる市場レジーム判定
- `kabusys.research`
  - ファクター計算（momentum / value / volatility）や特徴量探索（forward returns, IC, summary）

---

## セットアップ手順

1. リポジトリをクローン / ワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要な依存パッケージをインストール  
   （プロジェクトに requirements.txt/poetry 設定がない場合は、少なくとも下記をインストールしてください）
   ```
   pip install duckdb openai defusedxml
   ```
   実運用では logger 等の追加パッケージや HTTP 関連ユーティリティが必要になる場合があります。

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数 / .env の準備  
   プロジェクトルートに `.env`（および `.env.local`）を置くと自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。  
   必須の環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知に使用（必須）
   - SLACK_CHANNEL_ID — Slack チャンネルID（必須）
   - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必須）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — SQLite（監視データ等）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）

   .env の書式は一般的な KEY=VALUE 形式に従います。詳細は `kabusys.config` を参照。

---

## 使い方（簡単な例）

以下は主要な操作の例です。実際のワークフローではエラーハンドリングやロギングを適切に追加してください。

- DuckDB 接続の作成（監査 DB 初期化）
  ```python
  from kabusys.config import settings
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db(settings.duckdb_path)  # ファイルがなければ作成してスキーマ初期化
  ```

- 日次 ETL を実行（株価・財務・カレンダーの差分取得）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアの生成（ai_scores 書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} symbols")
  ```
  ※ api_key を省略すると環境変数 `OPENAI_API_KEY` が使用されます。

- 市場レジーム判定の実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使用
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  ```

- データ品質チェックを実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

---

## 自動環境読み込みについて
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml のある場所）を起点に `.env` / `.env.local` を自動読み込みします。
- 読み込み順: OS 環境 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須変数が未設定の場合、`kabusys.config.Settings` のプロパティ呼び出しで `ValueError` が発生します。

---

## ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコア
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプラインと run_daily_etl
    - etl.py                 — ETL public re-exports (ETLResult)
    - news_collector.py      — RSS 収集
    - calendar_management.py — 市場カレンダー管理機能
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     — momentum/value/volatility 計算
    - feature_exploration.py — forward returns / IC / summary / rank

---

## 運用上の注意
- OpenAI API を使う機能（news_nlp, regime_detector）は API コストとレイテンシを伴います。テストではモック可能な設計（内部の _call_openai_api をパッチ）になっています。
- J-Quants API のレート制限（120 req/min）や 401 リフレッシュ処理、リトライロジックを組み込んでいますが、運用時は id_token の管理やバックオフポリシーを確認してください。
- DuckDB の executemany に関するバージョン依存の挙動（空パラメータ不可など）に注意が必要です（既にコード側でガード済み）。
- audit スキーマは一度作成したら削除しない前提で使う想定です。init_audit_schema は冪等で実行可能です。

---

## 開発・貢献
- コントリビュートやバグ報告は Pull Request / Issue を作成してください。
- ユニットテストでは外部 API 呼び出しをモックすること（OpenAI、J-Quants、ネットワーク I/O）を強く推奨します。
- .env の実運用値をリポジトリに含めないでください（機密情報の管理に注意）。

---

README に記載されていない細かい実装・仕様はソースコードの docstring に詳細が記載されています。まずは `kabusys.config` で環境（.env）を整え、`run_daily_etl` の実行から始めるのが推奨ワークフローです。