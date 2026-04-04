# KabuSys

日本株向けのデータ基盤・自動売買支援ライブラリです。  
ETL（J-Quants からのデータ収集）、ニュース NLP（OpenAI ベースのセンチメント評価）、市場レジーム判定、研究用ファクター計算、監査ログ（発注/約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要 API / 実行例）
- 環境変数（.env）
- ディレクトリ構成（ファイル一覧）
- 注意事項 / 設計方針のポイント

---

## プロジェクト概要

KabuSys は日本株の自動売買システム／研究プラットフォーム向けに設計された Python モジュール群です。  
主に以下を目的としています。

- J-Quants API からの差分 ETL（株価、財務、取引カレンダー）
- RSS ニュース収集と OpenAI を用いた銘柄毎のセンチメント評価（ai_score）
- 市場レジーム判定（ETF とマクロニュースの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions テーブル）によるトレーサビリティ

多くの処理は DuckDB を想定した SQL / Python ハイブリッド実装で、バックテスト用のルックアヘッドバイアス対策（target_date ベースの処理）を重視しています。

---

## 主な機能一覧

- data/jquants_client:
  - J-Quants API からのデータ取得（株価日足、財務、上場情報、マーケットカレンダー）
  - ページネーション対応、レートリミット、リトライ、ID トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- data/pipeline:
  - run_daily_etl を含む差分 ETL（calendar → prices → financials）と品質チェック
  - ETL 結果を ETLResult に格納

- data/news_collector:
  - RSS フィード収集、前処理、raw_news への冪等保存、news_symbols との紐付け（設計）

- ai/news_nlp:
  - raw_news を基に OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores に保存
  - バッチ処理、レスポンス検証、リトライ（429/ネットワーク/5xx）ロジック

- ai/regime_detector:
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成し、市場レジーム（bull/neutral/bear）を判定
  - LLM 呼び出しのフェイルセーフ（失敗時は macro_sentiment=0.0）

- research:
  - calc_momentum / calc_value / calc_volatility 等のファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank（研究用統計）

- data/quality:
  - 欠損、スパイク、重複、日付不整合のチェック、QualityIssue を返す

- data/audit:
  - 監査ログ用スキーマ定義・初期化（signal_events / order_requests / executions）
  - init_audit_db で専用 DuckDB を初期化可能

- config:
  - .env 自動読み込み（プロジェクトルート検出）
  - Settings クラスで設定値をプロパティとして提供
  - 環境: development / paper_trading / live をサポート

---

## セットアップ手順

1. リポジトリのクローン（想定）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージのインストール（代表例）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際の requirements.txt があれば `pip install -r requirements.txt` を使用してください。

4. パッケージとして開発インストール（プロジェクトルートに setup/pyproject がある想定）
   ```
   pip install -e .
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数の例は次節「環境変数」を参照。

6. DuckDB データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 環境変数（主要）

config.Settings で参照される代表的な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使用）

- KABU_API_PASSWORD (必須)  
  kabuステーション API のパスワード（発注周りで使用）

- KABU_API_BASE_URL (任意)  
  kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）

- OPENAI_API_KEY (LLM の API キー、score_news/score_regime に未指定時参照)

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)  
  LINE 通知を使う場合

- DUCKDB_PATH（任意, default: data/kabusys.duckdb）  
  DuckDB ファイルパス

- SQLITE_PATH（任意, default: data/monitoring.db）

- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START（監視用）

- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）

- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

自動読み込みの挙動:
- OS 環境変数が最優先
- 次に `.env.local`（override=True）
- 最後に `.env`（override=False）
- プロジェクトルートは .git または pyproject.toml を基準に自動検出
- 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要 API と実行例）

以下はライブラリ利用のサンプルです。各関数の引数や戻りはソースの docstring を参照してください。

- DuckDB 接続を得る（例）:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）:
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると today が使われます（ただし内部で trading day に調整されます）
  result = run_daily_etl(conn, target_date=None, id_token=None)
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（score_news）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を参照
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（score_regime）:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  status = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants ID トークン取得:
  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注:
- score_news / score_regime は OpenAI API を呼び出します。api_key 引数で明示的に渡すか OPENAI_API_KEY 環境変数を設定してください。
- 多くの関数は「target_date」を外部から与えることでルックアヘッドバイアスを防止しています。内部で date.today() を参照しない設計です（バックテスト向け）。

---

## ディレクトリ構成

（ソースに基づく主要ファイル一覧）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - (その他 jquants_client で参照されるユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの役割:
- config.py: .env 自動読み込み、Settings プロパティ（環境変数のアクセス統一）
- data/: データ収集・ETL・品質チェック・監査ログ等
- ai/: ニュース NLP / レジーム判定（OpenAI 利用）
- research/: ファクター計算・IC・統計ユーティリティ

---

## 注意事項 / 設計方針のポイント

- ルックアヘッドバイアス防止: 多くの処理は target_date を明示して行い、現在時刻の利用を極力避けています。
- 冪等性: ETL や保存処理は基本的に ON CONFLICT DO UPDATE / INSERT ... DO UPDATE などで冪等に実装されています。
- フェイルセーフ: LLM 呼び出しや外部 API の失敗時は例外を投げずに安全側の値（例: macro_sentiment=0.0）にフォールバックする実装が多いです。
- レート制限・リトライ: J-Quants クライアントには固定インターバルの RateLimiter とリトライロジックがあります。OpenAI 呼び出し周りもリトライを実装しています。
- セキュリティ:
  - news_collector は SSRF 対策（プライベートIP ブロック、スキーム検証）、defusedxml を使用
  - URL 正規化、トラッキングパラメータ除去、記事 ID を SHA-256 で生成して冪等性を担保
- DuckDB 互換性: executemany の空リスト問題など DuckDB の実装差異を意識した実装があります。

---

この README はリポジトリ内のソースコードを基に作成しています。実際に動かす際はプロジェクトの pyproject.toml / requirements.txt を確認し、必要な外部ライブラリやランタイムを揃えてください。必要であれば利用方法の詳細（具体的な ETL スケジュール、監視の実行例、kabu ステーション連携の実行手順など）を追加しますので教えてください。