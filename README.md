# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ（軽量モジュール群）

このリポジトリは、J-Quants からのデータ ETL、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、カレンダー管理、監査ログ（発注〜約定トレーサビリティ）など、日本株の自動売買システムでよく使う機能群を提供します。

---

## 主な概要

- データ取得・保存（J-Quants API）と差分 ETL（DuckDB）
- ニュースの収集と前処理（RSS）、LLM を使ったニュースセンチメント評価
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量解析ユーティリティ
- 市場カレンダー管理（JPX）、営業日判定ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions）用のスキーマ初期化・ヘルパー

---

## 機能一覧（抜粋）

- kabusys.config
  - .env/.env.local の自動読み込み（プロジェクトルートを探索）
  - 必須設定の取得（JQUANTS_REFRESH_TOKEN 等）
  - 環境判定（development / paper_trading / live）やログレベル取得

- kabusys.data
  - jquants_client: J-Quants API からの取得（株価、財務、カレンダー）、DuckDB へ冪等保存
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL（run_prices_etl 等）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック
  - calendar_management: 営業日判定 / next/prev/get_trading_days / calendar_update_job
  - quality: データ品質チェック群（欠損・スパイク・重複・日付）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize などの統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores に書き込み
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロセンチメントを合成して market_regime に書き込み

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 必要条件 / 依存関係

- Python 3.10 以上（PEP 604 の `X | Y` 型などを使用）
- 実行に必要な主なパッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK v1系想定)
  - defusedxml
- そのほか標準ライブラリのみで動作するモジュールも多く、外部 HTTP は urllib を使用します。

例: 簡易インストール（仮想環境推奨）
```bash
python -m venv .venv
source .venv/bin/activate
pip install "duckdb" "openai" "defusedxml"
# 必要であればその他のパッケージを追加
```

---

## 環境変数（主要項目）

設定は .env / .env.local / OS 環境変数から読み込まれます。プロジェクトルート（.git または pyproject.toml を探索）にある .env を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（README 用抜粋）:

- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token（get_id_token に利用）
- OpenAI / LLM
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime のデフォルト）
- kabu ステーション API（運用系）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE 通知（オプション）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 実行監視
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT など
- システム
  - KABUSYS_ENV (development | paper_trading | live) — 動作モード
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-xxxxxxxx
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 環境を準備（3.10+）
2. 依存パッケージをインストール
   - duckdb, openai, defusedxml など
3. プロジェクトルートに `.env`（または `.env.local`）を作成して上記環境変数を設定
4. ディレクトリ `data/` を作成（デフォルト DB ファイル用）
   ```bash
   mkdir -p data
   ```
5. DuckDB を使う場合は必要に応じて初期スキーマを用意（audit 用はライブラリが初期化可能）
   - 監査 DB を分けて使う場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマを追加:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（サンプル）

以下は代表的な呼び出し例です。実行時には必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を用意してください。

- DuckDB 接続を作って ETL を実行（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI を使用）
```python
import duckdb, os
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定している場合、api_key は None で OK
written = score_news(conn, target_date=date(2026, 3, 20), api_key=os.getenv("OPENAI_API_KEY"))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
```

- ファクター計算 / 研究ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

- ニュース収集（RSS）例
  - RSS の取得と前処理は `kabusys.data.news_collector.fetch_rss` を利用します。取得した記事は DB に保存するロジック（raw_news への保存）を本プロジェクトの ETL 内で使う前提です。

---

## 注意点 / 実運用における留意点

- Look-ahead-bias の回避設計が随所に組み込まれています（target_date 未満のみ参照する、取得日時を fetched_at で記録する、など）。
- OpenAI 呼び出しはリトライ・バックオフやレスポンスバリデーションが入っていますが、API コストとレート制限に注意してください。
- J-Quants API のレート制限（120 req/min）に対応するレートリミッタを実装していますが、運用時は ID トークンや API の仕様変更に注意が必要です。
- .env 自動ロードはプロジェクトルート検出に依存します。自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のバージョンによっては executemany の挙動に差があるため、コードに互換性処理が入っています（例: 空リストの executemany を避ける等）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースの LLM スコアリング（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント & DuckDB への保存
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult の再エクスポート
    - news_collector.py      -- RSS 収集・前処理
    - calendar_management.py -- 市場カレンダー管理 / 営業日ユーティリティ
    - quality.py             -- データ品質チェック
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - audit.py               -- 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py     -- calc_momentum, calc_value, calc_volatility
    - feature_exploration.py -- calc_forward_returns, calc_ic, factor_summary, rank
  - monitoring/ (存在する場合は監視系モジュール)
  - strategy/ (戦略層は別途実装想定)
  - execution/ (発注実行・ブローカー連携は別途実装想定)

---

## 追加情報 / 開発メモ

- テスト時には環境変数の自動ロードを無効化したいケースがあります。その場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の呼び出し（_call_openai_api）はモジュール内で定義されており、ユニットテスト時はパッチして差し替えられるようになっています。
- DuckDB のタイムゾーンは監査スキーマ初期化時に UTC に固定します（`SET TimeZone='UTC'`）。
- ETL の戻り値は ETLResult（dataclass）で、to_dict() により品質チェック結果やエラー情報を含めた辞書化が可能です。

---

必要ならば、README に含めるサンプル .env.example、さらに詳しい API 使用例（関数ごとの引数説明）やスキーマ定義（DDL）の抜粋も追加できます。どうしますか？