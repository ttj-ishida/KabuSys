# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買ユーティリティ群。  
DuckDB をデータストアに用い、J-Quants / RSS / OpenAI 等と連携してデータ収集・品質チェック・ファクター計算・AI ベースのニュース評価・市場レジーム判定・監査ログを提供します。

## 主な特徴（機能一覧）
- データ収集（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダーの差分取得（ページネーション対応）
  - レート制御・再試行・トークン自動リフレッシュを備えたクライアント
- ETL パイプライン
  - 差分取得・冪等保存（DuckDB）・品質チェックを統合した日次 ETL（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue を返す）
- ニュース収集・前処理
  - RSS 取得、URL 正規化、SSRF 防止、トラッキングパラメータ除去、raw_news 保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM（gpt-4o-mini を想定）で評価して ai_scores へ格納（score_news）
- 市場レジーム判定（AI + テクニカル）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定・保存（score_regime）
- 研究用ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算、将来リターン、IC（Spearman）、Z スコア正規化等
- 監査ログ（トレーサビリティ）
  - シグナル→発注→約定まで UUID による追跡ができる監査テーブル初期化・専用 DB 関数（init_audit_db）を提供
- カレンダー管理
  - market_calendar に基づく営業日判定・前後営業日の取得・夜間カレンダー更新ジョブ

---

## 必要条件（主な依存）
- Python 3.9+
- duckdb
- openai (OpenAI Python SDK、gpt-4o-mini 等を利用する場合)
- defusedxml
- （標準ライブラリ多数: urllib, datetime, json など）

実行環境によっては追加のパッケージが必要になる場合があります。

---

## 環境変数（主要）
アプリ設定は環境変数（またはプロジェクトルートの .env / .env.local）から読み込まれます。自動読み込みはデフォルトで有効です。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（アプリの主要機能を使う際）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（自動売買機能利用時）
- SLACK_BOT_TOKEN — Slack 通知（必要に応じて）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime を使う場合）

任意・デフォルトあり:
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — ログレベル: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動ロードを無効化

.env 形式はシェルの export 付き行やクォート、コメント（#）に対応するカスタムパーサを用いて読み込まれます。

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo_url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. パッケージをインストール
   - pip install -U pip
   - pip install -e .            # パッケージが setuptools/pyproject に対応していれば開発インストール
   - pip install duckdb openai defusedxml
   - （その他必要なパッケージがあれば追加で pip install）
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートしてください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=xxx
     SLACK_CHANNEL_ID=xxx
5. DuckDB 用ディレクトリを作成（必要なら）
   - mkdir -p data

---

## 基本的な使い方（コード例）

ここでは主要なユースケースの最小例を示します。実行前に環境変数を適切に設定してください。

- DuckDB 接続の作成（監査 DB 初期化も含む）
```python
import duckdb
from pathlib import Path
from kabusys.data.audit import init_audit_db

# ファイル DB を作る場合
db_path = Path("data/kabusys_audit.duckdb")
conn = init_audit_db(db_path)  # 監査スキーマ初期化済み接続を返す

# あるいは通常の DuckDB 接続を直接使う
conn2 = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# conn は duckdb.DuckDBPyConnection
result = run_daily_etl(conn2, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
n_written = score_news(conn2, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（OpenAI 必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn2, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn2, target_date=date(2026, 3, 20))
vals = calc_value(conn2, target_date=date(2026, 3, 20))
vols = calc_volatility(conn2, target_date=date(2026, 3, 20))
```

- 監査テーブルの初期化（既存接続にスキーマ追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn2, transactional=True)
```

---

## 自動環境読み込みの挙動
パッケージの起動時（kabusys.config モジュール）はプロジェクトルート（.git または pyproject.toml を探索）を基に `.env` → `.env.local` の順で読み込みます。OS 環境変数が優先され、`.env.local` は上書きで適用されます。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要モジュールと概要です（抜粋）。

- src/kabusys/
  - __init__.py                — パッケージ初期化、バージョン管理
  - config.py                  — 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult の再エクスポート
    - jquants_client.py        — J-Quants API クライアント（fetch/save 系）
    - news_collector.py        — RSS ニュース収集・前処理
    - calendar_management.py   — 市場カレンダー管理・営業日ロジック
    - quality.py               — データ品質チェック
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                 — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py       — Momentum / Value / Volatility 等
    - feature_exploration.py   — 将来リターン・IC・統計サマリー
  - ai/__init__.py
  - research/__init__.py

（上のファイル群は README 作成時点の主要実装を反映しています）

---

## 運用上の注意
- OpenAI 呼び出しはコストとレート制限を伴います。商用環境では API キー管理やレート制御、リクエストバッチサイズの調整に注意してください。
- DuckDB に対する executemany の空リスト渡しは一部バージョンで問題があるためライブラリ内で保護処理があります。DB 操作時には例外ハンドリングを行ってください。
- ETL と品質チェックは個別にエラーハンドリングされ、1 ステップの失敗で全体が停止しない設計です。ただし重要な品質エラーはログおよび戻り値で通知されます。
- production 環境では KABUSYS_ENV を適切に設定し（例: live）、ログレベル・Slack 通知等で監視を行ってください。

---

## 参考
- 環境変数と .env の読み込み仕様は `kabusys.config` を参照してください。
- J-Quants API の使用方法・フィールドマッピングは `kabusys.data.jquants_client` にドキュメント化されています。
- LLM への入力／レスポンス処理の仕様（JSON Mode 期待・レスポンスバリデーション等）は `kabusys.ai.news_nlp` / `kabusys.ai.regime_detector` を参照してください。

---

追加で README に入れたい実行例や CI／デプロイ手順、ライセンス情報などがあれば教えてください。必要に応じてサンプル .env.example も作成します。