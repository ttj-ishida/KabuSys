# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリセットです。  
データ収集（J-Quants / RSS）、ETL、品質チェック、特徴量計算、ニュースNLP（OpenAI）、市場レジーム判定、監査ログなどを含むモジュール群を提供します。

---

## 概要

KabuSys は以下を目的とした内部向けライブラリです。

- J-Quants API と連携した株価 / 財務 / カレンダーの差分ETL
- RSS を用いたニュース収集と LLM による銘柄毎センチメント算出（ai_scores）
- 市場全体のレジーム判定（ETF とマクロ記事の融合）
- 研究用途のファクター計算・特徴量探索ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → execution）のスキーマ初期化ユーティリティ

設計上の共通方針として「ルックアヘッドバイアスを避ける」「DB への冪等保存」「外部 API はリトライ/バックオフ」「DuckDB ベースのローカルデータ保存」を採用しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ冪等保存: save_daily_quotes, save_financial_statements, save_market_calendar
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果を ETLResult で返却、品質チェックの結果を含む
- ニュース収集・NLP
  - RSS 取得: fetch_rss（SSRF 対策、トラッキングパラメータ除去、gzip対応）
  - ニュースセンチメント: score_news（OpenAI を用いた銘柄ごとのスコアリング）
- 市場レジーム判定
  - score_regime（ETF 1321 の 200 日 MA 乖離 と マクロ記事の LLM センチメントを合成）
- 研究用ユーティリティ
  - calc_momentum / calc_value / calc_volatility（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ（audit）
  - init_audit_schema / init_audit_db（監査用テーブル・インデックスを冪等で作成）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の union 型等を利用）
- Git / OS 標準ツール

例: 仮想環境を作成して必要パッケージをインストールする手順

1. 仮想環境作成・有効化 (例: venv)
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   必要な主な依存（プロジェクトに requirements.txt が無い場合の参考）:
   - duckdb
   - openai
   - defusedxml

   インストール例:
   ```bash
   pip install duckdb openai defusedxml
   ```

3. リポジトリを開発モードでインストール（オプション）
   ```bash
   pip install -e .
   ```

4. 環境変数 (.env) を用意
   プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑止可能）。下記を設定してください（例）:

   .env.example
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   必須環境変数（実行に必要）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - OPENAI_API_KEY: OpenAI API キー（score_news/score_regime 実行時）
   - KABU_API_PASSWORD: kabuステーション API パスワード（運用時）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を行う場合

---

## 使い方（簡単な例）

以下は Python インタラクティブ / スクリプトからの利用例です。DuckDB 接続は `duckdb.connect(path)` で作成します。

- ETL を日次実行する（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数または api_key 引数で指定
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定
```

- 監査ログ DB を初期化（監査専用 DB）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# これで監査テーブルが作成されます
```

- 研究用: モメンタム計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
rows = calc_momentum(conn, target_date=date(2026, 3, 20))
print(rows[:5])
```

- データ品質チェック（ETL 後に呼ぶ）
```python
from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

---

## .env 自動読み込みについて

- パッケージは起動時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、`.env` と `.env.local` を読み込みます。
  - 読み込み優先順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にしたい場合は環境変数を設定:
  ```
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理 (.env 自動ロード)
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュースセンチメント（score_news）
    - regime_detector.py                — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py            — 市場カレンダー管理（is_trading_day 等）
    - etl.py                            — ETL インターフェース再エクスポート
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - stats.py                          — 統計ユーティリティ（zscore_normalize）
    - quality.py                        — データ品質チェック
    - audit.py                          — 監査ログスキーマ初期化
    - jquants_client.py                 — J-Quants API クライアント / 保存処理
    - news_collector.py                 — RSS 収集 / 前処理 / 保存
  - research/
    - __init__.py
    - factor_research.py                — ファクター計算（momentum/value/volatility）
    - feature_exploration.py            — 将来リターン・IC・統計サマリー等
  - research（ユーティリティ読み出しのみ）
  - その他: strategy/ execution/ monitoring 等のパッケージ名が __all__ に含まれるが、
    本コードスニペット範囲では data/research/ai に主に実装があります。

---

## 運用上の注意点

- OpenAI 呼び出しは外部 API のためコストとレート制限に注意してください。API キーは環境変数で管理することを推奨します。
- J-Quants API のレート制限（120 req/min）を守るため内部でレートリミッタを設けていますが、並列実行時はさらに注意してください。
- DuckDB に対する executemany の空リスト渡しや接続のトランザクション取り扱いに制約があるため、関数はこれらに配慮した実装になっています。ETL ロジック等を拡張する際は同様の注意を払ってください。
- 本ライブラリはバックテスト用にルックアヘッドバイアス防止設計（日付条件の排他等）を行っています。バックテストループからの生API呼び出しは避け、事前にデータを取得してから解析してください。

---

## 追加情報 / 貢献

バグ報告や機能追加は issue を利用してください。開発時はユニットテストで API 呼び出し箇所をモックして外部依存を切り離すことを推奨します。

---

以上。README の補足やサンプルスクリプトが必要であれば、どのユースケース（ETL cron スクリプト、news scoring バッチ、監査 DB 初期化など）を優先して欲しいか教えてください。