# KabuSys

日本株自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）→ データ品質チェック → ファクター計算 → ニュース NLP / レジーム判定 → 監査ログ管理、というワークフローを提供します。

概要、機能、セットアップ手順、使い方、ディレクトリ構成を以下にまとめます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム／研究プラットフォーム向けの共通ユーティリティ群です。主な役割は次のとおりです。

- J-Quants API からのデータ ETL（株価日足 / 財務 / 市場カレンダー）
- raw データの品質チェック（欠損・スパイク・重複・日付整合性）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）
- ニュース収集と LLM による銘柄別センチメント解析
- 市場レジーム判定（ETF MA と LLM によるマクロセンチメントの合成）
- 監査テーブル（シグナル → 発注 → 約定）初期化ユーティリティ
- 環境変数 / 設定の読み込みを容易にする設定モジュール

設計上の特徴：
- DuckDB を中心としたローカル DB により再現性ある ETL と解析を実行
- Look-ahead bias を避けるため、日時の扱いとデータ選択に注意
- API 呼び出しはリトライ・レートリミット・フェイルセーフ実装
- LLM 呼び出しは JSON Mode を想定し、レスポンス検証を行う

---

## 主な機能一覧

- data:
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day など）
  - ニュース収集（RSS）と前処理
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査（audit）スキーマ初期化ユーティリティ

- ai:
  - news_nlp.score_news: 指定ウィンドウのニュースをまとめて LLM で銘柄ごとのセンチメントを算出し ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ保存

- research:
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize

- config:
  - Settings クラスを介した環境変数読み取り、自動 .env ロード機能（プロジェクトルートから .env / .env.local を自動読み込み）

---

## 必要条件 / 依存

- Python 3.10 以上（| 型や union 構文を利用しているため）
- 必要なライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ: urllib, json, datetime, logging 等）

インストール例（仮）:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
# またはプロジェクト配布形式があれば:
# pip install -e .
```

※ 実行環境に合わせて requirements.txt / pyproject.toml からインストールしてください。

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local`（優先度: OS 環境 > .env.local > .env）から読み込まれます。自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト時に有用）。

主な環境変数（必須項目はライブラリが ValueError を投げます）:

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時に必要）
- DUCKDB_PATH: DuckDB データベースファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

設定参照例:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン / ダウンロード
2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトで requirements / pyproject があればそちらを使用）

4. .env を作成（.env.example を参考に必要な環境変数を設定）
   - JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など

5. DuckDB データベースの格納ディレクトリ作成（デフォルト: data/）
   ```bash
   mkdir -p data
   ```

6. 監査用 DB を初期化する（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な API）

以下はライブラリの代表的な使い方です。関数は DuckDB 接続（duckdb.connect(...) が返す接続オブジェクト）を受け取ることが多いです。

- DuckDB 接続の作成:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ":memory:" も可
```

- 日次 ETL を実行（市場カレンダー取得 → 株価・財務 ETL → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 単体で株価 ETL を実行
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

- ニュース NLP による銘柄スコアの算出（LLM を使用）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY を環境変数に設定しているか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

- 統計正規化ユーティリティ
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
```

- 監査テーブルの初期化（既存接続に対して）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意:
- news_nlp.score_news / regime_detector.score_regime は OpenAI API キーが必要です。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。未設定の場合 ValueError が発生します。
- J-Quants の取得は JQUANTS_REFRESH_TOKEN が必須です。settings.jquants_refresh_token を参照して自動的に取得します。

---

## よくあるトラブルと対処

- ValueError: "OpenAI API キーが未設定です"  
  → OPENAI_API_KEY が未設定。環境変数か関数引数で指定してください。

- ValueError: "環境変数 'XXXX' が設定されていません"  
  → 必須の環境変数が不足しています。`.env.example` を参考に .env を用意してください。

- ネットワーク/API の一時エラー  
  → モジュールはリトライ/バックオフ実装を持ちますが、継続的に失敗する場合はネットワーク設定や API トークンの有効性を確認してください。

- DuckDB の executemany に関する問題  
  → 一部の DuckDB では executemany に空リストを渡すとエラーになるため本ライブラリは事前チェックを行っています。自前で呼ぶ場合も空チェックを行ってください。

---

## ディレクトリ構成

主要なファイル / モジュール構成（src/kabusys 以下を抜粋）:

- kabusys/
  - __init__.py
  - config.py                 -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             -- ニュース NLP スコアリング（score_news）
    - regime_detector.py      -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント、fetch/save
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - quality.py              -- データ品質チェック
    - stats.py                -- 汎用統計ユーティリティ（zscore_normalize）
    - calendar_management.py  -- 市場カレンダー管理（is_trading_day 等）
    - news_collector.py       -- RSS ベースのニュース収集
    - audit.py                -- 監査テーブル定義・初期化
    - etl.py                  -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py      -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py  -- 将来リターン／IC／統計サマリー等

各モジュールはドキュメント文字列とログ出力を備え、DuckDB 上の定義済みテーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, signal_events, order_requests, executions など）を前提に動作します。

---

## 開発者向けメモ

- config._find_project_root() は .git または pyproject.toml を基準にプロジェクトルートを検出し、自動で .env を読み込みます。テスト等で自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- LLM 呼び出し部分はテスト容易性を考慮して内部呼び出し（_call_openai_api 等）をモック可能に実装しています。
- DuckDB への書き込みは冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を考慮しています。
- 時刻や日付に関する実装は look-ahead bias を避けるため date / datetime の扱いが慎重に設計されています（内部で datetime.today() を直接参照しない等）。

---

もし README に追加したい使い方のサンプルや、具体的な .env.example のテンプレート、またはセットアップスクリプト（requirements.txt / pyproject.toml の整備）が必要でしたら教えてください。