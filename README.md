# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買（戦略・監査・実行補助）を想定したライブラリ群です。J-Quants / RSS / OpenAI 等の外部サービスと連携し、データ収集（ETL）、品質チェック、ニュース NLP による銘柄スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（発注トレーサビリティ）などの機能を提供します。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗時に継続）」です。

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants API からの株価（日足）・財務データ・マーケットカレンダー取得（ページネーション・レートリミット対応）
  - 差分更新（最終取得日ベース）、バックフィル、ETL結果を表す ETLResult
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース処理
  - RSS フィード収集（SSRF 防止、URL 正規化、トラッキングパラメータ除去）
  - raw_news / news_symbols 連携、冪等保存
- AI（LLM）連携
  - ニュースを銘柄別にまとめて OpenAI（gpt-4o-mini 等）に投げ、銘柄ごとのセンチメント（ai_scores）を計算（バッチ・リトライ・レスポンス検証）
  - マクロニュースと ETF（1321）の 200 日 MA 乖離を組み合わせて市場レジーム（bull/neutral/bear）を日次判定
- リサーチ／ファクター計算
  - Momentum / Value / Volatility / Liquidity 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - シグナル・発注要求・約定を追跡する監査用テーブル群／DDL 初期化ユーティリティ
  - DuckDB を利用した監査 DB 初期化補助
- その他
  - market calendar（営業日判定、next/prev 営業日取得、夜間更新ジョブ）
  - 環境設定管理（.env 自動読み込み、必須環境変数検査）

---

## 必要条件 / 前提

- Python 3.10 以降（コードに union 型（A | B）を使用）
- 必要となる主要依存（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API、OpenAI、RSS ソース 等）

パッケージの実際の install 要件はプロジェクトの packaging（pyproject.toml / requirements.txt）に依存します。ここでは最低限の例を示します。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements.txt があれば
   # pip install -r requirements.txt
   ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` および（必要に応じて）`.env.local` を配置すると自動的に読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

   主要な環境変数（少なくとも以下を設定する必要がある箇所があります）:

   - J-Quants 関連
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - OpenAI
     - OPENAI_API_KEY — OpenAI API キー（score_news / regime 判定で使用）
   - kabu ステーション（発注・接続）
     - KABU_API_PASSWORD — kabu API パスワード（使用する場合）
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
   - LINE 通知（任意）
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
   - DB / ファイルパス（デフォルトあり）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PID_FILE_PATH (default: data/execution.pid)
     - KILL_FLAG_PATH (default: data/kill.flag)
   - 環境/ログ
     - KABUSYS_ENV ∈ {development, paper_trading, live} (default: development)
     - LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL} (default: INFO)

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL から利用する例です。DuckDB 接続は `duckdb.connect(path)` を利用します。

- ETL（日次パイプライン）を実行する例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとの ai_scores を生成）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査テーブルを作成）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- RSS フィード取得（ニュース収集の個別ユーティリティ）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

注意:
- OpenAI 連携を行う関数（score_news, score_regime）は API 呼び出しに失敗した場合でも安全に継続する設計ですが、正しく動かすには OPENAI_API_KEY が必要です。
- J-Quants との連携は JQUANTS_REFRESH_TOKEN が必須です。

---

## 自動 .env 読み込みの挙動

- プロジェクトルート（このパッケージの __file__ から上位ディレクトリで `.git` または `pyproject.toml` が見つかる場所）を自動検出します。
- 読み込み優先順位:
  1. OS 環境変数（既存のプロセス環境）
  2. .env.local（存在すれば OS 環境変数を上書き。ただし OS の既存キーは保護される）
  3. .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env パーサはシェル形式の export 対応やコメント、引用符のエスケープなどに対応しています。

---

## 主要モジュールとディレクトリ構成

（プロジェクトルート: src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数設定管理（Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースを LLM でスコアリングして ai_scores に書込
    - regime_detector.py  — マクロニュース＋ETF MA200 乖離で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
    - pipeline.py         — ETL パイプラインと run_daily_etl、個別 ETL ジョブ
    - etl.py              — ETLResult の再エクスポート
    - news_collector.py   — RSS 収集・正規化・SSRF 対策
    - quality.py          — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py            — z-score 正規化ユーティリティ
    - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py            — 監査ログ DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー、ランク関数
  - ai/、data/、research/ はそれぞれの高レベル API を公開（__all__ 等で制御）

---

## 開発・貢献

- コーディング規約やテスト、CI 設定がある場合はプロジェクトルートを参照してください（README は最低限の利用ガイドを提供します）。
- 外部 API キーや認証情報は必ずローカルの .env（git 管理外）で管理してください。
- ネットワーク呼び出しを伴う関数群はモック可能な設計（内部の _call_openai_api / _urlopen 等を patch）になっているため単体テストが書きやすくなっています。

---

## 注意事項

- 本ライブラリは発注（実際の売買）を含む実運用システムの一部を想定した設計が含まれます。実運用前には十分なテスト・監査・リスク管理を行ってください。
- OpenAI や J-Quants、証券会社 API を利用する場合は各サービスの利用規約に従ってください。
- デフォルトの挙動や閾値（スパイク閾値、ニュースウィンドウ等）はコード内定数で管理されています。必要に応じて引数や環境変数で調整してください。

---

もし README に追加したい使用例（CLI スクリプト、Docker、CI、具体的な .env.example など）があれば、教えてください。必要に応じて追記します。