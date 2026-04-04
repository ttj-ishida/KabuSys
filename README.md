# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株向けのデータパイプライン、リサーチ、AI ベースのニューススコアリング、監査ログ、ETL といった機能を備えた自動売買システムのライブラリ群です。本リポジトリは主にデータ取得・整備・品質チェック、特徴量計算、ニュースセンチメント評価、及び市場レジーム判定までを含み、実運用またはリサーチ用途に利用できます。

注意: 本 README はソースコード（src/kabusys 以下）の実装を元に記載しています。実際に取引を行う部分（発注ロジック等）は含まれていないか、別モジュールで実装する想定です。バックテストや本番運用時は必ず十分な検証を行ってください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 環境変数（.env）
- 使い方（サンプル）
- ディレクトリ構成
- 補足・注意点

---

## プロジェクト概要

KabuSys は以下のコンポーネントを持つ Python モジュール群です。

- data: J-Quants API 経由のデータ取得（株価・財務・マーケットカレンダー）、ETL パイプライン、品質チェック、ニュース収集、監査ログなど
- research: ファクター計算・特徴量探索ユーティリティ（モメンタム、ボラティリティ、バリュー、IC 等）
- ai: ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコアリング）と市場レジーム判定（ETF の MA とマクロニュースの合成）
- config: 環境変数管理（.env 自動読み込み機能、必須値チェック）
- その他: 監視・実行周りの設定等

設計上のポイント:
- ルックアヘッドバイアスに配慮（内部で date.today()/datetime.today() を盲目的に使わない実装）
- DuckDB を用いたローカルデータストア（高速な列指向クエリ）
- OpenAI（gpt-4o-mini）による JSON Mode を利用したセンチメント評価（JSONレスポンスの検証・リトライを実装）
- J-Quants API のレート制御・トークン自動リフレッシュ・リトライ実装

---

## 主な機能一覧

- ETL パイプライン（data.pipeline.run_daily_etl）
  - 市場カレンダー、株価日足、財務データの差分取得と保存
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- J-Quants クライアント（data.jquants_client）
  - fetch/save の整備（pagination, rate limiting, token refresh）
- ニュース収集（data.news_collector）
  - RSS 取得、SSRF 対策、トラッキングパラメータ除去、記事正規化、raw_news 保存
- ニュース NLP（ai.news_nlp.score_news）
  - 銘柄ごとに記事をまとめて OpenAI に送信し ai_scores に保存
- 市場レジーム判定（ai.regime_detector.score_regime）
  - ETF 1321 の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して market_regime に書き込み
- 監査ログ（data.audit.init_audit_db / init_audit_schema）
  - signal_events, order_requests, executions テーブルを含む監査スキーマの初期化
- 研究ユーティリティ（research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / zscore_normalize

---

## セットアップ手順

以下は開発環境・実行環境の最低限の手順例です。プロジェクトに requirements.txt や pyproject.toml がある場合はそちらに従ってください。

1. リポジトリをクローン
   ```
   git clone <this-repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成（推奨: Python 3.10+）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（最低限の依存）
   ```
   pip install duckdb openai defusedxml
   ```
   実運用では追加のログ管理や HTTP ライブラリ、テスト用パッケージ等が必要になる場合があります。プロジェクトの pyproject.toml / requirements.txt があればそれを使用してください。

4. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。
   - 必須環境変数や推奨変数は次節参照。

---

## 環境変数（主なキー）

config.Settings に定義されている主なキー：

- J-Quants（必須）
  - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（settings.jquants_refresh_token が参照）

- kabuステーション API
  - KABU_API_PASSWORD: kabu API パスワード
  - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"

- OpenAI / AI
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime のデフォルト）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）

- DB / ファイルパス（デフォルト有り）
  - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH: デフォルト "data/monitoring.db"
  - PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定

- 動作モード / ログ
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト "development"）
  - LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）

.env の読み込みルールの要点:
- プロジェクトルートは .git または pyproject.toml を基準に自動検出
- 読み込み順序: OS 環境 > .env.local > .env（.env.local は .env を上書き）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能

例（.env の最小例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要機能のサンプル）

以下は Python REPL やスクリプトからの利用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を開く（デフォルトパスを settings から取得）
```python
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# 例: 2026-03-20 の ETL を実行
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニューススコアリング（ai.news_nlp）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数で設定しておくか、api_key 引数で渡す
n = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定（ai.regime_detector）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境変数に設定
```

- 監査ログ用 DB 初期化（独立 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
```

- J-Quants から株価を直接取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
saved = save_daily_quotes(conn, records)
print(saved)
```

ログレベルの調整や監視フラグ、kill flag の挙動などは config.Settings のプロパティに従います。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル・モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py        -- ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py -- マーケットレジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch/save）
    - pipeline.py            -- ETL 実行 (run_daily_etl, run_prices_etl, ...)
    - quality.py             -- データ品質チェック（欠損・スパイク等）
    - news_collector.py      -- RSS ニュース収集、SSRF 対策
    - calendar_management.py -- 市場カレンダー管理・営業日判定
    - stats.py               -- 汎用統計ユーティリティ（zscore_normalize など）
    - audit.py               -- 監査ログスキーマ初期化
    - etl.py                 -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム/バリュー/ボラティリティ算出
    - feature_exploration.py -- 将来リターン・IC・統計要約
  - monitoring/ (記載はヘッダのみ、実装は別ファイルにある想定)
  - strategy/, execution/ 等（上位モジュールとしてエクスポーズ予定）

---

## 補足・注意点

- OpenAI の呼び出しや外部 API 呼び出しにはコストとレート制限があります。開発中はトークンや API 呼び出しの取り扱いに注意してください。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に探索します。CI/テスト環境で挙動をコントロールしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。
- DuckDB の executemany に空リストを与えるとエラーになるバージョンがあるため、save 等の実装では空チェックを行っています。ローカル DB バージョンに依存する挙動に注意してください。
- 本ライブラリはプロダクション運用を想定した堅牢性（リトライ、トランザクション管理、冪等性、ログ）を備えていますが、実際の売買ロジック・資金管理・リスク制御は別途実装して下さい。
- 各モジュール内に詳細な docstring（日本語）が記載されています。実装や挙動を確認する場合は該当ファイルを参照してください。

---

この README は実装ファイルのコメント・docstring を元に作成しています。追加で「セットアップ用のスクリプト」「requirements.txt」「実行用 CLI」「テストケース」などが必要であれば、目的に応じて追記案を提示できます。必要であれば教えてください。