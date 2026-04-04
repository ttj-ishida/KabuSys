# KabuSys

KabuSys は日本株のデータ取得・ETL、ニュース NLP（LLM）によるセンチメント評価、ファクター計算、監査ログ等を含む日本株自動売買プラットフォームのライブラリ群です。本リポジトリはライブラリとしての提供を想定しており、各モジュールを組み合わせて ETL バッチや戦略ロジック、実行系を構築できます。

---

## 概要

主な目的は以下です。

- J-Quants API を用いた株価・財務・カレンダー等の差分取得（ETL）
- DuckDB によるデータ保存と品質チェック（quality）
- RSS ニュース収集と前処理（news_collector）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントのスコア化（news_nlp）
- マクロニュースと ETF（1321）200日 MA 乖離を合成した市場レジーム判定（regime_detector）
- 研究用途のファクター計算・特徴量探索（research モジュール群）
- 監査ログ（signal → order_request → executions）のスキーマ初期化（audit）

このライブラリは Look-ahead バイアス回避、API リトライ、冪等性、SSRF 対策など運用・安全面の配慮が組み込まれています。

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルートを検出）
  - settings オブジェクトによる集中管理（J-Quants / kabu / LINE / DB パス 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl 等）
  - calendar_management: 市場カレンダー管理・営業日判定
  - news_collector: RSS フィード収集・前処理・raw_news 保存（SSRF 対策あり）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - stats: 汎用統計ユーティリティ（zscore 正規化等）
  - audit: 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - etl: ETLResult 型の再エクスポート
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価・ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の ma200 乖離とマクロセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提・依存関係

- Python 3.10 以上（PEP 604 の型構文（A | B）を使用）
- 必須 Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib 等）を多用

（プロジェクトに requirements.txt がある場合はそれを使用してください。なければ上記パッケージをインストールしてください。）

インストール例:
```
python -m pip install --upgrade pip
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートに移動
2. Python 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
4. データディレクトリを作成（settings のデフォルト DB パスに合わせる）
   ```
   mkdir -p data
   ```
5. 環境変数（または .env ファイル）を用意
   - 自動読み込みについて:
     - パッケージはプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探索し、プロジェクトルートにある `.env` を自動読み込みします。
     - 読み込み優先順位: OS 環境変数 > .env.local > .env
     - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主な環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=xxxxx
     OPENAI_API_KEY=sk-...
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development   # development | paper_trading | live
     LOG_LEVEL=INFO
     ```
   - 必須: JQUANTS_REFRESH_TOKEN（J-Quants 認証）、KABU_API_PASSWORD（kabu API を使う場合）、OPENAI_API_KEY（AI スコアを使う場合）

---

## 使い方（基本的な例）

以下のサンプルは Python スクリプト/REPL からの利用例です。DuckDB の接続は kabusys.config.settings.duckdb_path を参照するか明示パスを渡してください。

- DuckDB 接続を作る:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（J-Quants のトークンは settings から自動取得されます）:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースのセンチメントをスコア化して ai_scores に保存:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# 明示的に API キーを渡すことも可能（api_key=None の場合は OPENAI_API_KEY を参照）
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored codes:", count)
```

- 市場レジーム判定を実行:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB を初期化（独立 DB を使う場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/monitoring_audit.duckdb")
# これで監査テーブルが作成されます
```

- 監視・品質チェックを実行:
```python
from kabusys.data.quality import run_all_checks
from datetime import date

issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for issue in issues:
    print(issue)
```

注意点:
- OpenAI 呼び出しや J-Quants API 呼び出しはネットワーク依存・料金発生するため、テスト時はモック化を推奨します（コード内でもテスト差替えや _call_openai_api の patch を想定）。
- DuckDB executemany に対する空リストの扱い（バージョン差）を各所で考慮しています。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（LLM 呼び出しに使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視等で使用するファイル）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（任意）

設定は .env / .env.local に記述すると自動で読み込まれます（上書きルールに注意）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル群（本リポジトリ内の実装に基づく一覧）です。

- src/kabusys/
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
    - stats.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - その他（将来的に strategy, execution, monitoring 等のモジュールを想定）

各モジュールはドキュメント文字列や関数名で使い方が説明されており、関数レベルで直接呼び出せる設計です。

---

## 運用上の注意

- Look-ahead バイアス回避:
  - AI モジュール・ETL 等は target_date を明示することで将来情報の参照を避ける設計になっています。バックテスト用途では必ず過去のデータのみを使うよう注意してください。
- 冪等性:
  - jquants_client の保存関数や audit の初期化は基本的に冪等です（ON CONFLICT 等を使用）。
- エラーハンドリング:
  - 外部 API 呼び出しはリトライ・フォールバック（API 失敗時のローカルフォールバック等）を実装しており、致命的な失敗時は例外を投げます。運用時はログ監視と通知（LINE 連携等）を検討してください。
- テスト:
  - 外部 API を呼ぶ箇所（OpenAI / J-Quants / HTTP）はモック化して単体テストを行ってください。コード内で差し替えを想定した hook（_call_openai_api の patch 等）が用意されています。

---

## 開発・貢献

- コードのスタイルやテスト方針に合わせて Pull Request をお送りください。
- 外部 API のキーや秘密情報はコミットしないでください（.env を利用し、README に示した方法で管理してください）。

---

この README はコード内のドキュメント文字列を基に作成しています。詳細な API 仕様や追加ユーティリティは各モジュールの docstring を参照してください。必要であれば利用例・CLI スクリプト・デプロイ手順などの追加ドキュメントも作成します。