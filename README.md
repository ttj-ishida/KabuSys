# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
DuckDB ベースのデータパイプライン、J-Quants からの ETL、ニュース収集と LLM によるニュースセンチメント評価、マーケットレジーム判定、リサーチ用のファクター計算、監査ログスキーマなどを提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API からの株価（日次 OHLCV）・財務データ・マーケットカレンダーの差分取得（pagination 対応）
  - 差分取得 / バックフィル / 品質チェックを行う日次 ETL パイプライン（data.pipeline.run_daily_etl）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集・NLP
  - RSS からのニュース収集と raw_news 保存（ニュース→銘柄紐付け）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出（ai.news_nlp.score_news）
  - マクロニュース + ETF MA200 乖離から市場レジームを判定（ai.regime_detector.score_regime）

- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（情報係数）計算や統計サマリー（research.feature_exploration）
  - クロスセクション Z スコア正規化ユーティリティ（data.stats.zscore_normalize）

- データ品質・カレンダー管理
  - データ品質チェック（欠損・重複・スパイク・日付不整合）（data.quality）
  - JPX カレンダー管理と営業日判定ユーティリティ（data.calendar_management）

- 監査・トレーサビリティ
  - シグナル→発注→約定までをトレースする監査スキーマの初期化・操作（data.audit.init_audit_db など）

- 設定管理
  - .env ファイルおよび環境変数による設定（kabusys.config.settings）
  - 自動 .env 読み込み（プロジェクトルートの .env / .env.local。無効化可）

---

## 前提（Requirements）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他（ネットワークアクセス、J-Quants / OpenAI API キー等）

例: 仮想環境作成・インストール（プロジェクトに requirements.txt がない場合は手動で）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（実運用では適切な依存管理ファイルを用意してください）

---

## 環境変数 / .env（主な設定）

kabusys は環境変数や .env ファイルから設定を読み込みます（プロジェクトルートの .git または pyproject.toml を起点に自動検出）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主なキー（README 用サンプル）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI スコア計算で利用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）など（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment: one of development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

簡単な .env.example（プロジェクトルートに配置して利用）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - プロジェクトルートに .git または pyproject.toml があることを想定（自動 .env 検出に使用）

2. 仮想環境作成・依存パッケージをインストール
   - Python 3.10 以上を使用
   - 必要なパッケージをインストール（例）
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb openai defusedxml
     ```

3. 環境変数の設定
   - 上記の .env.example を参考に `.env`（および必要なら `.env.local`）を作成
   - プロジェクトルートに置くと自動で読み込まれます（テストで自動読み込みを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

4. データベース初期化（監査用 DB など）
   - 監査ログ用 DuckDB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # :memory: も可
     ```
   - ETL 等で使うメイン DuckDB は settings.duckdb_path を参照して作成・接続してください。

---

## 使い方（代表的なユースケース）

以下はライブラリを直接インポートして利用する簡単な例です。実運用では適切なロギング・例外処理・スケジューリング（cron / Airflow 等）を組み合わせてください。

- DuckDB 接続を開く（メイン DB）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算（OpenAI API キーを環境変数に設定しておく）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロ記事の LLM スコア合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- リサーチ用ファクター計算
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

- 監査スキーマを既存 DB に追加
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

---

## 実装上の注意点 / 設計方針の要約

- ルックアヘッドバイアス対策:
  - 各モジュール（ETL / AI / リサーチ）は内部で datetime.today() を不必要に参照しないよう設計されています。必ず target_date を渡すか DB 内の日時を参照します。
- 冪等性:
  - DuckDB への保存は可能な限り ON CONFLICT / DO UPDATE を利用して冪等にしています。
- フェイルセーフ:
  - OpenAI API や外部 API の失敗時は、極力処理を中断せずフェイルセーフなデフォルト（例: マクロセンチメント=0.0）で継続します。ただし重要な設定不足（APIキー等）は例外を投げます。
- セキュリティ:
  - RSS 収集での SSRF 対策、XML パーサの hardening（defusedxml）、リクエストサイズ上限などを実装しています。
- ロギング:
  - settings.log_level によってログレベルを制御できます（環境変数 LOG_LEVEL）。

---

## ディレクトリ構成

主要なファイルとディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py  (パッケージ version: 0.1.0)
  - config.py  (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py         (銘柄別ニュースセンチメント算出)
    - regime_detector.py  (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント、取得・保存関数)
    - pipeline.py         (ETL パイプライン・run_daily_etl 等)
    - etl.py              (ETLResult 再エクスポート)
    - news_collector.py   (RSS 収集・前処理)
    - calendar_management.py (JPX カレンダー管理 / 営業日判定)
    - quality.py          (データ品質チェック)
    - stats.py            (統計ユーティリティ: zscore_normalize)
    - audit.py            (監査ログスキーマ初期化 / init_audit_db)
  - research/
    - __init__.py
    - factor_research.py  (momentum/value/volatility)
    - feature_exploration.py (forward returns, IC, factor summary)
  - research/* その他の補助モジュール

（リポジトリルートに README.md、.env.example、pyproject.toml 等があることを想定）

---

## 開発 / テストについて

- 自動 .env 読み込みはプロジェクトルートの .env / .env.local を優先して行われます。テスト時に自動ロードを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants API 呼び出しはモック可能な設計（内部 _call_openai_api の差し替えなど）になっています。ユニットテストでは外部 API 呼び出しをモックして実行してください。

---

## 最後に

この README はコードベースの公開インターフェースと主要な使い方を簡潔にまとめたものです。細かな挙動や API の詳細（J-Quants レスポンスフィールドなど）は各モジュールの docstring を参照してください。必要であれば、運用手順やデプロイ手順、CI 設定などの追加ドキュメント作成もサポートします。