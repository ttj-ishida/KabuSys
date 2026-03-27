# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
DuckDB を用いたデータパイプライン、J-Quants API 経由のデータ取得、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（注文→約定のトレーサビリティ）などのユーティリティを提供します。

主な想定用途:
- データの差分 ETL（株価・財務・市場カレンダー）
- ニュースを用いた銘柄センチメントスコア生成（LLM を利用）
- ETF 指標とマクロニュースを組み合わせた市場レジーム判定
- 研究（ファクター計算 / 特徴量探索）
- 監査ログ（シグナル→発注→約定の履歴保持）

---

## 機能一覧

- 環境変数 / .env の自動ロードと設定取得（kabusys.config）
  - 自動ロードを無効化するフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- データ ETL（kabusys.data.pipeline）
  - J-Quants API から差分取得（株価 / 財務 / 市場カレンダー）
  - 保存（DuckDB）・品質チェック（欠損/スパイク/重複/日付整合性）
  - 日次パイプライン: `run_daily_etl`
- J-Quants API クライアント（kabusys.data.jquants_client）
  - レートリミット制御、リトライ、トークン自動更新、ページネーション対応
  - save_* 系で DuckDB への冪等保存を実装
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理・冪等保存のためのユーティリティ
  - SSRF/サイズ制限などの安全対策あり
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント生成
  - バッチ・リトライ・レスポンス検証を備えた実装
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを組み合わせて日次レジームを生成
- 研究モジュール（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC、統計サマリー、z-score 正規化
- 監査ログ（kabusys.data.audit）
  - シグナル / 発注要求 / 約定を追跡するテーブルと初期化ユーティリティ
  - `init_audit_db` / `init_audit_schema`

---

## 前提 / 必須環境

- Python 3.10+（型注釈に union 型などを利用）
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリのみで動作する箇所も多いですが、上記は最低限必要です

（プロジェクトに pyproject.toml / requirements.txt がある想定でインストールしてください）

---

## セットアップ手順（例）

1. リポジトリをチェックアウト
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - pyproject / requirements がある場合はそれを利用してください。例:
   ```bash
   pip install -U pip
   pip install duckdb openai defusedxml
   # pip install -e .  # プロジェクトがパッケージ化されている場合
   ```

4. 環境変数を設定
   - .env ファイル（プロジェクトルート）を作成することで自動読み込みされます（既存の OS 環境変数を上書きしない設定）。
   - 重要な環境変数（最小例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector 実行時に未指定なら参照）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（該当機能で使用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に利用（該当機能で使用）
     - DUCKDB_PATH: デフォルト: data/kabusys.duckdb
     - SQLITE_PATH: デフォルト: data/monitoring.db
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - 自動 .env ロードを無効化するには:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（例）

以下は代表的なユースケースのサンプルコード例です。実行は Python REPL / スクリプトから。

- DuckDB 接続を用意する
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定（None で今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（OpenAI API キーを環境変数に設定）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key 引数を渡すことも可能
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {written} codes")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit_kabusys.duckdb")
  # audit_conn は監査スキーマが初期化済みの DuckDB 接続
  ```

- RSS フィード取得（ニュース収集の一部）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- score_news / score_regime は OpenAI API を呼ぶため API キー（環境変数 `OPENAI_API_KEY` または関数引数）を必ず与えてください。未設定だと ValueError を送出します。
- run_daily_etl は J-Quants の認証に J-Quants refresh token（環境変数 JQUANTS_REFRESH_TOKEN）を使用します。

---

## 設定（環境変数の要点）

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
  - 既存の OS 環境変数は保護されます（上書きされません）。`.env.local` は override フラグで上書き可能ですが、OS 環境を保護する仕組みがあります。
  - 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- 主要な必須変数（実行する機能に応じて必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（ETL）
  - OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知（必要時）
  - KABU_API_PASSWORD — kabu ステーション API（実行環境がある場合）
  - DUCKDB_PATH / SQLITE_PATH — デフォルトデータベースのパス
  - KABUSYS_ENV — 実行モード（development / paper_trading / live）
  - LOG_LEVEL — ログレベル（DEBUG / INFO / ...）

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py
  - パッケージバージョン等
- config.py
  - 環境変数・.env 自動ロード・settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py : ニュースの LLM センチメント処理（銘柄別スコア・バッチ・検証）
  - regime_detector.py : ETF MA とマクロニュースを組み合わせた市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py : マーケットカレンダーの管理・営業日判定
  - etl.py : ETL インターフェース再エクスポート
  - pipeline.py : 日次 ETL 実装（差分取得・保存・品質チェック等）
  - stats.py : 共通統計ユーティリティ（z-score 正規化等）
  - quality.py : データ品質チェックモジュール
  - audit.py : 監査ログ（シグナル / 発注 / 約定）のスキーマ定義と初期化
  - jquants_client.py : J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py : RSS 収集・前処理・安全対策
- research/
  - __init__.py
  - factor_research.py : モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py : 将来リターン計算・IC・統計サマリー等
- その他トップレベルモジュール
  - data, research などが外部から利用される入口となる

（上記は抜粋・要約です。各モジュールに詳細な docstring があり設計方針や注意点が記載されています）

---

## 運用上の注意 / ベストプラクティス

- Look-ahead bias の防止:
  - モジュール設計上、内部処理は可能な限り `date`/`datetime` を引数で受け取り、`date.today()` を直接参照しないように設計されています。バックテスト等では明示的に日付を渡して再現性を確保してください。
- OpenAI 呼び出し:
  - レスポンス検証やリトライ・フォールバック（失敗時は neutral スコアや 0.0 を利用）を行いますが、API コストとレート制限に注意してください。
- J-Quants API:
  - レート制限（120 req/min）を遵守する設計ですが、運用時にはトークン管理（JQUANTS_REFRESH_TOKEN）を安全に保管してください。
- データベース:
  - デフォルトの DuckDB ファイルは `data/kabusys.duckdb`。本番環境ではバックアップ・ファイル配置に注意してください。
- 監査ログ:
  - 監査テーブルは削除しない前提で設計されています。監査 DB の管理（アーカイブ / サイズ管理）を運用で検討してください。

---

## 開発者向けメモ

- 自動 .env 読み込みはパッケージ配布後でも CWD に依存せず機能するように `__file__` を起点にプロジェクトルートを探索します。
- テスト時に自動 .env 読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- OpenAI 呼び出し部などはテスト容易性を考慮して内部関数（例: `_call_openai_api`）をパッチして差し替えられるように設計されています。

---

必要であれば、README に以下の追加情報も用意できます:
- 具体的な requirements.txt / pyproject.toml のサンプル
- CI / デプロイ手順（ETL の定期実行ジョブ例）
- よくあるトラブルシューティング（OpenAI の JSON parse error 回避、DuckDB のバージョン注意点 など）

どの追加情報が欲しいか教えてください。