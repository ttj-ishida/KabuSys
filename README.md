# KabuSys

日本株向けのデータパイプライン・リサーチ・AI支援を備えた自動売買 / 研究プラットフォームのコアライブラリです。  
このリポジトリは主に次を提供します：

- J-Quants API を用いた差分 ETL（株価、財務、カレンダー）
- ニュース収集と LLM（OpenAI）によるニュースセンチメント集約（銘柄別 / マクロ）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック、マーケットカレンダー管理、監査ログ（発注・約定トレーサビリティ）
- DuckDB を中心としたローカルデータ保存

注意: 本 README は src/kabusys 以下の実装に基づき記載しています。戦略・実行（発注）や監視機能のアプリケーション層は別途実装を想定しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - 環境変数管理（.env / .env.local の自動ロード、必須変数取得）
  - 環境（development / paper_trading / live）やログレベルの検証

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得／保存／リトライ／レート制限）
  - pipeline: 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - news_collector: RSS 収集（SSRF対策・サイズ制限・正規化）と raw_news 保存処理
  - audit: 監査ログ用スキーマ初期化（signal_events, order_requests, executions）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: zscore_normalize 等の汎用統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント（OpenAI → ai_scores に書込）
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロセンチメントを合成して market_regime に書込

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility（price / financials ベース）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats の zscore_normalize を再利用可能

---

## セットアップ手順

前提
- Python 3.10+（typing | 型アノテーションに Path | | を用いているため）
- DuckDB を利用（ローカル DB）
- OpenAI API を用いる機能は OpenAI の API キーが必要

1. リポジトリをクローン（例）
   ```
   git clone <this-repo>
   cd <this-repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージのインストール（例）
   - 最低限必要なパッケージ（実装に依存するもの）
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発時はプロジェクトが pyproject.toml を提供していれば:
     ```
     pip install -e .
     ```
     （editable install。なければ上記個別インストールで十分）

4. 環境変数 / .env の設定
   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` と `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。テストなどで自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必要な環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - OPENAI_API_KEY: OpenAI API キー（AI スコアリング用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注等）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト値あり）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite (monitoring) のパス（例: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live
   - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

   .env のサンプル:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は Python スクリプト / REPL からの利用例です。実行前に必ず必要な環境変数を設定してください。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメント（銘柄別）のスコア取得
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数に設定されていること
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", written)
  ```

- マーケットレジーム判定（ETF 1321 の MA200 + マクロセンチメント）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  # api_key を引数で与えることも可能（None なら OPENAI_API_KEY を参照）
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算（モメンタム / ボラティリティ / バリュー）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  m = calc_momentum(conn, date(2026,3,20))
  v = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

- 監査ログスキーマの初期化（発注/約定テーブルの作成）
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn, transactional=True)
  ```

- RSS 取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

- J-Quants からのデータ取得（直接呼び出し）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  from datetime import date

  token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  ```

---

## 注意事項 / 実装上の設計方針（抜粋）

- Look-ahead bias 対策:
  - 計算関数や ETL は内部で datetime.today() / date.today() を不用意に参照しない設計を意識しています。target_date を明示的に渡して利用してください。
  - データ取得時に fetched_at を記録し「いつ入手したか（知り得たか）」をトレースします。

- 冪等性:
  - jquants_client の保存関数（save_*）やニュース保存は ON CONFLICT / INSERT … DO UPDATE / DO NOTHING を用いて冪等的に動作します。

- API リトライ・レート制限:
  - J-Quants クライアントは固定間隔スロットリング（120 req/min）と指数バックオフを実装しています。
  - OpenAI 呼び出しはリトライ（429/ネットワーク/5xx）を行い、最終失敗時はスコアをフォールバック（0.0）して継続する設計です。

- セキュリティ/堅牢性:
  - news_collector は SSRF 対策、gzip 解凍サイズチェック、XML の defusedxml を利用したパース、URL の正規化とトラッキングパラメータ除去などを行います。

---

## ディレクトリ構成（src/kabusys の主要ファイル）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - quality.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (strategy/, execution/, monitoring/ は __all__ に含まれますが、実装はプロジェクトにより補完されます)

各モジュールには docstring で設計方針と処理フローが詳述されているため、実装参照の際に役立ちます。

---

## トラブルシューティング / よくある質問

- .env が読み込まれない
  - プロジェクトルートは .git または pyproject.toml を上から探索して決定します。該当ファイルが無いレイアウトの場合は自動読み込みがスキップされます。自動読み込みを無効化している場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認してください。

- OpenAI API 呼び出しの失敗
  - OPENAI_API_KEY を正しく設定してください。API レートや課金制限に抵触する可能性もあるため注意してください。AI 関連関数は失敗時にフォールバックする設計ですが、ログを確認して根本原因を解析してください。

- DuckDB への書き込み／スキーマ初期化
  - 初回は監査スキーマなどが無いため `init_audit_schema` などを呼んでください。ファイルパスのディレクトリが存在しない場合は自動で作成されます（init_audit_db を使用する場合）。

---

## 貢献 / 拡張案

- strategy / execution モジュールを実装して実際の発注フローを追加
- GUI / Web ダッシュボードで ETL 状態や品質チェック、監査ログを可視化
- モデル管理（戦略バージョン管理）やバックテストフレームワークと連携

---

以上が本コードベースの概要と基本的な使い方です。詳細は各モジュールの docstring を参照してください。追加で README に載せたい例（CI、テスト方法、pyproject 設定例など）があれば教えてください。