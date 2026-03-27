# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログなどの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API を使った株価・財務・カレンダー等の差分取得（Rate limit・リトライ・ページネーション対応）
- DuckDB を用いたデータ格納と ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去・容量制限）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 / マクロ）
- 市場レジーム判定（ETF + マクロニュースの合成）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）

設計上の共通方針として、バックテストやモデル評価でのルックアヘッドバイアスを避けるため「現在時刻参照を直接行わない」などの配慮がされています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl）
  - J-Quants クライアント（認証・ページネーション・保存用関数）
  - ニュース収集（RSS, トラッキング除去, SS R F 対策）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - マーケットカレンダー管理（営業日判定、next/prev trading day）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースで市況レジーム判定
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings: 環境変数から各種設定を参照（.env 自動ロード機能あり）

---

## 必要条件 / 依存関係

- Python 3.10+（Union 型記法 Path | None 等を使用）
- 主要ライブラリ（例）
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
- ネットワークアクセス: J-Quants API / RSS / OpenAI（必要に応じて）

pip でのインストール例（開発時）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発リポジトリであれば:
pip install -e .
```

（実際のパッケージ化で依存リストは pyproject.toml / setup.cfg に記載してください）

---

## 環境変数 / 設定

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY (必須 for AI 関数実行)  
  OpenAI API キー（ai.score_news / regime_detector で使用）
- KABU_API_PASSWORD  
  kabuステーション API パスワード（実取引・発注関連で使用）
- KABUSYS_ENV (任意, default: development)  
  有効値: "development", "paper_trading", "live"
- LOG_LEVEL (任意, default: INFO)  
  有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (任意: モニタリング通知用)
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)
- SQLITE_PATH (任意, default: data/monitoring.db)

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を自動で読み込みます。
- 優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡易 .env 例 (.env.example 参考):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（概要）

1. Python 仮想環境を作成・有効化
2. 依存パッケージをインストール（duckdb, openai, defusedxml など）
3. プロジェクトルートに `.env` を作成し必要な環境変数を設定
4. DuckDB 用ディレクトリ（デフォルト: data/）を作成（必要に応じて）
5. 必要な初期化（監査 DB を使う場合は init_audit_db を実行してスキーマ作成）

例:
```python
from pathlib import Path
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# DuckDB の接続を得る（ファイルがなければ作成）
db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))

# 監査テーブルを初期化（任意）
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

または監査専用 DB を作る:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

---

## 使い方（代表的な例）

- 日次 ETL を実行する（ETL は差分取得・保存・品質チェックを行う）:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を評価して ai_scores テーブルに書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # API キーは OPENAI_API_KEY 環境変数から取得
print(f"scored {count} codes")
```

- 市場レジームスコアを算出して market_regime テーブルに書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

- ETL の結果確認（ETLResult）:
```python
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn)
if res.has_errors:
    # ログやメール通知などの処理
    pass
```

注意点:
- OpenAI 呼び出しは外部 API のため API キーや利用料金、レート制限に注意してください。ライブラリはリトライや JSON mode を利用する実装です。
- DuckDB の `executemany` は空リストを渡せない箇所があるため内部で保護されています。API の呼び出し側で特別対応は不要です。

---

## ディレクトリ構成（主要ファイル）

（リポジトリのルートが `pyproject.toml` / `.git` を含む想定）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                   -- 銘柄別ニューススコアリング（score_news）
    - regime_detector.py            -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch / save）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult の再公開
    - news_collector.py             -- RSS 収集・前処理（fetch_rss 等）
    - calendar_management.py        -- マーケットカレンダー管理（is_trading_day 等）
    - quality.py                    -- データ品質チェック
    - stats.py                      -- zscore_normalize 等
    - audit.py                      -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py            -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        -- calc_forward_returns / calc_ic / factor_summary / rank
  - research/（その他）...
  - (その他のモジュール: strategy, execution, monitoring 等は __all__ に含まれるが本リストにない場合があります)

---

## 実運用上の注意 / ベストプラクティス

- 環境分離:
  - 本番（live）とペーパー（paper_trading）を環境変数 `KABUSYS_ENV` で切り替え、実取引パスワードや通知先を分けてください。
- シークレット管理:
  - API キーやパスワードは環境変数やシークレット管理サービスで保管し、リポジトリに直書きしないでください。
- ロギングと監視:
  - LOG_LEVEL や Slack 通知を活用して ETL や AI 呼び出しの失敗を監視してください。
- テストとモック:
  - ai モジュールは OpenAI 呼び出し部をモックできる設計です（内部関数を patch 可能）。ユニットテストでは外部 API 呼び出しをモックしてください。
- DB バックアップ:
  - DuckDB ファイルは適切にバックアップしてください。監査ログは削除前提ではないためサイズや保持方針を検討してください。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンスやコントリビュート手順を記載してください。例: MIT, 開発ガイドライン, コードスタイル, テストカバレッジ要件 等）

---

この README はコードベース（src/kabusys 以下）から主要な機能と使い方を抜粋して作成しています。詳細な API や追加のユーティリティは各モジュールの docstring を参照してください。必要であれば具体的な使用例や運用手順（systemd ジョブ, cron, Airflow など）を追記します。