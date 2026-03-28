# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、リサーチ用のファクター計算、監査ログ（約定トレース）、マーケットカレンダー管理など、売買システムの基盤機能をモジュール化して提供します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（Settings クラス）
- データ取得・ETL（J-Quants）
  - 日次株価（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーの差分取得
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT）
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存
  - SSRF / 圧縮バッファ / トラッキングパラメータ除去 等の安全対策
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを統合して LLM によるセンチメント評価（gpt-4o-mini を想定）
  - JSON Mode を使ったバリデーション、バッチ処理、リトライ処理
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次で 'bull/neutral/bear' を判定
- リサーチ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損・重複・スパイク（急騰/急落）・日付不整合の検出
- 監査ログ（トレーサビリティ）
  - signal → order_request → executions の階層で監査用テーブルを作成、初期化ユーティリティあり

---

## 要件

- Python 3.10+
- 必要パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ: sqlite3 等は別途不要）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

※ 実行環境に合わせて仮想環境の利用を推奨します。

---

## セットアップ手順

1. リポジトリをクローン／展開
   - 例: git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - 主要パッケージ例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（Settings が参照するもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード
     - SLACK_BOT_TOKEN — Slack ボットトークン（通知用）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルト有り:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト INFO）
     - KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — SQLite パス（デフォルト data/monitoring.db）
     - OPENAI_API_KEY — OpenAI API キー（score_news/score_regime の引数未指定時に参照）
   - .env の例 (.env.example を参考に作成してください):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DB/ディレクトリ準備
   - DuckDB や出力ディレクトリ（例 data/）を作成しておくと便利です。
   - 監査DBを初期化するユーティリティも用意されています（下記参照）。

---

## 使い方（主要なAPI/コマンド例）

以下は Python スクリプトや REPL から利用する例です。

- DuckDB 接続の確立例:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（market calendar / prices / financials を差分取得）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア生成（OpenAI 必須）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- リサーチ関数（例: モメンタム・ボラティリティ・バリュー）:
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- 監査ログ（監査スキーマ初期化）:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- RSS フィード取得（ニュース収集ユーティリティの一部）:
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  ```

注意点:
- OpenAI 呼び出しを行う機能（score_news / score_regime）を使う場合は OPENAI_API_KEY を環境変数に設定するか、関数引数 api_key を指定してください。
- J-Quants への API 呼び出しは認証トークンを要求します（JQUANTS_REFRESH_TOKEN を .env に設定してください）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理（.env 自動ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py       — ニュースの LLM スコアリング（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - etl.py   — ETL の公開インターフェース
    - pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（欠損/重複/スパイク/日付不整合）
    - audit.py — 監査ログスキーマ定義／初期化（init_audit_schema / init_audit_db）
    - jquants_client.py — J-Quants API クライアント（fetch_*/save_*）
    - news_collector.py — RSS 収集・前処理・安全対策
    - pipeline.py — ETL パイプライン本体（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility の計算
    - feature_exploration.py — 将来リターン/IC/統計サマリー 等
  - research/（補助ユーティリティや再エクスポート含む）
  - その他（strategy / execution / monitoring 等の名前空間は __all__ に含まれますが、ここではデータ・研究・AI を中心に説明しています）

---

## 実運用上の注意 / 設計上の留意点

- Look-ahead bias（未来情報の参照）を防ぐため、モジュールの多くは明示的な target_date を受け取り、datetime.today()/date.today() を直接参照しない設計になっています。
- API 呼び出し（J-Quants / OpenAI）はリトライやバックオフ、レート制限順守の実装がありますが、プロダクション設定（鍵の管理・モニタリング・リトライポリシー）を必ず見直してください。
- DuckDB への executemany に空配列を渡すと問題になるバージョンがあるため、空チェックを行ってから保存する等の注意が払われています。
- ニュース取得においては SSRF や XML 攻撃、gzip ボムなどの対策が実装されていますが、実行環境のセキュリティポリシーに合わせてさらに強化してください。

---

## サポート / 開発メモ

- テストしやすくするために、API 呼び出しポイント（OpenAI 呼び出しや urllib の _urlopen など）はモック可能な構造になっています（unittest.mock.patch 等を利用）。
- 自動で .env を読み込む挙動を無効にしたい（テストや CI）場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

README に含めるべき追加情報（例）
- requirements.txt / Pipfile / pyproject.toml が存在する場合はそちらに従って依存を管理してください。
- 実機での発注（kabu ステーション）機能を使う場合は、運用口座の安全性（2段階認証、テスト環境、監査ログの確認）を必ず確保してください。

ご要望があれば、README に実行例スクリプト（cron / Airflow ジョブ例）、CI 設定、または .env.example の完全なテンプレートを追加で作成します。