# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュース収集＆AIによるセンチメント評価、ファクター計算、監査ログなどの機能を提供します。

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 環境変数（.env）一覧（例）
- 使い方（主要API例）
- ディレクトリ構成（要約）
- テスト・開発メモ

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・特徴量（ファクター）計算・AIベースのニュースセンチメント評価・市場レジーム判定・監査ログ管理などを包括的に扱うモジュール群です。  
主に以下用途を想定しています。

- J-Quants API からの株価・財務・カレンダー取得（ETL）
- DuckDB によるローカルデータ保存と品質チェック
- RSS ベースのニュース収集と記事の前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースの銘柄別センチメント評価（ai_score）
- ETF とマクロニュースの組み合わせによる市場レジーム判定
- 研究用途のファクター計算・IC/統計解析
- 取引フローの監査ログ（signal → order_request → executions）

設計上の特徴:
- ルックアヘッドバイアス対策を厳格に実装（target_date に依存する設計）
- DuckDB を中心に SQL と Python 両方で効率的に処理
- 冪等性（ON CONFLICT / INSERT の扱い）やリトライ・レート制御を考慮
- テストしやすい分離（例: OpenAI 呼び出しを差し替え可能）

---

## 主な機能

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・ページネーション・ID トークン自動更新、レートリミット）
  - pipeline / etl: 日次 ETL ワークフロー（calendar, prices, financials）と ETLResult の集約
  - news_collector: RSS 収集・前処理・raw_news への保存（SSRF対策・XMLセーフ）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブルの初期化とユーティリティ（signal, order_request, executions）
  - calendar_management: JPX カレンダー判定（is_trading_day / next_trading_day 等）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを取得して ai_scores に格納
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースを合成して market_regime を生成
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数管理（.env 自動読み込み、Settings クラス）

---

## 前提・依存関係

推奨 Python バージョン: 3.10+（typing の '|' や型注釈が使用されています）

主要依存パッケージ（一例）:
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

（プロジェクトに pyproject.toml / requirements.txt があればそちらを参照してください）

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone <repository-url>

2. Python 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係インストール（例）
   - pip install duckdb openai defusedxml

   プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください:
   - pip install -r requirements.txt
   - あるいは pip install -e .

4. 環境変数設定
   - プロジェクトルートに .env を置くか、OSの環境変数で設定します。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 環境変数（.env）一覧（主なもの・デフォルト）

以下は config.Settings で参照される主なキー（大文字）。デフォルト値がコードに書かれているものは記載しています。

必須（未設定時は ValueError）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン

任意 / デフォルトあり:
- KABU_API_PASSWORD : kabu ステーション API パスワード（必須で使う箇所あり）
- KABU_API_BASE_URL : デフォルト "http://localhost:18080/kabusapi"
- LINE_CHANNEL_ACCESS_TOKEN : LINE 通知用（任意）
- LINE_USER_ID : LINE 通知先ユーザID（任意）
- DUCKDB_PATH : デフォルト "data/kabusys.duckdb"
- SQLITE_PATH : デフォルト "data/monitoring.db"
- PID_FILE_PATH : デフォルト "data/execution.pid"
- KILL_FLAG_PATH : デフォルト "data/kill.flag"
- KILL_FLAG_CLEAR_ON_START : "1" に設定すると起動時に kill flag をクリア
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT : 監視閾値（数値）
- KABUSYS_ENV : "development" | "paper_trading" | "live"（デフォルト "development"）
- LOG_LEVEL : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト "INFO"）
- OPENAI_API_KEY : OpenAI を使う場合はここにキーを指定（score_news / score_regime で使用）

.env 自動読み込みの挙動:
- プロジェクトルート（.git / pyproject.toml を基準）から .env と .env.local を読み込みます。
  - OS 環境変数 > .env.local > .env の優先順
- テスト時などで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要API例）

以下は主要な関数の簡単な利用例です。詳細は各モジュールの docstring を参照してください。

- 共通準備（DuckDB 接続・設定の取得）
```python
from datetime import date
import duckdb
from kabusys.config import settings

# DuckDB 接続（ファイルは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を走らせる（calendar / prices / financials を実行）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを計算して ai_scores テーブルへ保存（OpenAI APIキーは環境変数か引数）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# score_news は api_key を引数で与えることも可能
written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"written: {written} codes")
```

- 市場レジーム判定（ETF 1321 MA とマクロニュース）
```python
from kabusys.ai.regime_detector import score_regime

ret = score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 研究用途（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, target_date=date(2026,3,20))
volatility = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

- 監査ログスキーマを初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# or: init_audit_schema(conn, transactional=True)
```

テスト向けのフック:
- OpenAI API 呼び出しは各モジュール内の _call_openai_api をモック可能（unittest.mock.patch）です。ユニットテストで外部呼び出しを差し替えてください。

---

## ディレクトリ構成（src/kabusys の主要ファイル）

- kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント（score_news）
    - regime_detector.py            -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants APIクライアント + DuckDB 保存
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult エクスポート
    - news_collector.py             -- RSS 収集・前処理
    - quality.py                    -- データ品質チェック
    - calendar_management.py        -- 市場カレンダー管理
    - audit.py                      -- 監査ログスキーマ初期化
    - stats.py                      -- zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py            -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        -- calc_forward_returns / calc_ic / factor_summary / rank
  - monitoring/ (referenced in package __all__ but not listed in provided files)
  - execution/, strategy/, monitoring/ (パッケージ分割想定)

上記ファイル群はそれぞれドキュメント文字列（docstring）で詳細な処理フロー・安全対策・フォールバック挙動を記載しています。実装側での注釈（例: ルックアヘッドバイアス対策、リトライ方針、フェイルセーフ）に注意して利用してください。

---

## テスト・開発メモ

- OpenAI 呼び出しは外部 API を利用するため、ユニットテストでは _call_openai_api をパッチしてレスポンスを模擬することが推奨されます。
- news_collector では SSRF・XML 攻撃対策（_SSRFBlockRedirectHandler / defusedxml）を実装していますが、実運用では外部ネットワーク接続のログ取得・監査も推奨します。
- DuckDB の executemany に対するバージョン差異（空リスト不可など）への対応がコードに含まれています。DuckDB のバージョンに注意してください。
- ETL は部分失敗時も他ステップを継続する設計です。ETLResult の errors / quality_issues をチェックして運用判断を行ってください。

---

README に書かれている使い方はコード上の docstring に基づいています。より詳細な API 仕様や運用手順は各モジュールの docstring を参照してください（例: kabusys/data/jquants_client.py、kabusys/ai/news_nlp.py、kabusys/research/*）。問題や追加のドキュメントが必要であれば教えてください。