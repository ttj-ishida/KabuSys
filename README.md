# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ管理などを含みます。

## 主な概要
- DuckDB をバックエンドとしたデータプラットフォーム（raw_prices / raw_financials / market_calendar / raw_news など）
- J-Quants API 経由で株価・財務・カレンダーを差分取得する ETL パイプライン
- RSS ベースのニュース収集と OpenAI を用いた銘柄ごとのニュースセンチメント評価（ai_score）
- ETF（1321）200日移動平均とマクロニュースセンチメントを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）および特徴量探索ユーティリティ
- 監査ログ（signal / order_request / execution）用のスキーマ初期化ユーティリティ
- 環境変数/.env を自動読み込みする設定管理

## 主な機能一覧
- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェックを行う Settings オブジェクト（kabusys.config.settings）
- Data (src/kabusys/data)
  - jquants_client: J-Quants API 呼び出し + DuckDB への保存（差分取得・ページネーション・トークン自動リフレッシュ・レート制御）
  - pipeline: 日次 ETL（run_daily_etl）＋個別 ETL（run_prices_etl 等）と ETL 結果クラス（ETLResult）
  - news_collector: RSS 取得・前処理・raw_news 保存（SSRF対策、トラッキングパラメータ除去、XML セーフパース）
  - calendar_management: JPX カレンダー管理、営業日判定・前後営業日検索、夜間更新ジョブ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats: z-score 正規化ユーティリティ
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
- AI (src/kabusys/ai)
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI に問い合わせて ai_scores テーブルに書き込む
  - regime_detector.score_regime: ETF(1321)のMA乖離とマクロニュースセンチメントを合成して market_regime に書き込む
- Research (src/kabusys/research)
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 監視・実行系（パッケージの核となるモジュール群を提供）

---

## 要件（推奨）
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他: 標準ライブラリ以外の依存は各機能で必要に応じて導入してください

簡易インストール例:
```
python -m pip install duckdb openai defusedxml
```

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## 環境変数（主要）
以下はコード上で使用している主な環境変数です。必須項目は明示します。

- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用されます。
- KABU_API_PASSWORD (必須)  
  - kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (必須 for AI 機能)  
  - news_nlp / regime_detector の OpenAI クライアントに使用。関数呼び出し時に api_key を明示的に渡すことも可能。
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)
- SQLITE_PATH (任意, default: data/monitoring.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (default: development) — 有効値: development, paper_trading, live
- LOG_LEVEL (default: INFO)

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある .env/.env.local を自動で読み込みします。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（ローカル開発向けの最小手順）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .\.venv\Scripts\activate    # Windows
   ```
3. 必要ライブラリをインストール
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb openai defusedxml
   ```
4. 環境変数を設定（.env を作成）
   - 最低限 JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY を設定してください（AI 機能や ETL 実行に必要）。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxx...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=DEBUG
     ```
5. データ用ディレクトリを作成
   ```
   mkdir -p data
   ```

---

## 使い方（コード例）
以下は代表的な利用例です。すべての関数はテスト容易性を考慮し、DuckDB 接続を呼び出し側で作成して渡します。

- 日次 ETL を実行する:
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む:
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 19), api_key=None)  # env OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

- 市場レジームを評価して market_regime に保存する:
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 19), api_key=None)  # env OPENAI_API_KEY を使用
```

- 監査ログ用の DuckDB を初期化する:
```
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring.duckdb")
# conn を使って order_requests / signal_events / executions にアクセス可能
```

- 研究系ファクター計算（例: モメンタム）:
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 19))
# records は dict のリスト
```

- 環境変数自動読み込みを無効化したい場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 注意点 / 設計上の重要事項
- Look-ahead バイアス防止:
  - AI/リサーチ系の機能は内部で datetime.today() を参照せず、呼び出し元が target_date を渡す設計です。バックテスト用途では target_date を適切に管理してください。
- OpenAI 呼び出し:
  - API 呼び出しはリトライ・バックオフ・JSON 検証を組み込んでいますが、API キーは環境変数（OPENAI_API_KEY）または関数引数で必ず指定してください。
- J-Quants API:
  - rate limit（120 req/min）を遵守するための RateLimiter を実装しています。ID トークンは自動リフレッシュされます。
- DuckDB との互換性:
  - 一部の操作（executemany の空パラメータ等）について DuckDB のバージョン差に配慮した実装があります。DuckDB バージョンによる挙動差異に注意してください。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / Settings 管理（自動 .env ロード）
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュース NLP スコアリング（score_news）
    - regime_detector.py           -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント + 保存関数
    - pipeline.py                  -- ETL パイプライン（run_daily_etl など） & ETLResult
    - etl.py                       -- ETLResult 再エクスポート
    - news_collector.py            -- RSS 取得・前処理・raw_news 保存
    - calendar_management.py       -- 市場カレンダー管理・営業日ロジック
    - stats.py                     -- zscore_normalize 等
    - quality.py                   -- データ品質チェック
    - audit.py                     -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py       -- calc_forward_returns / calc_ic / factor_summary / rank

---

## 開発・拡張のヒント
- 単体テスト:
  - 各 AI 呼び出しやネットワーク I/O 部分（_call_openai_api, _urlopen, jquants_client._request など）はモック可能な関数として設計されています。unittest.mock を使って外部依存を差し替えたテストが容易です。
- DB スキーマ:
  - audit.init_audit_schema は冪等で実行できます。既存接続に対して transactional 引数で BEGIN/COMMITを制御できます（DuckDB のトランザクション挙動に注意）。
- ロギング:
  - settings.log_level と組み合わせて詳細ログを有効にするとトラブルシュートが容易です。

---

この README はコードベース内の主要モジュール・設計方針に基づいて作成しています。実運用前に各 API キー・データパス・ネットワーク設定を適切に構成し、少量データでの動作確認を行ってください。質問や追加したい利用例があれば教えてください。