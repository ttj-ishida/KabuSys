# KabuSys

日本株向けの自動売買・データ基盤ライブラリセット。ETL、ニュースNLP、マーケットレジーム判定、ファクター計算、監査ログなど、運用バッチやリサーチで使う主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つ Python ライブラリ群です。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS からのニュース収集と銘柄紐付け（news_collector）
- OpenAI を使ったニュースセンチメント分析（news_nlp）
- マクロニュースとETFの移動平均乖離を組み合わせた市場レジーム判定（regime_detector）
- ファクター計算・特徴量探索・統計ユーティリティ（research）
- データ品質チェック（quality）
- 監査ログ（signal → order → execution トレース用テーブル）初期化ユーティリティ（audit）
- マーケットカレンダー管理（calendar_management）

設計上のポイント:
- Look‑ahead bias を避けるため、内部処理は明示的な target_date を受け取り現在時刻を直接参照しません。
- ETL／API 呼び出しは冪等性・リトライ・レート制御が組まれています。
- DuckDB を主要なデータストアとして想定しています。

---

## 機能一覧

主なモジュールと概要:

- kabusys.config
  - 環境変数読み込み（.env / .env.local 自動ロード）と設定アクセス（settings）
- kabusys.data
  - pipeline: 日次 ETL 実行（run_daily_etl 等）
  - jquants_client: J-Quants API クライアント（取得・保存ロジック）
  - news_collector: RSS 取得・前処理・保存
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査テーブル DDL 初期化 utilities
  - stats: zscore 正規化などの統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースから市場レジームを判定
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは requirements.txt や pyproject.toml を参照してください。

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（最低限の例）
   ```
   pip install duckdb openai defusedxml
   ```

   - もしパッケージをローカルで editable インストールする場合:
     ```
     pip install -e .
     ```

4. 環境変数 (.env) を用意
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動でロードされます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   推奨する最低環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb            # 任意（デフォルト）
   SQLITE_PATH=data/monitoring.db             # 任意（監視用）
   KABUSYS_ENV=development                    # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   - 環境変数は OS 環境で設定しても構いません。`.env.local` は `.env` を上書きできます。

---

## 使い方（簡単な例）

注意: すべての操作は明示的な DuckDB 接続を渡すか、戻り値を確認して実行してください。

- DuckDB 接続作成例:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（OpenAI 必須）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定済みか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DuckDB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.db")
  ```

- ファクター計算（例: モメンタム）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(recs))
  ```

ログレベルは環境変数 `LOG_LEVEL`（DEBUG/INFO/…）で制御します。

---

## ディレクトリ構成

主要なファイル/ディレクトリ（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（OpenAI）
    - regime_detector.py            — 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py             — J-Quants API クライアント + 保存
    - news_collector.py             — RSS 収集・前処理
    - calendar_management.py        — カレンダー管理（営業日判定）
    - stats.py                      — 統計ユーティリティ（zscore など）
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログ DDL / 初期化
    - etl.py                        — ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 計算
    - feature_exploration.py        — forward returns / IC / summary / rank
  - research/（上記の __init__ で公開）
  - その他: strategy, execution, monitoring（パッケージ API 上で __all__ に登録）

（プロジェクトルート）
- .env, .env.local (自動ロード対象)
- pyproject.toml / setup.cfg / requirements.txt（プロジェクトによって存在）
- README.md (このファイル)

---

## 注意事項・運用メモ

- OpenAI API や J-Quants API は認証情報（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）が必須です。これらは .env または OS 環境で設定してください。
- 設定は kabusys.config.settings 経由でアクセスできます（例: settings.jquants_refresh_token）。
- 自動で .env を読み込む仕組みは有効がデフォルトです。テストなどで無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB への大量挿入やクエリは適切な接続設定で運用してください。監査ログの初期化は init_audit_schema / init_audit_db を使うと安全です。
- 外部 API 呼び出し部分はリトライやレート制御が組み込まれていますが、実運用では別途監視とアラート設定を推奨します。

---

必要に応じて README にサンプル .env.example、詳しい依存関係、CI / テスト手順、デプロイ方法を追加できます。どの情報をさらに充実させたいか教えてください。