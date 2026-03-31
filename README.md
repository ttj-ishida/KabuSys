# KabuSys

KabuSys は日本株向けのデータプラットフォームとリサーチ / AI 支援の自動売買基盤のコアライブラリです。  
DuckDB に格納したマーケットデータを ETL で収集・品質検査し、AI（OpenAI）を使ったニュースセンチメントや市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local から自動ロード（プロジェクトルート検出）
  - 必須設定を .env.example を元に管理
- データ収集（J-Quants 統合）
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 四半期財務データ取得
  - JPX マーケットカレンダー取得・更新
  - レートリミッティング・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得・バックフィル・品質チェック（欠損、重複、スパイク、日付不整合）
  - run_daily_etl による一括実行
- ニュース収集・前処理
  - RSS フィードから記事を収集・トラッキングパラメータ除去・正規化・SSRF 対策
- AI（OpenAI）連携
  - ニュースごとのセンチメントスコアリング（ai.score_news）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（ai.score_regime）
  - OpenAI の JSON Mode を用いた堅牢なレスポンス処理とリトライ
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions テーブルの初期化・管理
  - order_request_id による冪等（重複発注防止）

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（typing の | 演算子等を使用）
- Git（ソース取得時）

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   最低限の依存:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. パッケージをインストール（開発インストール推奨）
   ```
   pip install -e .
   ```

5. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を作成します。自動ロードはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。主に必要な環境変数:

   - JQUANTS_REFRESH_TOKEN（必須） — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD（必須） — kabuステーション API のパスワード
   - KABU_API_BASE_URL（任意、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN（必須） — Slack 通知用
   - SLACK_CHANNEL_ID（必須）
   - DUCKDB_PATH（任意、デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（任意、デフォルト: data/monitoring.db）
   - KABUSYS_ENV（optional）: development / paper_trading / live
   - LOG_LEVEL（optional）: DEBUG / INFO / WARNING / ERROR / CRITICAL

   注意: OpenAI を使う機能を呼ぶ場合は OPENAI_API_KEY を環境変数で設定するか、各関数に api_key 引数を渡します。

---

## 使い方（簡単な利用例）

以下はライブラリ API の代表的な使い方です。DuckDB 接続は duckdb.connect() で作成できます。

1. DuckDB 接続
   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL 実行
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # 引数で target_date, id_token など指定可
   print(result.to_dict())
   ```

3. ニュースセンチメントスコア（OpenAI API キー必須）
   ```python
   from kabusys.ai import score_news
   from datetime import date

   # 環境変数 OPENAI_API_KEY が設定されている場合は api_key を省略可
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書き込み銘柄数: {written}")
   ```

4. 市場レジームスコア
   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date

   score_regime(conn, target_date=date(2026, 3, 20))
   ```

   注意: OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY を使用します。

5. 研究用ファクター計算例
   ```python
   from kabusys.research import calc_momentum, calc_value, calc_volatility
   from datetime import date

   mom = calc_momentum(conn, date(2026, 3, 20))
   vol = calc_volatility(conn, date(2026, 3, 20))
   val = calc_value(conn, date(2026, 3, 20))
   ```

6. 監査ログ DB の初期化（発注・約定用）
   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/audit.duckdb")
   # audit_conn を通じて監査テーブルを利用できます
   ```

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（ai 関数を使う場合）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — "development" / "paper_trading" / "live"
- LOG_LEVEL — ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化

自動ロードは、パッケージ内の設定モジュールがプロジェクトルート（.git または pyproject.toml）を検出した場合に .env → .env.local の順で行います。

---

## ディレクトリ構成

リポジトリ内（主要ファイル）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理
    - ai/
      - __init__.py
      - news_nlp.py            — ニュースセンチメント（OpenAI）
      - regime_detector.py     — マクロ + MA200 による市場レジーム判定
    - data/
      - __init__.py
      - calendar_management.py — マーケットカレンダー管理・営業日判定
      - etl.py                 — ETL インターフェース再エクスポート
      - pipeline.py            — ETL パイプライン実装（run_daily_etl 等）
      - stats.py               — 統計ユーティリティ（zscore_normalize 等）
      - quality.py             — データ品質チェック
      - audit.py               — 監査ログテーブル定義・初期化
      - jquants_client.py      — J-Quants API クライアント（取得＋保存）
      - news_collector.py      — RSS ニュース収集・前処理
    - research/
      - __init__.py
      - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
      - feature_exploration.py — 将来リターン・IC・統計サマリー
    - research/*（他ユーティリティ）
  - （パッケージメタ情報等）

この README は主要な利用ポイントをまとめたものです。コード内の docstring に詳細な設計方針や注意点が多数記載されていますので、実装や拡張時は個別モジュールのドキュメントコメントを参照してください。

---

もし README に特定の使い方（eg. CI / デプロイ手順、監視設定、Slack 通知設定例、.env.example のテンプレート）を追加したい場合は、その内容を教えてください。必要に応じてサンプル .env.example も作成します。