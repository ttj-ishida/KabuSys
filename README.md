# KabuSys

日本株向けのデータプラットフォームと自動売買補助ライブラリ群です。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集・NLP（OpenAI を用いたセンチメント）、ファクター計算、監査ログ（発注→約定のトレーサビリティ）など、戦略開発・運用に必要なユーティリティをまとめて提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - raw_news / news_symbols への冗長性のない保存処理
- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM へ投げ、センチメント（ai_score）を ai_scores に保存
  - マクロニュースから市場レジーム（bull/neutral/bear）を判定
  - API エラー時のフォールバック・リトライロジックを備える
- リサーチ / ファクター処理
  - Momentum / Value / Volatility / Liquidity 等のファクター計算
  - 将来リターン・IC（スピアマン）・統計サマリ、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等、発注から約定までのトレーサビリティ用テーブル定義・初期化
  - 冪等性・UTC タイムスタンプ対応
- ユーティリティ
  - 市場カレンダーの営業日判定ロジック（フォールバックあり）
  - J-Quants クライアント（レート制限・リトライ・トークン自動リフレッシュ）
  - 汎用統計ユーティリティ

---

## 必須環境・依存

- Python 3.10 以上（PEP 604 の型記法を使用）
- 主な Python ライブラリ:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装された部分も多いですが、上記は必須または推奨）
- ネットワークで J-Quants / OpenAI にアクセスするための環境

（パッケージ化時は setup/pyproject の requirements を参照してください）

---

## セットアップ

1. リポジトリをクローンして作業ディレクトリに移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -e .
   # または個別に
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env
   - プロジェクトルートの `.env` と `.env.local` を自動読み込みします（既存 OS 環境変数優先）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - OPENAI_API_KEY=<your_openai_api_key>  # AI機能を使う場合
     - KABU_API_PASSWORD=<kabu_api_password>  # kabuステーション連携時
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>

   - 追加の設定（オプション）
     - KABUSYS_ENV = development | paper_trading | live
     - LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）

   例（.env の最小例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な API とサンプルコード）

※ ここで示すのはライブラリ API の一例です。CI/CLI は別途実装してください。

- DuckDB 接続の作成（settings でパスを管理）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（差分取得・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しない場合は today が使用されます
  result = run_daily_etl(conn, target_date=None)
  print(result.to_dict())
  ```

- ニュースセンチメントスコアの生成
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # target_date に対応するウィンドウ（前日15:00 JST 〜 当日08:30 JST）の記事を処理
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（監査専用 DB を分離したい場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査テーブルへ書き込み可能
  ```

- RSS フェッチ（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意事項:
- AI 関連メソッド（score_news, score_regime）は OpenAI API キー（環境変数 OPENAI_API_KEY または引数 api_key）が必要です。
- バックテストやモデル評価時には「Look-ahead Bias」を避ける設計が組み込まれています（関数は内部で date.today() を参照しない等の配慮）。
- DuckDB のバージョン依存（executemany の空リスト扱い等）があるため、ETL の呼び出し時は注意してください。

---

## 環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN (必須: J-Quants 用リフレッシュトークン)
- OPENAI_API_KEY (AI / OpenAI を使う場合必須)
- KABU_API_PASSWORD (kabuステーション連携)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（.env 自動読み込みを無効化）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            # ニュースセンチメント計算（OpenAI）
  - regime_detector.py     # マクロ + MA200 で市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py # 市場カレンダー管理・営業日判定
  - pipeline.py            # ETL パイプライン（run_daily_etl 等）
  - jquants_client.py      # J-Quants API クライアント（取得・保存）
  - news_collector.py      # RSS ニュース収集
  - quality.py             # 品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py               # 汎用統計ユーティリティ（Zスコア等）
  - audit.py               # 監査ログスキーマ (signal/order/execution)
  - etl.py                 # ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py     # Momentum/Value/Volatility 計算
  - feature_exploration.py # 将来リターン / IC / 統計サマリ

その他: テスト、パッケージング用ファイル、ドキュメント（別途管理）

---

## 開発・運用上の注意

- システムは Look-ahead bias を避けるよう設計されています。バックテスト用にデータを使う場合は ETL 時刻・取得範囲に注意してください。
- 外部 API（J-Quants / OpenAI 等）呼び出しはリトライとレート制限制御が入っていますが、API 利用料金やレート制限に注意して運用してください。
- ニュース収集では SSRF 対策・XML の安全解析（defusedxml）・レスポンス上限を設けています。追加ソースを登録する際はホワイトリスト運用を推奨します。
- DuckDB はファイルベースの軽量 DB です。運用では定期的なバックアップとファイルアクセス制御を行ってください。

---

以上が KabuSys の簡易 README です。追加で CLI 実行例、データスキーマ（DDL）、運用手順（cron / scheduler）のテンプレートなどが必要であれば教えてください。