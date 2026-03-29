# KabuSys — 日本株自動売買基盤 (README)

KabuSys は日本株のデータ取得・ETL、ファクター研究、ニュース NLP、レジーム判定、監査ログなどを備えた自動売買基盤のライブラリ群です。本リポジトリはモジュール化されており、データパイプラインと研究用ユーティリティ、AI を使ったニュース解析・市場レジーム判定、監査（トレーサビリティ）機能を提供します。

---

## 主な特徴

- データ取得・ETL
  - J-Quants API から株価日足、財務データ、上場情報、JPX マーケットカレンダーを差分取得（ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT / INSERT … DO UPDATE）
  - データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- ニュース収集＆前処理
  - RSS フィード取得（SSRF対策、gzip 対応、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存処理
- AI(LLM) を用いた NLP
  - ニュースの銘柄別センチメント（gpt-4o-mini を想定）を ai_scores に書き込み（batch±retry）
  - マクロ記事のセンチメントと ETF（1321）200 日 MA 乖離を合成して市場レジーム（bull/neutral/bear）を判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブルを DuckDB に初期化
  - order_request_id を冪等キーとして二重発注を防止
- 設定管理
  - 環境変数（.env / .env.local）の自動ロード、必須環境変数の検証、実行環境判定（development/paper_trading/live）

---

## 必要条件

- Python 3.10+
- 必要パッケージ（主なもの）:
  - duckdb
  - openai
  - defusedxml
  - その他: 標準ライブラリ以外を追加する場合はプロジェクトの requirements を確認してください

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を用意します。
   ```bash
   git clone <this-repo>
   cd <this-repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 依存パッケージをインストールします（例）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

3. 環境変数設定
   - プロジェクトルート(.git または pyproject.toml のある場所) に `.env` を置くと自動で読み込まれます（.env.local は .env を上書きする）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主に必要な環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot token（必須）
     - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う際に必須）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — 実行環境 (development | paper_trading | live). デフォルトは development
     - LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL). デフォルト INFO

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-xxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（主要 API の例）

以下は主要な利用例です。DuckDB 接続には `duckdb.connect(path)` を利用します。

- DuckDB 接続の作成（デフォルトパスを使う例）:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を省略すると今日が対象（内部では営業日に調整されます）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLU（銘柄ごとのニュースセンチメント）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数に設定されていれば api_key 引数不要
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n} codes")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（トレーサビリティ）スキーマ初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  # ファイルを作成して初期化
  audit_conn = init_audit_db("data/audit_kabusys.duckdb")
  # あるいは既存 conn に対して init_audit_schema(conn, transactional=True) を呼ぶ
  ```

- 研究用ファクター計算の呼び出し例:
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点:
- AI 呼び出し（News / Regime）は OpenAI API を使用します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- AI 呼び出しはリトライとフォールバック（失敗時は 0.0 等）を実装していますが、料金発生やレート制限に注意してください。

---

## 設定の自動読み込み挙動

- モジュール `kabusys.config` は実行時にプロジェクトルート (現在のファイルから親ディレクトリ上で `.git` または `pyproject.toml` を探索) を見つけると `.env` および `.env.local` を自動読み込みします。
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` を上書きします（override=True）。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- `Settings` クラス経由で設定へアクセスできます（例: `from kabusys.config import settings`）。

---

## ディレクトリ構成 (主要ファイルと概要)

以下は package の主要なディレクトリとモジュールの概観（src/kabusys）:

- __init__.py
  - パッケージ定義、public サブパッケージの列挙
- config.py
  - 環境変数管理、自動 .env ロード、Settings クラス
- ai/
  - news_nlp.py — ニュースセンチメント解析（OpenAI 経由）、ai_scores への書き込み
  - regime_detector.py — ETF(1321) MA200 乖離とマクロニュースを統合して market_regime を生成
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ等
  - __init__.py — 研究用 API エクスポート
- data/
  - pipeline.py — ETL のメインロジック（run_daily_etl 等）
  - etl.py — ETL 関連の公開型（ETLResult）
  - jquants_client.py — J-Quants API クライアント（取得/保存/認証/レート制御）
  - news_collector.py — RSS 取得・前処理・保存（SSRF 対策・gzip 対応）
  - calendar_management.py — マーケットカレンダー、営業日計算、calendar_update_job
  - stats.py — 共通統計ユーティリティ（Zスコア正規化）
  - quality.py — データ品質チェック（欠損/重複/スパイク/日付不整合）
  - audit.py — 監査ログテーブル定義と初期化
  - __init__.py
- research/
  - research 用ユーティリティとファイル群（上記参照）
- その他
  - 各サブモジュールは duckdb 接続を引数に取り、データベース操作を行う設計

（実際のリポジトリでは src を含むトップツリー構成になっています）

---

## 実行環境・運用に関する注意

- Python バージョン: ソース内の型注釈（X | None）に合わせ Python 3.10 以上を推奨します。
- セキュリティ:
  - API キーやトークンは `.env` やシークレットマネージャに安全に保存してください。
  - news_collector は SSRF 対策や受信サイズ上限を施していますが、運用時は RSS ソースの信頼性・帯域・頻度に注意してください。
- Look-ahead bias 防止:
  - 多くの関数は内部で datetime.today()/date.today() を無暗に参照せず、外部から target_date を渡す設計になっています。バックテストでは必ず適切な date を渡してください。
- レート制限:
  - J-Quants API のレート制限（120 req/min）や OpenAI の制限に注意し、連続処理では適切な間隔・リトライ戦略を確保しています。

---

## 開発・テスト

- モジュール内の API 呼び出しや時間取得部分はテストで差し替えやすいように分離されています（例: _call_openai_api を patch する等）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で .env 自動読み込みをオフにしてテストを行うことができます。

---

## 参考（よく使うインポート例）

```python
# 設定アクセス
from kabusys.config import settings

# ETL
from kabusys.data.pipeline import run_daily_etl, ETLResult

# ニューススコアリング / レジーム
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

# 監査ログ初期化
from kabusys.data.audit import init_audit_db
```

---

README はここまでです。追加で「インストール手順をスクリプト化」や「各環境変数の .env.example」を作成したい場合や、特定の機能（例: news_collector の RSS ソース追加手順）について詳細なドキュメントを生成することも可能です。必要があれば教えてください。