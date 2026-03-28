# KabuSys

日本株を対象とした自動売買 / データ基盤ライブラリ群です。  
データ収集（J-Quants, RSS）、データ品質チェック、ファクター計算、ニュースのAI評価、監査ログ（発注→約定トレーサビリティ）など、トレーディングプラットフォームに必要な主要機能をモジュール単位で提供します。

主な目的
- データパイプライン（ETL）による株価・財務・マーケットカレンダーの取得と永続化（DuckDB）
- ニュースの自然言語処理による銘柄センチメント評価（OpenAI）
- 市場レジーム判定（ETF + マクロニュース）
- 研究用途のファクター計算・特徴量解析
- 発注・約定フローの監査ログ（監査用 DuckDB スキーマ）

---

## 機能一覧

- data
  - jquants_client：J-Quants API からのデータ取得（株価、財務、マーケットカレンダー等）と DuckDB 保存（冪等処理）
  - pipeline：日次 ETL（calendar → prices → financials）と ETL 結果クラス（ETLResult）
  - quality：データ品質チェック（欠損、重複、スパイク、日付不整合）
  - news_collector：RSS からニュース収集と前処理（SSRF・Gzip・トラッキング除去対策）
  - calendar_management：市場カレンダー管理／営業日判定ユーティリティ
  - audit：戦略→シグナル→発注→約定 を追跡する監査スキーマの初期化ユーティリティ
  - stats：Zスコア正規化など共通統計ユーティリティ
- ai
  - news_nlp.score_news：ニュースを銘柄ごとにまとめ、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルに保存
  - regime_detector.score_regime：ETF（1321）200日MA乖離とマクロニュース（LLM評価）を合成して market_regime を作成
- research
  - factor_research：momentum / volatility / value 等のファクター計算関数
  - feature_exploration：将来リターン計算、IC（Spearman）計算、統計サマリーなど

設計上の特徴
- ルックアヘッドバイアス防止（内部で date.today() を直接参照しない、DB クエリに排他条件を付ける等）
- 冪等性（DB 保存は ON CONFLICT で上書き）
- ネットワーク/API 呼び出しに対するリトライとバックオフ
- テスト容易性（OpenAI 呼び出し箇所などをテスト時にモックしやすい実装）

---

## 動作要件（推奨）

- Python 3.10+
- 主な依存ライブラリ（インストール例は次節参照）
  - duckdb
  - openai (OpenAI の新しい SDK を想定)
  - defusedxml
  - そのほか標準ライブラリのみで多くを実装

---

## セットアップ手順

1. リポジトリをチェックアウト（例）
   ```
   git clone <repo-url>
   cd <repo-directory>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要ライブラリをインストール（例）
   - 単純な例（最小）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実プロジェクトでは requirements.txt / pyproject.toml 経由で管理してください。

4. 環境変数の準備
   - プロジェクトルートに `.env` と `.env.local` を置くと、自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必須（運用・機能に応じて）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client 用）
     - OPENAI_API_KEY — OpenAI API キー（ai/news_nlp, ai/regime_detector 用）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（取引実行系で使用）
     - SLACK_BOT_TOKEN — Slack 通知用（必要に応じて）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルトあり:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   例 .env の一部:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=yourpassword
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な例）

下記はライブラリを直接 Python から利用する例です。DuckDB の接続先は settings.duckdb_path のデフォルトに合わせるか、明示的に指定してください。

- 日次 ETL を実行（pipeline.run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に保存（ai.news_nlp.score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込まれた銘柄数: {written}")
  ```

- 市場レジームをスコアリングして market_regime に保存（ai.regime_detector.score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用データベース初期化（audit.init_audit_db）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn は監査テーブルが初期化された DuckDB 接続
  ```

- ファクター計算（research.factor_research）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), "件のモメンタム計算結果")
  ```

テスト時のポイント
- OpenAI への HTTP 呼び出しは各モジュール内の _call_openai_api を patch/mocking して差し替え可能です（unit test での外部依存除去）。
- jquants_client の HTTP 呼び出しも外部に依存するため、モックやスタブを使ってテストしてください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール（src/kabusys 以下）を抜粋しています。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL 結果型の再エクスポート
    - news_collector.py             — RSS 収集 / 前処理
    - calendar_management.py        — マーケットカレンダー管理 / 営業日判定
    - quality.py                    — データ品質チェック
    - stats.py                      — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログ（テーブル定義・初期化）
    - pipeline.py                   — （ETL の本体）
  - research/
    - __init__.py
    - factor_research.py            — momentum/volatility/value 等
    - feature_exploration.py        — 将来リターン, IC, 統計サマリー
  - ai/__init__.py
  - research/__init__.py

（上記は主要ファイルのみ。細かなユーティリティはコメントの通り多くの関数が実装されています）

---

## 実運用上の注意 / ヒント

- 自動で .env 読み込みを行う挙動
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` → `.env.local` を自動読み込みします。テストや特殊環境では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- DuckDB のスキーマとテーブル
  - ETL / save_* 関数は特定のテーブル（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, market_regime 等）への保存を前提としています。初期スキーマはプロジェクト側で定義・整備してください（audit.init_audit_db で監査テーブルは自動作成できます）。
- OpenAI 呼び出し
  - news_nlp と regime_detector は gpt-4o-mini（JSON mode）を想定したプロンプト設計・レスポンス検証を行っています。API に依存するため、APIキー管理やコスト・レート制限に注意してください。
- J-Quants API レート制限
  - jquants_client は 120 req/min 制限を守るため RateLimiter を使っています。大量のページネーションや全銘柄取得時は時間がかかることに注意してください。
- ログと運用モード
  - KABUSYS_ENV（development / paper_trading / live）で挙動の分岐があるので、本番運用時は live を設定してください。LOG_LEVEL で出力レベルを調整できます。

---

## 貢献 / 開発

- コードの各所にテスト容易性を考慮したポイント（API 呼び出しの抽象化、明示的な引数注入など）があるため、ユニットテストは外部依存の差し替え（monkeypatch / unittest.mock）で実装してください。
- 変更を行う際は、ETL・データ保存の冪等性・ルックアヘッドバイアスの回避を壊さないよう注意してください。

---

README にない詳細や、実際のスキーマ（CREATE TABLE 文）・CI 設定・パッケージング方針などはリポジトリ内のドキュメント（DataPlatform.md, StrategyModel.md 等）を参照するとよいです。質問や使用例の追加が必要であれば教えてください。