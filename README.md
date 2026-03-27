# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、研究（ファクター計算）、監査ログなどを含むモジュール群を提供します。

## 主要な目的
- J-Quants API を使った日次データ取得・ETL パイプライン
- ニュースを用いた銘柄単位の AI スコアリング（OpenAI）
- ETF とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算 / 特徴量探索（リサーチ用途）
- DuckDB ベースのデータ管理、監査ログスキーマ（発注→約定トレース）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 機能一覧（抜粋）

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得とバリデーション（`kabusys.config.settings`）

- データ取り込み / ETL
  - J-Quants クライアント（取得・ページネーション・保存）
  - 日次 ETL パイプライン（calendar / prices / financials の差分取得）
  - 市場カレンダーの更新ジョブ
  - RSS ニュース収集と前処理（SSRF対策・サイズ制限・トラッキング除去）

- データ品質
  - 欠損データ / スパイク / 重複 / 日付不整合の検出（`kabusys.data.quality`）
  - 品質チェックを集約する `run_all_checks`

- AI（OpenAI を使用）
  - ニュースセンチメント（銘柄ごとの ai_score）: `kabusys.ai.news_nlp.score_news`
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）: `kabusys.ai.regime_detector.score_regime`

- リサーチ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ

- 監査 / トレーサビリティ
  - signal_events / order_requests / executions の監査テーブル定義と初期化
  - 冪等性・ステータス管理を想定

---

## セットアップ手順

前提
- Python 3.10 以上（typing における X | Y 型注釈を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 開発用に setup.py / pyproject.toml があれば `pip install -e .` を推奨
   - 少なくとも下記パッケージが必要です:
     - duckdb
     - openai (OpenAI の公式 SDK)
     - defusedxml
   例:
   ```
   pip install -e .
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env の用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に自動で `.env` と `.env.local` を読み込みます（無効化可）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      — kabuステーション API パスワード
     - SLACK_BOT_TOKEN        — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       — Slack チャネル ID
     - OPENAI_API_KEY         — OpenAI API キー（AI 機能を使う場合）
   - 任意 / デフォルト:
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL              — ログレベル（DEBUG/INFO/...、デフォルト INFO）
     - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH            — 監視用 SQLite（デフォルト data/monitoring.db）
   - `.env.local` は `.env` を上書きします。

   環境変数参照例（Python）
   ```py
   from kabusys.config import settings
   print(settings.jquants_refresh_token)
   ```

5. 自動 .env ロードを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方（代表的な例）

- DuckDB 接続を作成して ETL を実行（Python REPL / スクリプト）
  ```py
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア（OpenAI 必須）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数を指定
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} tickers")
  ```

- 市場レジーム判定（OpenAI 必須）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB の初期化（監査用専用 DB を作る）
  ```py
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  ```

- リサーチ機能の利用例（モメンタム算出）
  ```py
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

注意:
- AI 関連機能（news_nlp, regime_detector）は OpenAI の利用が前提です。API キーは環境変数 OPENAI_API_KEY または関数引数で渡してください。
- ネットワーク / API のエラーは多くの箇所でリトライやフォールバック（例: スコア0.0）がありますが、ログで詳細を確認してください。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースセンチメント（OpenAI）
    - regime_detector.py              — 市場レジーム判定（ETF1321 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL インターフェース再エクスポート
    - calendar_management.py          — 市場カレンダー管理 / 営業日判定
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - quality.py                      — データ品質チェック
    - audit.py                        — 監査ログスキーマ初期化
    - news_collector.py               — RSS 収集 + 前処理
  - research/
    - __init__.py
    - factor_research.py              — Momentum/Value/Volatility 等
    - feature_exploration.py          — IC / forward returns / summary 等
  - ai/、data/、research/ などの下に更に細かなロジックやユーティリティが実装されています。

---

## 実装上の注意点 / 設計方針（概要）
- ルックアヘッドバイアス対策:
  - target_date を明示する設計で、内部で date.today() を不用意に参照しないようにしています。
  - 取得ウィンドウは排他的条件等で将来データを使わない工夫あり。

- 冪等性:
  - DuckDB への保存は ON CONFLICT（更新）で実装し、再実行に耐えるようになっています。

- フェイルセーフ:
  - AI API の失敗や JSON パース失敗時はスコアを 0.0 にフォールバックするなど、上位で例外を起こさない設計の箇所が多くあります（ただし ETL の主要部分は例外を上位へ伝播する場合あり）。

- セキュリティ / 頑健性:
  - RSS の収集では SSRF 対策、受信サイズ制限、defusedxml を使用して XML 攻撃対策を行っています。
  - J-Quants クライアントはレートリミットとリトライを実装しています。

---

## よくある質問 / トラブルシューティング

- .env がロードされない:
  - プロジェクトルートが .git または pyproject.toml で検出されます。テスト環境などで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI の呼び出しが失敗する:
  - OPENAI_API_KEY が正しく設定されているか確認してください。API のレートやモデル名（gpt-4o-mini）に注意してください。

- DuckDB のファイルパスを変更したい:
  - 環境変数 DUCKDB_PATH を設定するか、duckdb.connect() に直接パス文字列を渡してください。

---

README は簡潔にまとめています。より詳細な API 仕様や運用手順（ジョブスケジューリング、監視、Slack 通知など）は別ドキュメントに分けて管理することを推奨します。必要であれば各モジュールの使用例や Schema（テーブル定義）を追加で作成します。