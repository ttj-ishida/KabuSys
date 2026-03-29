# KabuSys — 日本株自動売買 / データプラットフォーム

KabuSys は日本株向けのデータ取得・品質管理・特徴量生成・ニュースNLP・市場レジーム判定・監査ログまでを備えた自動売買 / 研究基盤です。  
このリポジトリは主に以下を提供します：

- J-Quants API を使った株価・財務・マーケットカレンダーの ETL
- DuckDB を用いたデータ永続化と品質チェック
- RSS ベースのニュース収集と OpenAI による銘柄別 NLP スコアリング
- ETF とマクロニュースを組み合わせた市場レジーム判定 (LLM ベース)
- ファクター計算・特徴量探索（研究用ユーティリティ）
- 発注フローの監査ログ（トレーサビリティ用テーブル生成）
- 環境設定の読み込みユーティリティ（.env 自動読み込み等）

以下はコードベースに基づく README（日本語）です。

---

## 主な機能

- ETL（差分取得・バックフィル・品質チェック）
  - run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl
- J-Quants API クライアント（ページネーション・リトライ・レート制御・トークン自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue オブジェクト）
- ニュース収集（RSS）と前処理（SSRF/サイズ/トラッキング除去等）
  - fetch_rss / preprocess_text / news → raw_news, news_symbols への保存（別処理）
- OpenAI を使った NLP スコアリング
  - score_news（銘柄毎のセンチメントを ai_scores に書き込み）
  - score_regime（ETF 200日MA乖離 + マクロニュースの LLM センチメントで市場レジーム判定）
- 研究用ユーティリティ
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / zscore_normalize など
- 監査ログ（audit）テーブルの初期化ユーティリティ
  - init_audit_schema / init_audit_db
- 設定管理
  - settings（環境変数 / .env / .env.local の自動読み込み、必須キーチェック）

---

## 動作要件

- Python 3.10+
  - （typing の | 演算子や型注釈を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai (openai パッケージ v1 系を想定)
  - defusedxml
- ネットワークアクセス（J-Quants、OpenAI、RSS フィード）
- J-Quants / OpenAI の API キー等の環境変数

（プロジェクトの requirements.txt がある場合はそちらを使用してください。なければ上のパッケージを pip でインストールしてください）

---

## インストール手順（開発環境）

1. リポジトリをクローン：
   ```
   git clone <このリポジトリのURL>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）：
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール（例）：
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml に従ってください。

4. 開発用インストール（パッケージ化されている場合）：
   ```
   pip install -e .
   ```

---

## 環境変数 / .env

このプロジェクトは環境変数またはルートの `.env` / `.env.local` から設定を読み込みます（自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。必須となる環境変数は次の通りです。

必須（最低限）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API パスワード（注文連携ある場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI 呼び出しを行う場合（score_news / score_regime）

任意:
- KABUSYS_ENV — 開発環境指定（development, paper_trading, live）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ（DB 初期化など）

- 監査ログ用 DuckDB を作成してスキーマ初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # :memory: も可
  ```
  または既存 DuckDB 接続へスキーマを追加:
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

---

## 使い方（例）

以下は主要ユーティリティの使用例です。実行は Python スクリプトまたは REPL で行えます。

- settings の参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)         # Path オブジェクト
  print(settings.is_live, settings.log_level)
  ```

- DuckDB へ接続して日次 ETL を実行:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア（OpenAI を用いて ai_scores に書き込む）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数にあれば api_key 引数は省略可能
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"wrote {written} scores")
  ```

- 市場レジーム判定（ETF 1321 を用いた MA + マクロニュース）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を直接渡すか環境変数 OPENAI_API_KEY を設定
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログスキーマ初期化（既存接続へ）:
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 研究用ユーティリティの呼び出し例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
  ```

---

## ログと実行モード

- KABUSYS_ENV:
  - development / paper_trading / live
  - settings.is_live / is_paper / is_dev で判定可能
- LOG_LEVEL 環境変数でログ出力レベルを制御

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主要モジュールと概要です（抜粋）。

- src/kabusys/__init__.py
  - パッケージ定義（__version__ 等）
- src/kabusys/config.py
  - 環境変数・.env 自動読み込み・設定オブジェクト（settings）
- src/kabusys/ai/
  - news_nlp.py — 記事をまとめて OpenAI で銘柄別センチメント評価（score_news）
  - regime_detector.py — ETF 1321 MA200 とマクロニュースを組み合わせた市場レジーム判定（score_regime）
- src/kabusys/data/
  - jquants_client.py — J-Quants API クライアント（取得/保存/認証）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）と ETLResult
  - quality.py — データ品質チェック（欠損/重複/スパイク/日付不整合）
  - news_collector.py — RSS 取得・前処理・記事 ID 生成
  - calendar_management.py — JPX カレンダー管理（営業日判定・更新ジョブ）
  - audit.py — 監査ログテーブル定義/初期化
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py / etl.py — ETL 統合インターフェース
- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー等
  - __init__.py — 研究向けユーティリティの再エクスポート

（上記は主要ファイルの抜粋です。実際のディレクトリにはさらに補助モジュールやサブ機能が含まれます）

---

## 実行上の注意点 / ベストプラクティス

- Look-ahead Bias に配慮:
  - 各モジュールは内部で date を明示的に指定する設計（datetime.today() を直接参照しない）
  - バックテストや研究では ETL の時点で取得したデータのみを用いてください
- OpenAI 呼び出し:
  - API 呼び出しはリトライや JSON バリデーションを実装していますが、APIキーの管理・コストに注意してください
- J-Quants レート制限:
  - _RateLimiter による固定間隔スロットリングを実装（120 req/min を想定）
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して .env を自動読み込みします。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください
- DuckDB の挙動:
  - executemany に空リストを渡せないバージョンの互換対応がされています（呼び出し側でも注意）

---

## サポート / 貢献

ドキュメントの修正や機能追加、バグ修正は Pull Request を歓迎します。実行に必要な追加ドキュメント（requirements.txt、実運用手順、CI 設定等）を整備することで利用しやすくなります。

---

この README はソースコードの構成・コメントをもとに作成しています。実際の運用前には環境変数の設定、API キーの取得、DuckDB スキーマの作成（必要に応じて別途スキーマ初期化スクリプト）を行ってください。必要であれば、各モジュールの使い方のより詳細なチュートリアルや設定テンプレート（.env.example）を追加できます。