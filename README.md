# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・LLM によるニュースセンチメント、ファクター計算、監査ログ（トレーサビリティ）、マーケットカレンダー管理などを提供します。

---

## 概要

KabuSys は日本株のデータ取得・品質管理・リサーチ・戦略実行までの基本機能をまとめたライブラリです。  
主に以下の領域をカバーします。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（duckdb に保存）
- RSS ベースのニュース収集と前処理（raw_news 保存）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / 市場レジーム判定
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算、特徴量探索ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions の追跡用テーブル）
- JPX マーケットカレンダーの管理と 営業日判定ロジック
- Paper Trading 用設定（モック執行動作など）

パッケージは標準ライブラリと最小限の外部依存で動作するよう設計されています（一部機能は外部ライブラリを必要とします）。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants からのデータ取得（株価・財務・カレンダー）と DuckDB への保存（冪等）
  - pipeline: 日次 ETL のエントリポイント（run_daily_etl 等）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 収集、記事前処理、raw_news への保存
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - audit: 監査ログスキーマ初期化・監査用 DB ユーティリティ
  - stats: 汎用統計（Zスコア正規化など）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュース（LLM）の合成で市場レジーム判定
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数読み込み・設定ラッパ（自動 .env 読み込み、Settings オブジェクト）
- 実行周り（監視・実行）は別モジュール（execution / monitoring 等）を想定（__all__ に公開）

---

## セットアップ手順（開発向け）

前提
- Python 3.10 以上（型注釈に `X | None` などを使用）
- Git が使える環境（自動 .env ロードはプロジェクトルート検出で .git や pyproject.toml を参照します）

手順（例）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - 最低限必要なパッケージ例:
     - duckdb
     - openai
     - defusedxml
   - pip install duckdb openai defusedxml
   - （実際のプロジェクトでは requirements.txt を用意している場合はそれを使用してください）

4. 環境変数設定
   - プロジェクトルート（.git か pyproject.toml のあるディレクトリ）に `.env` と `.env.local` を置くことができます。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（またはよく使う）環境変数（概要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携など）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / score_regime を実行する場合）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- KABUSYS_ENV: 実行環境 ("development", "paper_trading", "live")（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB 等（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper trading の fill 動作（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite のパス（デフォルト: data/paper_trading.db）

※ .env.example を参考に .env を作成することを推奨（リポジトリにある場合）。

---

## 使い方（簡単な例）

以下はライブラリ API を直接使う例です。実際の運用では各関数をスケジューラやワーカーから呼び出します。

- DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

# ファイルパスは settings.duckdb_path により管理
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）スコア生成
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n_written} codes")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用データベース初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル（signal_events, order_requests, executions 等）が作られます
```

---

## 自動 .env ロードの挙動

- パッケージはインポート時にプロジェクトルート（__file__ の親階層で .git または pyproject.toml を探索）を探し、見つかれば `.env` を読み込む仕組みがあります。
- 読み込み順:
  1. OS の環境変数
  2. .env（プロジェクトルート）
  3. .env.local（存在すれば .env の上書き）
- `.env.local` の値は .env より優先されますが、OS 環境変数は常に最優先です。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

.env に含める代表的なキー（例）
- JQUANTS_REFRESH_TOKEN=
- KABU_API_PASSWORD=
- OPENAI_API_KEY=
- DUCKDB_PATH=data/kabusys.duckdb
- PAPER_FILL_MODE=instant
- KABUSYS_ENV=development

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の src/kabusys を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数・設定管理
    - ai/
      - __init__.py
      - news_nlp.py             # ニュースセンチメント（score_news）
      - regime_detector.py      # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント・保存関数
      - pipeline.py             # ETL パイプライン（run_daily_etl 等）
      - quality.py              # データ品質チェック
      - news_collector.py       # RSS 収集、記事前処理
      - calendar_management.py  # 市場カレンダー管理 / 営業日判定
      - audit.py                # 監査ログスキーマ初期化
      - etl.py                  # ETL インターフェース再エクスポート
      - stats.py                # 統計ユーティリティ（zscore_normalize 等）
    - research/
      - __init__.py
      - factor_research.py      # ファクター計算（momentum/value/volatility）
      - feature_exploration.py  # 将来リターン・IC・統計サマリー
    - research/ ... (他の研究用ユーティリティ)
    - その他モジュール（strategy, execution, monitoring 等は __all__ で想定）

各モジュールは docstring に設計方針・処理フロー・フォールバックの方針が詳細に書かれており、実運用に必要な堅牢性（冪等性・エラーハンドリング・フェイルセーフ）を考慮して実装されています。

---

## 運用上の注意点

- OpenAI 呼び出しを行う機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必要とします。API 呼び出しの失敗はフェイルセーフでスコア 0.0 にフォールバックする設計ですが、呼び出し制限や料金に注意してください。
- J-Quants API 利用にはトークンが必要です（JQUANTS_REFRESH_TOKEN）。get_id_token は自動リフレッシュと 401 のハンドリングを含みます。
- DuckDB のファイルパスは settings.duckdb_path で管理されます。バックアップ・ローテーションや排他アクセス設計は運用環境に合わせてください。
- ETL / API 呼び出しにはレート制限やリトライが組み込まれていますが、運用環境での監視やアラート設定を行うことを推奨します。
- 監査ログテーブルは削除しない前提で設計されています。スキーマ初期化後はアプリ側で created_at/updated_at を適切に設定してください。

---

この README はコードベースの主要機能と使い方を要約しています。各モジュールには詳細な docstring があるので、実装・拡張時は該当モジュールのドキュメントを参照してください。必要であれば README にインストール用 requirements や運用例（systemd / cron / Airflow サンプル）を追記します。