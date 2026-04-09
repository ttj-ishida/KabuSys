# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログなど、アルゴリズム取引システムのコア機能を提供します。

---

## 目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（簡単な例）
- 環境変数（主要）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買やリサーチ向けに設計されたモジュール群です。  
主に以下を目的とします：

- J-Quants API を用いた株価・財務・カレンダーの差分ETL
- ETL 後のデータ品質チェック
- ニュースの収集・前処理と LLM によるセンチメント解析
- 市場レジーム判定（価格指標 + マクロニュース）
- ファクター計算・特徴量探索（Research向け）
- 取引監査ログ（signal → order_request → execution のトレーサビリティ）
- DuckDB をデータストアとして利用

設計上、ルックアヘッドバイアスに注意し、API 呼び出しはリトライやレート制御を行い、安全性（SSRF対策等）に配慮しています。

---

## 主な機能一覧

- 設定管理
  - .env ファイル（.env/.env.local）または環境変数から自動ロード
  - 必須値チェック（JQUANTS_REFRESH_TOKEN 等）
- データ取得・ETL
  - J-Quants からの日次株価、財務、カレンダー取得（ページネーション対応）
  - 差分更新、バックフィル、保存（DuckDB へ冪等保存）
  - run_daily_etl（市場カレンダー → prices → financials → 品質チェック）
- データ品質チェック
  - 欠損データ、主キー重複、スパイク、日付不整合の検出
- ニュース処理 / NLP
  - RSS 収集（SSRF / トラッキング除去 / 前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント解析（score_news）
  - マクロニュース + ETF MA 乖離から市場レジーム判定（score_regime）
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events, order_requests, executions テーブルを初期化／管理
  - 監査用 DB 初期化ユーティリティ

---

## セットアップ手順

以下は一般的なセットアップ手順の例です。プロジェクト配布に合わせて requirements.txt / pyproject.toml を用意している想定です。

1. Python 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を記載してください。

3. パッケージを開発モードでインストール（オプション）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env または .env.local を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 必要な環境変数の例は次節「環境変数」を参照。

---

## 環境変数（主要）

settings（kabusys.config.Settings）で参照される主な環境変数：

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 実行に必須）
  - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注などで使用）
- 任意 / デフォルトあり
  - KABUSYS_ENV           : "development" / "paper_trading" / "live"（デフォルト: development）
  - LOG_LEVEL             : ログレベル（"INFO" 等、デフォルト: INFO）
  - KABU_API_BASE_URL     : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY        : OpenAI API キー（LLM 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用（任意）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_FILL_MODE       : PaperTrading の fill モード（instant/partial/never/reject）
  - PAPER_TRADING_SQLITE_PATH : PaperTrading 用 SQLite DB パス（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH, KILL_FLAG_PATH 等の監視関連設定

.env ファイルは .env（デフォルト読み込み）→ .env.local（上書き）順で読み込まれ、既存OS環境変数は保護されます。

---

## 使い方（簡単な例）

以下は基本的な呼び出し例です。DuckDB 接続オブジェクト（duckdb.connect(...) が返す接続）を渡して利用します。

- ETL（日次）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OpenAI キーは環境変数 OPENAI_API_KEY を設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions のテーブルが作成されます
```

- 設定取得例
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

注意:
- score_news / score_regime は OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。
- ニュースの集約や ai_scores テーブルへ書き込む前提として raw_news / news_symbols 等のテーブルが存在している必要があります。ETL やニュース収集ジョブでデータを準備してください。

---

## 実装上のポイント / 運用注意

- Look-ahead バイアス対策：内部処理は datetime.today() / date.today() を参照せず、外部から渡された target_date に基づいて処理する設計です（再現性と安全性を確保）。
- J-Quants クライアントはレート制御（120 req/min）とリトライ、401 時のトークン自動リフレッシュを実装しています。
- RSS 取得では SSRF 対策（ホスト検査、リダイレクト検査）、受信バイト上限による DoS 緩和、トラッキングパラメータ削除などの前処理が行われます。
- OpenAI 呼び出しはリトライとバックオフを行い、API エラー時はフェイルセーフ（0.0 を用いる等）で継続する設計です。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE）で行います。

---

## ディレクトリ構成（主なファイル）

（ソースが src/kabusys 配下にある想定）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # ニュースセンチメント（score_news）
    - regime_detector.py   # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント・保存ロジック
    - pipeline.py          # ETL パイプライン（run_daily_etl など）
    - etl.py               # ETL の公開インターフェース（ETLResult 再エクスポート）
    - quality.py           # データ品質チェック
    - stats.py             # 統計ユーティリティ（zscore_normalize 等）
    - news_collector.py    # RSS 収集・前処理
    - calendar_management.py  # マーケットカレンダー管理（is_trading_day 等）
    - audit.py             # 監査ログ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py   # calc_momentum, calc_value, calc_volatility
    - feature_exploration.py # calc_forward_returns, calc_ic, factor_summary, rank

（実際の配布では README に合わせて pyproject.toml / requirements.txt を追加してください）

---

## ライセンス / 貢献

この README ではライセンス情報は省略しています。実際のプロジェクトに導入する場合は適切な LICENSE を追加してください。バグや機能追加、改善提案は Issue / Pull Request を通じて行ってください。

---

もし README に追記してほしい項目（API リファレンス、より詳細な環境変数一覧、運用手順、デプロイ手順、サンプル .env.example など）があれば教えてください。