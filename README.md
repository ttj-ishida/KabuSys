# KabuSys

日本株向け自動売買・データ基盤ライブラリ

KabuSys は日本株のデータ取得・品質チェック・特徴量生成・ニュース NLP・市場レジーム判定・監査ログなどを含む内部ライブラリ群です。ETL パイプライン、AI を使ったニュースセンチメント、研究用ファクター集計、監査テーブル初期化など、量的リサーチと自動売買システムの基盤機能を提供します。

---

## 目次

- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数（重要）
- ディレクトリ構成
- 開発・テストに関するメモ

---

## プロジェクト概要

本コードベースは次の責務を持つモジュール群で構成されています。

- データ取得（J-Quants API 経由）と DuckDB への保存（ETL）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 市場カレンダー管理（JPX カレンダー）
- ニュース収集（RSS）とニュースセンチメント（OpenAI）
- 市場レジーム判定（ETF とマクロニュースの組成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算）
- 監査ログ（シグナル→発注→約定のトレーサビリティを担保する DuckDB スキーマ）

設計上の共通方針として、バックテストや運用でのルックアヘッドバイアス防止、冪等性（INSERT … ON CONFLICT）、外部 API のリトライ・レート制御、フェイルセーフ（API 失敗時の安全動作）等が意識されています。

---

## 主な機能一覧

- ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- J-Quants API クライアント（fetch_*/save_*）
- ニュース収集（RSS → raw_news、news_symbols）
- ニュース NLP（score_news: OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（score_regime: ETF ma200 とマクロセンチメントの合成）
- 研究用ファクター（calc_momentum / calc_value / calc_volatility 等）
- 統計ユーティリティ（zscore_normalize 等）
- データ品質チェック（run_all_checks）
- 監査ログ初期化（init_audit_db / init_audit_schema）
- カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）

---

## 必要条件

- Python 3.10 以上（PEP 604 の型表記（|）を使用）
- 主な依存パッケージ（少なくとも以下が必要）
  - duckdb
  - openai
  - defusedxml

※ 実行環境や CI 用に requirements.txt を用意してください。最小インストール例は下記参照。

---

## セットアップ手順

1. リポジトリをクローン／コピー
2. 仮想環境を作成・有効化（任意）
   - macOS / Linux:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトで requirements.txt を用意している場合は `pip install -r requirements.txt`）

4. 環境変数ファイルを作成
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` と `.env.local`（任意）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
   - 必須項目は後述の「環境変数」セクションを参照してください。

5. DuckDB（監査DB等）のディレクトリを準備
   - デフォルトの duckdb ファイルは `data/kabusys.duckdb`（settings.duckdb_path）です。ディレクトリがなければ自動作成される処理が一部に存在しますが、権限を確認してください。

---

## 環境変数（設定項目）

設定は `.env` または OS 環境変数から読み込まれ、`kabusys.config.settings` 経由で参照します。自動ロード順序は OS 環境変数 > .env.local > .env （.env.local が .env を上書き）です。OS 環境変数にあるキーは保護され、.env から上書きされません。

主な設定キー:

- JQUANTS_REFRESH_TOKEN  … J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD      … kabuステーション API パスワード（必須）
- KABU_API_BASE_URL      … kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        … Slack Bot Token（必須）
- SLACK_CHANNEL_ID       … Slack Channel ID（必須）
- DUCKDB_PATH            … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            … SQLite ファイルパス（監視用、デフォルト: data/monitoring.db）
- OPENAI_API_KEY         … OpenAI API キー（score_news / score_regime で未指定時に参照）
- KABUSYS_ENV            … 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL              … ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

注意: `kabusys.config.Settings` のプロパティは不足時に ValueError を投げるものがあります（必須設定）。

---

## 使い方（簡易サンプル）

以下は基本的な利用例です。すべて Python からの呼び出し例です。

- DuckDB 接続と ETL 実行例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 監査 DB 初期化:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの duckdb 接続
```

- ニュースセンチメントスコア（OpenAI 必須）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# 環境変数 OPENAI_API_KEY が設定されているか、api_key を渡す
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

注意:
- OpenAI 呼び出しは `openai.OpenAI` クライアントを内部で生成します。テストでは内部の `_call_openai_api` をモック可能です（unittest.mock.patch を利用）。
- API キーは関数引数で渡すことも、環境変数 `OPENAI_API_KEY` を使うこともできます。

---

## 主要な API（抜粋）

- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL（カレンダー→価格→財務→品質チェック）
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes — J-Quants からの取得・保存
- kabusys.data.quality.run_all_checks — データ品質チェック実行
- kabusys.data.news_collector.fetch_rss — RSS 取得（内部的に raw_news へ保存するラッパーあり）
- kabusys.ai.news_nlp.score_news — ニュースセンチメントを ai_scores に書込
- kabusys.ai.regime_detector.score_regime — 日次市場レジーム判定を market_regime に書込
- kabusys.data.audit.init_audit_db — 監査 DB 初期化（テーブル・インデックス作成）

各関数・モジュール内に docstring が充実していますので、IDE の補完や help() を参照してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）:

- src/
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
      - stats.py
      - quality.py
      - audit.py
      - etl.py (export)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (監視関連モジュールが想定されるディレクトリ)
    - strategy/ (戦略レイヤー向けモジュールが想定されるディレクトリ)
    - execution/ (実際の発注・ブローカー連携向けモジュールが想定されるディレクトリ)
    - monitoring/ (監視向け DB/サービス連携)
- pyproject.toml (プロジェクトルートを判定するために利用される)
- .env.example（プロジェクトルートに置くことが想定されるサンプル）

---

## 開発・テストに関するメモ

- 自動で .env を読み込む挙動は、kabusys.config モジュールがプロジェクトルート（.git か pyproject.toml）を探して `.env` / `.env.local` を読み込みます。テスト中などで自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し・外部 HTTP 呼び出しはリトライ処理やレート制御が入っていますが、ユニットテストでは外部依存をモック（特に _call_openai_api, _urlopen, jquants_client._request 等）することを推奨します。
- DuckDB の一部操作（executemany の空リスト渡し等）はバージョン依存の注意があるため、本リポジトリは互換性を意識した実装になっています。DuckDB のバージョンはプロジェクトの CI 設定に合わせて揃えてください。
- ニュース収集モジュールは SSRF対策（リダイレクト先検査、プライベート IP 拒否）、XML パースの安全化（defusedxml）などセキュリティ面の実装が含まれます。

---

この README はコードの主要な利用方法と設計上の注意点をまとめたものです。各モジュールの詳細な API や引数・戻り値はソースコードの docstring を参照してください。必要であれば README を拡張して、デプロイ手順・運用手順・監視設定・Slack 通知フローなどを追記します。