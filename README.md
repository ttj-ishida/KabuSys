# KabuSys

日本株向けのデータプラットフォーム & 研究・自動売買基盤のコンポーネント群です。  
このリポジトリは主に以下を提供します。

- J‑Quants API を用いたデータ ETL（株価・財務・市場カレンダー）
- ニュース収集・NLP スコアリング（OpenAI を利用）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算・特徴量解析ユーティリティ
- データ品質チェック、監査ログ（監査用 DuckDB スキーマ）ユーティリティ
- 設定読み込み・環境管理ユーティリティ

この README ではプロジェクト概要、機能、セットアップ、簡単な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（ETL）・品質チェック・特徴量計算・AI（LLM）を使ったニュースセンチメント評価・市場レジーム判定など、アルゴリズムトレーディング／リサーチ基盤で必要となる共通処理をまとめたライブラリ群です。  
内部では DuckDB をデータレイク代わりに用い、J‑Quants API から差分取得・保存を行います。OpenAI（gpt-4o-mini 等）をニュース解析に利用します。設計上、ルックアヘッドバイアスを避ける取り回し（target_date を明示して処理）を意識しています。

---

## 機能一覧

主要なモジュールと機能（抜粋）

- kabusys.config
  - .env / .env.local /環境変数から設定を読み込む（自動ロード有効）
  - 設定プロパティ（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
- kabusys.data
  - jquants_client
    - J‑Quants API からのデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info）
    - DuckDB へ冪等に保存する save_* 関数
    - トークン自動リフレッシュ、レートリミット、再試行ロジック
  - pipeline / etl
    - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の一括差分 ETL
    - 個別 ETL ヘルパー（run_prices_etl / run_financials_etl / run_calendar_etl）
    - ETL 結果を表す ETLResult
  - quality
    - 欠損データ、重複、スパイク（急騰急落）、日付不整合のチェック
    - run_all_checks でまとめて実行
  - news_collector
    - RSS から記事収集、前処理、SSRF 対策、トラッキング除去、raw_news テーブルへの冪等保存（設計方針に従った安全実装）
  - calendar_management
    - market_calendar を元に営業日判定、前後営業日取得、カレンダー更新ジョブ
  - audit
    - 監査ログ用の DuckDB スキーマ初期化（signal_events, order_requests, executions 等）
    - init_audit_db / init_audit_schema
  - stats
    - zscore_normalize 等の汎用統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)
    - 指定ウィンドウのニュースを銘柄ごとに集約して LLM でセンチメントを評価し ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を market_regime テーブルに保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

設計上の特徴：
- ルックアヘッドバイアス防止（target_date を明示、DB クエリは date < target_date など）
- 冪等性（DB 保存は ON CONFLICT DO UPDATE 等）
- API 呼び出しに対する堅牢なリトライ/バックオフ
- 外部依存を最小限にし、標準ライブラリと少数の主要パッケージで構成

---

## 必要条件

- Python 3.10 以上（型ヒントで | を使用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - openai (新しい SDK の OpenAI クライアントを想定)
  - defusedxml
  - defusedxml のほか、requests を使う実装があれば追加
- J‑Quants アカウント（リフレッシュトークン）、OpenAI API キー（ニュース NLP／レジーム判定用）

（実際の pyproject.toml / requirements.txt を参照してインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンし、開発用にインストール
   - git clone <repo>
   - cd <repo>
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - pip install -e .   # パッケージ化されていれば（setup/pyproject がある場合）

2. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動的に読み込まれます（.env.local は上書き）。
   - 自動ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 主要な環境変数例（.env）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb    # デフォルト
     - SQLITE_PATH=data/monitoring.db     # 監視 DB 等
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO

3. DuckDB データベースの準備
   - デフォルトは data/kabusys.duckdb（settings.duckdb_path）
   - 初期スキーマ（監査スキーマ等）は各 init_* 関数で作成できます（例: audit.init_audit_db）

---

## 使い方（簡易コード例）

以下は最小限の使用例です。すべて Python スクリプト内で行えます。

- 共通準備（設定読み込み・DuckDB 接続）:

```python
from datetime import date
import duckdb
from kabusys.config import settings

# settings は環境変数から値を取得する
db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)
```

- 日次 ETL 実行（prices / financials / calendar / 品質チェック）:

```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（指定日）をスコアして ai_scores に書き込む:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジームを評価して market_regime に書き込む:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化する（別 DB を作る例）:

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで監査ログ用テーブルが作成される
```

- 設定値の参照例:

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 未設定なら ValueError
print(settings.duckdb_path)
print(settings.env, settings.log_level)
```

注意点:
- LLM（OpenAI）を使う関数は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- すべての「日付ベース」の処理は target_date を明示して呼ぶこと（内部で date.today() に依存しない設計だが、run_daily_etl は省略可で today を使う）。

---

## よく使うコマンド / ユースケース

- ETL の自動化（cron / systemd timer など）で日次 run_daily_etl を呼ぶ
- ニュース収集を定期実行して raw_news を更新、夜間に score_news を回す
- 毎営業日の朝に score_regime を実行して market_regime を更新し、戦略のモジュールに供給する
- quality.run_all_checks により ETL 後の品質問題を検知・アラート化する

---

## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系実装がある場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動読み込みを無効化

.env の読み込み仕様:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` を自動で読み込みます。
- `.env.local` があれば `.env` 上から上書きします（OS 環境変数は保護されます）。
- .env のパースはシェル風の `export KEY=val` やクォート、コメントをある程度考慮します。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主なファイル / フォルダ（提供されたコードに基づく）

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
      - quality.py
      - stats.py
      - news_collector.py
      - calendar_management.py
      - audit.py
      - (その他 ETL 補助モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - (strategy/, execution/, monitoring/ といったモジュールが存在する可能性があります)
- .env.example (想定)
- pyproject.toml / setup.cfg（パッケージ設定：存在する場合）

---

## 注意事項 / 運用上のポイント

- API レートや課金の注意
  - J‑Quants の API はレート制限を設けています（実装でスロットリングしていますが、実運用では利用規約に従ってください）。
  - OpenAI の呼び出しはコストが発生します。バッチの頻度やモデル選択に注意してください。
- セキュリティ
  - .env やシークレットはリポジトリに含めないでください。CI / 本番ではシークレット管理ツールを利用してください。
  - news_collector は SSRF 対策や XML の安全パースを組み込んでいますが、運用環境に合わせて追加対策を検討してください。
- テスト
  - OpenAI / J‑Quants 呼び出しはモック可能なように設計されています（内部の _call_openai_api や HTTP 呼び出しを差し替え）。
- ルックアヘッドバイアス対策
  - 研究・バックテスト用途で本ライブラリを利用する際は、target_date の扱いに注意し、取得タイミング（fetched_at）を考慮してください。

---

## 追加情報 / 貢献

バグ報告・機能提案は Issue にお願いします。プルリクエストは歓迎します。コードスタイルやテスト方針はプロジェクトの CONTRIBUTING.md があればそれに従ってください。

---

以上がこのコードベースの概要と基本的な使い方です。README の内容を特定の実行環境や CI に合わせてカスタマイズすることを推奨します。必要なら各機能（ETL、ニュース収集、監査スキーマ等）の詳細な操作手順サンプルも作成します。どの部分のサンプルが欲しいか教えてください。