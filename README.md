# KabuSys

日本株向けの自動売買／データプラットフォーム基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ（約定トレース）などを含むモジュール群を提供します。

---

## 主な特徴

- J-Quants API 経由での株価日足・財務データ・マーケットカレンダー取得（ページネーション・リトライ・レートリミット対応）
- DuckDB を用いた ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と LLM によるニュースセンチメントスコアリング（gpt-4o-mini を想定）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースのセンチメントを合成）
- 研究用のファクター計算・特徴量解析ユーティリティ（モメンタム、ボラティリティ、バリュー、IC 等）
- 監査ログ（signal / order_request / execution）用のスキーマ定義と初期化ユーティリティ
- 環境変数 / .env 自動読み込み（プロジェクトルート検出）

---

## 機能一覧（モジュール）

- kabusys.config
  - 環境変数管理・自動 .env 読み込み
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline / etl: ETL 実行エントリ（run_daily_etl 等）
  - news_collector: RSS → raw_news 保存（SSRF対策・前処理）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定
  - audit: 監査ログ（テーブル・インデックス）初期化
  - stats: 汎用統計ユーティリティ（z-score 正規化）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとニュースセンチメントを ai_scores に書込
  - regime_detector.score_regime: 日次の市場レジーム判定（bull/neutral/bear）
- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 要件

- Python 3.10+
- 必須（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- ネットワークアクセス: J-Quants API, RSS ソース, OpenAI API へのアクセスが必要

（実際のインストール要件は pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン / コピー
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. インストール
   - 開発中に参照する場合（editable install）
     ```bash
     pip install -e .
     ```
   - もしくは必要パッケージのみインストール
     ```bash
     pip install duckdb openai defusedxml
     ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - その他（任意）
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG/INFO/...)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB）
     - PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

   - .env.example（参考）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## データベース初期化

- 監査ログ用 DuckDB を初期化するサンプル:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可
  ```

- 任意の DuckDB 接続に監査スキーマを追加する:
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

---

## 使い方（代表的な API）

- DuckDB 接続作成（設定のパスを使用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai_scores へ書き込む）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {n}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込む）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- RSS フィード取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点:
- score_news / score_regime は OpenAI API を使用します。API 失敗時はフェイルセーフ（スコア 0 や一部スキップ）で継続する実装です。
- J-Quants API はレート制限（120 req/min）とトークンリフレッシュを内部で扱いますが、APIキーの管理は `.env` 等で行ってください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋、実際は src 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py                       - 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    - ニュースセンチメント (score_news)
    - regime_detector.py             - 市場レジーム判定 (score_regime)
  - data/
    - __init__.py
    - jquants_client.py              - J-Quants API クライアント（fetch/save）
    - pipeline.py                    - ETL パイプラインと run_daily_etl
    - etl.py                         - ETLResult の再エクスポート
    - news_collector.py              - RSS 収集・前処理
    - quality.py                     - データ品質チェック
    - calendar_management.py         - 市場カレンダー管理（is_trading_day 等）
    - audit.py                       - 監査ログ（DDL / 初期化）
    - stats.py                       - zscore 正規化 等
  - research/
    - __init__.py
    - factor_research.py             - モメンタム / ボラティリティ / バリュー
    - feature_exploration.py         - 将来リターン / IC / summary / rank

---

## 運用上の注意

- 環境設定（.env）に機密情報を含める際はアクセス管理・権限を適切に設定してください。
- OpenAI の利用はコストが発生します。バッチサイズやモデルの選定に注意してください。
- J-Quants API 利用は利用規約に従ってください（トークンやレート制限）。
- DuckDB ファイルは定期的にバックアップしてください（監査ログ等を失うと不可逆）。

---

## 貢献 / 開発者向け

- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env 読み込みを無効化できます（テスト時に便利）。
- OpenAI API 呼び出し等はユニットテストでモックしやすい設計になっています（内部呼び出し関数を差し替え可能）。

---

必要であれば README にサンプル .env.example を追加したり、具体的な CI / デプロイ手順（systemd の PID 管理や監視設定、Slack 通知フロー等）を追記できます。どの情報を優先して載せたいか教えてください。