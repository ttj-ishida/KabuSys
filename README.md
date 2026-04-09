# KabuSys

日本株向けのデータパイプライン・研究・自動売買/監視のための共通ライブラリ群です。  
DuckDB を中心としたデータプラットフォーム、J-Quants API クライアント、ニュースの NLP 処理、ファクター計算、監査ログ/発注追跡などのユーティリティを備えます。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からニュース収集し、LLM（OpenAI）を用いた銘柄センチメント（ai_score）生成
- マクロセンチメント + 指標を合成して市場レジーム（bull/neutral/bear）を判定
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算、特徴量探索（IC、将来リターン等）
- 監査ログ（signal → order_request → executions）のスキーマ初期化・操作ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上の特徴として、ルックアヘッドバイアス対策、冪等性（DB 保存時の ON CONFLICT）、API 呼び出しの堅牢なリトライ・レート制御、SSRF 対策等に配慮しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 呼び出し、ページネーション、トークン管理、DuckDB への保存関数
  - etl / pipeline: 日次 ETL 実行フロー（calendar / prices / financials）、ETLResult の報告
  - news_collector: RSS 取得・正規化・raw_news への保存（SSRF 対策・トラッキングパラメータ除去等）
  - quality: データ品質チェック（missing/spike/duplicates/date consistency）
  - audit: 監査ログテーブル（signal_events, order_requests, executions）の DDL と初期化ユーティリティ
  - calendar_management: JPX カレンダーの営業日判定・next/prev/get_trading_days・夜間更新ジョブ
  - stats: z-score 正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースをまとめて LLM に投げ、ai_scores テーブルへ書き込む処理
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロニュースセンチメントを合成して market_regime に保存
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility（ファクター計算）
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（統計解析）

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージをインストール
   - 開発中: pip install -e .
   - 依存パッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml
     - （その他、プロジェクトの pyproject.toml / requirements.txt を参照）

3. 環境変数の設定
   - プロジェクトルートの `.env` または `.env.local` に変数を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主要な環境変数（例）:
     - 必須
       - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
       - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能利用時）
     - OpenAI / 通知等
       - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に使用）
       - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知に使用（任意）
     - DB/監視
       - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
       - SQLITE_PATH (デフォルト: data/monitoring.db)
       - PAPER_FILL_MODE (paper_trading 用。'instant'|'partial'|'never'|'reject')
       - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - 実行環境
       - KABUSYS_ENV: development | paper_trading | live
       - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

   - 例: .env
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     OPENAI_API_KEY=sk-xxxx...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. DuckDB スキーマ初期化（監査ログなど）
   - 監査ログ専用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用の総合的な初期化は、利用するスキーマ定義に応じて行ってください（このリポジトリには schema 初期化ユーティリティが含まれている想定です）。

---

## 使い方（簡単なコード例）

以下は基本的な利用例です。実運用ではログ設定や例外処理を適切に追加してください。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（ai_scores への書き込み）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
  print(f"書込み銘柄数: {count}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))  # market_regime に保存される
  ```

- 監査ログスキーマ初期化（既存の DuckDB 接続で）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算 / 研究用ユーティリティ
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize

  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  # Zスコア正規化
  mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

注意: score_news / score_regime は OpenAI の JSON Mode を利用する想定です。テスト時はモジュール内の _call_openai_api をモックして外部呼び出しを防いでください（README 内コードに記載の通り）。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュール構成は以下の通りです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント、保存関数
    - pipeline.py                  — ETL 実行フロー（run_daily_etl 等）
    - etl.py                       — ETLResult の再エクスポート
    - news_collector.py            — RSS 収集・前処理・保存
    - quality.py                   — データ品質チェック
    - calendar_management.py       — 市場カレンダー管理
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py       — 将来リターン・IC・summary 等
  - research 包含の他モジュール...
- その他: pyproject.toml や .env.example をプロジェクトルートに配置する想定

---

## 注意事項 / 補足

- .env の自動ロード:
  - config.py は実行ファイル位置から親ディレクトリを遡って `.git` または `pyproject.toml` を検出し、プロジェクトルートを推定します。そこにある `.env` と `.env.local` を順にロードします。
  - テストや特別な環境では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。

- OpenAI 呼び出し:
  - news_nlp と regime_detector は JSON Mode（response_format={"type": "json_object"}）で呼び出す設計です。API エラー時はフェイルセーフとしてスコア 0.0 を使用する等の処理が入っています。
  - テストでは各モジュールの `_call_openai_api` を patch して応答を差し替えることを推奨します。

- J-Quants API:
  - レート制限（120 req/min）に合わせた RateLimiter を内蔵しています。401 時のトークン自動リフレッシュ（1回）や、408/429/5xx に対する指数バックオフのリトライが組み込まれています。

- DuckDB のバージョン差異:
  - 一部の executemany / リスト型バインドに関する処理は DuckDB のバージョンによって挙動が異なるため、pipeline / ai モジュール内で空リストの executemany を避ける実装になっています。DuckDB の推奨バージョンに合わせて運用してください。

---

## 貢献 / テスト

- テストを書く際は外部 API 呼び出し（OpenAI, J-Quants, HTTP）をモックしてください。モジュール内で _call_openai_api や _urlopen、_request などを差し替える設計になっています。
- バグ報告・改善提案は Pull Request でお願いします。

---

この README はコードベースの公開 API と設計方針、セットアップ・利用方法の概要をまとめたものです。詳細な API 仕様やスキーマ、運用手順は該当モジュール内の docstring（関数コメント）を参照してください。