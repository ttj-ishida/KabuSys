# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP による銘柄スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（監査テーブル）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ基盤と研究・運用レイヤーを統合するためのモジュール群です。主に次の機能を想定しています。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL（ページネーション・再試行・レート制御対応）
- RSS からのニュース収集（SSRF 対策、前処理、冪等保存）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント／市場レジーム評価（JSON Mode での厳密な入出力）
- ファクター計算（モメンタム／ボラティリティ／バリュー等）およびリサーチ補助関数
- データ品質チェック（欠損／重複／スパイク／日付不整合など）
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）
- 環境設定管理（.env 自動ロード・必須環境変数検証）

設計上の留意点として、ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を参照しない等）、冪等性、フェイルセーフ（API 失敗時に例外にせずフォールバック）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・認証・ページネーション・レート制御・再試行）
  - pipeline: 日次 ETL（run_daily_etl、個別 run_prices_etl 等）
  - news_collector: RSS 収集と raw_news 保存（SSRF/サイズ/圧縮対策）
  - calendar_management: JPX カレンダー管理・営業日判定
  - quality: データ品質チェック
  - audit: 監査ログスキーマ初期化・監査 DB ユーティリティ
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp: ニュースをバッチで LLM に投げて銘柄別スコアを ai_scores に保存（JSON mode）
  - regime_detector: ETF (1321) の 200 日 MA とマクロニュースセンチメントを合成して日次の市場レジーム判定
- research/
  - factor_research: momentum / value / volatility の計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー等
- config.py: .env 自動読み込み、必須環境変数チェック、設定ラッパー（settings）
- その他: audit / execution / monitoring 等の補助モジュール（パッケージ公開インターフェース）

---

## 必要条件（推奨）

- Python 3.10 以上（typing の | 演算子と __future__ annotations を使っています）
- 主要 Python パッケージ:
  - duckdb
  - openai
  - defusedxml

（上記はコード内で使用されています。環境に合わせて適宜導入してください。）

pip 例:
pip install duckdb openai defusedxml

プロジェクトをパッケージとして使う場合は通常の setuptools/poetry によるインストール手順に従ってください（例: pip install -e .）。

---

## セットアップ手順

1. リポジトリをクローンして venv を作成
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # その他開発用ツールやテスト用パッケージがあれば適宜追加
   ```

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。
   - .env の例（.env.example を参照して作成してください）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_DISABLE_AUTO_ENV_LOAD=  # 自動ロード無効化: 1
     ```
   - .env パーサーの挙動:
     - `export KEY=val` 形式対応
     - クォート (シングル/ダブル) のエスケープを尊重
     - 行頭 `#` はコメント、クォートなしの値中の `#` は直前が空白/タブのときコメントとして扱う

4. データベース用ディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡易ガイド）

以下は主要なユースケースの最小例です。実運用ではエラーハンドリング・ロギング・認証情報管理を適切に行ってください。

- DuckDB 接続の作成（例: データベースファイルを使用）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（J-Quants から取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースを LLM で評価して ai_scores に保存（score_news）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数または api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("Written scores:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルとインデックスが作成されます
  ```

- 各種ファクター計算（研究用途）
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  ```

- settings（環境設定）使用例
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live, settings.is_paper, settings.is_dev)
  ```

---

## 主要な環境変数

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う場合は必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注モジュール利用時）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知等に使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視等で使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

注: settings のプロパティは未設定の場合 ValueError を投げる（必須項目の保護）。

---

## 実運用上の注意点

- LLM 呼び出し:
  - news_nlp, regime_detector は OpenAI の JSON モードを用いて厳密な JSON を期待します。API レスポンスのパース失敗や API エラー時はフェイルセーフとしてスコアを 0.0 にフォールバックする実装です。
  - API のレート制御やリトライは実装されていますが、API 料金やレート制限に注意してください。

- Look-ahead Bias の防止:
  - 多くのモジュールはデータウィンドウを target_date を基準に過去側で限定しており、内部で date.today() を不用意に使わないように設計されています。バックテストや再現性の確保に有用です。

- ETL の冪等性:
  - J-Quants から取得したデータは DuckDB へ ON CONFLICT DO UPDATE（上書き）で保存されます。再実行可で差分回収を行います。

- ニュース収集の安全:
  - RSS 取得時に SSRF / プライベートアドレスアクセスを防ぐチェック、Content-Length / 読込上限、gzip 解凍後のサイズチェック（Gzip bomb 対策）が入っています。

---

## ディレクトリ構成（抜粋）

以下は src 内の主要モジュールの構成の抜粋です。

- src/
  - kabusys/
    - __init__.py
    - __version__ = "0.1.0"
    - config.py
    - ai/
      - __init__.py (score_news を公開)
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py (ETLResult 再エクスポート)
      - news_collector.py
      - calendar_management.py
      - stats.py
      - quality.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
      - ...（リサーチ用ユーティリティ）
    - (その他) strategy / execution / monitoring 等（パッケージ公開用 __all__ に含まれる）

（実際のファイル一覧はリポジトリルートを参照してください）

---

## 開発メモ / テストのヒント

- config の自動 .env ロードは、パッケージ内でファイル位置を __file__ を起点に探索しているため、開発時はリポジトリルートに .env を置くことで自動的に読み込まれます。テスト時に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しはテストのためにモック可能に設計されています（モジュール内の `_call_openai_api` を patch するなど）。
- DuckDB を使った関数は接続オブジェクトを引数に受け取るため、テストでは `duckdb.connect(":memory:")` を使うと良いです。
- news_collector の RSS 取得はネットワーク呼び出しを行うため、単体テストでは `_urlopen` をモックしてください。

---

## ライセンス / 著作権

（ここにプロジェクトのライセンス情報を記載してください。例: MIT License 等）

---

README の追加・修正や、具体的な実行スクリプト・CI 設定のテンプレートが必要であれば教えてください。用途に合わせた README の拡張（デプロイ手順、docker-compose、cron ジョブ例、Slack 通知設定例など）も作成できます。