# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ群）。  
データ取得・ETL、ニュースNLP（LLMを使ったセンチメント）、市場レジーム判定、研究用ファクター計算、監査ログ・発注トラッキング等を含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない実装）
- DuckDB を中心としたローカル DB ベースの ETL/分析
- OpenAI（gpt-4o-mini など）を用いたニュース解析（JSON Mode）
- J-Quants API との差分ETL、レート制御、トークン自動リフレッシュ
- 冪等性・トランザクション扱いに配慮した保存処理

---

## 機能一覧

- 環境設定管理
  - .env の自動ロード（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須環境変数取得時の検証（未設定時は ValueError）
- データ取得 / ETL
  - J-Quants API から株価・財務・上場銘柄情報・マーケットカレンダーを差分取得
  - run_daily_etl で日次ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS 取得・前処理・raw_news への保存（SSRF / XML Bomb 対策）
  - OpenAI を使った銘柄別ニュースセンチメント集計（score_news）
  - マクロニュースとETF MA乖離を組み合わせた市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー系ファクター計算
  - 将来リターン計算、IC（スピアマン）算出、ランク関数、Zスコア正規化
- 監査ログ（監査テーブル・初期化）
  - signal_events / order_requests / executions のスキーマ定義・初期化（init_audit_schema / init_audit_db）
  - 発注フローのトレーサビリティを保証するスキーマ

---

## 必要条件 / 依存関係

- Python 3.10+
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API、OpenAI、RSSソース 等）

（実際のインストールは下記セットアップ参照）

---

## 環境変数（代表）

以下は本プロジェクトで参照される主な環境変数の一覧と用途（すべて必須ではありませんが、一部機能は必須）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL に必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注関連）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・プロセスマネジメント
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env 読み込みの挙動：
- プロジェクトルート（.git または pyproject.toml を基準）を検出し、優先順位は OS 環境 > .env.local > .env です。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意）
   - Python venv の例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```

3. 必要パッケージをインストール
   - 例: pip を使う場合
     ```
     pip install -U pip
     pip install duckdb openai defusedxml
     # またはパッケージ化されているなら:
     pip install -e .
     ```

4. .env を作成（プロジェクトルート）
   例（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注意: リポジトリには .env.example を用意することを推奨します（本コードベースでは README 参照）。

5. DuckDB を初期化（監査DB を使う場合）
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/kabusys_audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（代表例）

- 日次 ETL を実行する（DuckDB 接続が必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントをスコア化（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定を実行（ETF 1321 とマクロニュースを組合せ）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- RSS フィードを取得する（ニュースコレクタの低レイヤ）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"])
  ```

- 監査スキーマを既存接続に追加
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

---

## ディレクトリ構成（該当コードベースの抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュースセンチメント解析（OpenAI）
    - regime_detector.py  # 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py  # マーケットカレンダー管理（営業日判定など）
    - etl.py                  # ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py             # ETL パイプライン本体（run_daily_etl 等）
    - stats.py                # 統計ユーティリティ（Zスコア）
    - quality.py              # 品質チェック（欠損/スパイク/重複/日付整合性）
    - audit.py                # 監査テーブル定義・初期化
    - jquants_client.py       # J-Quants API クライアント（取得・保存・レート制御）
    - news_collector.py       # RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py      # Momentum/Value/Volatility 計算
    - feature_exploration.py  # 将来リターン / IC / 統計サマリー 等
  - research/... (その他ユーティリティ)
  - (その他 strategy/execution/monitoring モジュールは __all__ に含める設計)

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取る設計が多く、直接 I/O や外部発注を行う機能は分離されています。

---

## 注意点 / トラブルシューティング

- OpenAI API 呼び出しはコストとレート制限に注意してください。news_nlp と regime_detector では再試行 / バックオフロジックを備えていますが、使用頻度に応じて料金が発生します。
- J-Quants API のレート上限（120 req/min）に合わせた内部レートリミッタを実装しています。認証トークンの自動リフレッシュ機能があり、401 受信時にリフレッシュを試みます。
- 環境変数の未設定は Settings のプロパティで ValueError を発生させます（必須項目をチェックしてください）。
- DuckDB に対する executemany の空リストなど、バージョン依存の注意点がコード内にあります（DuckDB 0.10 への互換性考慮）。
- news_collector は SSRF・XML Bomb 対策（ホスト検査、defusedxml、受信サイズ制限）を組み込んでいますが、運用時の安全ポリシーも併せてご検討ください。

---

## 貢献 / 開発

- コードスタイル、テスト、CI の整備を推奨します。
- 単体テストは外部 API 呼び出しをモックする設計になっています（内部で _call_openai_api などを差し替え可能）。
- 新規機能はモジュール分割（data / ai / research / execution / monitoring / config）に沿って実装してください。

---

必要に応じて README に追記・サンプルスクリプトや .env.example を追加します。追加で記載したい使用例や CI / デプロイ手順があれば教えてください。