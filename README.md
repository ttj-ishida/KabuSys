# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants）・ニュース収集・LLM によるニュースセンチメント評価・市場レジーム判定・研究用ファクター計算・監査ログ等のユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・品質チェック・特徴量計算・AI を使ったニュース評価・市場レジーム判定・監査ログ（注文→約定のトレーサビリティ）など、量的運用システムに必要な共通機能をまとめた Python パッケージです。  
主に DuckDB をデータ層に用い、J-Quants API など外部データソースと連携することを想定しています。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を乱用しない）
- 冪等性（ON CONFLICT / UUIDベースのキー）を重視した保存処理
- API 呼び出しはリトライやレート制御を実装しフェイルセーフを備える
- テストしやすさ（OpenAI 呼び出しの差し替え等）を考慮

---

## 機能一覧

- 環境変数 / 設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルートを探索）
  - 必須環境変数取得ユーティリティ

- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants から日次株価、財務、マーケットカレンダー取得（ページネーション対応）
  - 差分更新 / バックフィル / 保存（DuckDB へ冪等保存）
  - run_daily_etl で日次パイプラインを一括実行

- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、将来日付・非営業日データ検出
  - QualityIssue 型で結果を返す

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 前後の営業日取得 / 期間内営業日リスト
  - JPX カレンダーの差分更新ジョブ

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、raw_news への冪等保存
  - SSRF・Gzip Bomb・XML 攻撃対策を考慮した実装

- AI（kabusys.ai）
  - ニュースセンチメント: score_news（gpt-4o-mini を用いた JSON Mode）
  - 市場レジーム判定: score_regime（ETF 1321 の MA200 乖離 + マクロニュース LLM 結果を合成）

- 研究ユーティリティ（kabusys.research）
  - ファクター計算: momentum / volatility / value
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ヘルパー
  - init_audit_db で監査用 DB 初期化（UTC タイムゾーン固定）

---

## 必要条件

- Python >= 3.10（typing の新構文と | での型結合を利用）
- 以下の主要依存ライブラリ（少なくとも開発環境にインストールしてください）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml

（実稼働環境では他に urllib 等標準ライブラリで十分ですが、requirements.txt をプロジェクト側で用意してください）

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール（開発形態）
   - pip install -e .   # プロジェクトルートで

   または必要なライブラリだけ入れる:
   - pip install duckdb openai defusedxml

3. 環境変数の準備
   - プロジェクトルートに `.env` を作成してください。ライブラリは自動的にプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を探索して `.env` / `.env.local` を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須（少なくともテスト/稼働で必要となる代表例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - KABU_API_PASSWORD=your_kabu_api_password
   - OPENAI_API_KEY=your_openai_api_key

   任意:
   - KABUSYS_ENV=development|paper_trading|live   (デフォルト: development)
   - LOG_LEVEL=INFO|DEBUG|...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C0123456789
   KABU_API_PASSWORD=passwd
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主要な API と実行例）

以下は簡単な利用例です。基本的に各関数は DuckDB 接続（duckdb.connect(...) の戻り値）と date を受け取ります。

- DuckDB 接続の作成（ファイル DB または ":memory:"）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # テーブル作成済みの conn が返る
  ```

- 日次 ETL の実行（J-Quants からデータ取得して保存 → 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())  # ETLResult の概要を見る
  ```

- ニュースセンチメントのスコアリング（OpenAI API キーは env または引数で）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print("書込銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 研究（ファクター計算 / 正規化 / forward returns）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value
  from kabusys.data.stats import zscore_normalize
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))
  normed = zscore_normalize(momentum, ["mom_1m","mom_3m","mom_6m"])
  ```

- テスト時のポイント
  - OpenAI 呼び出しはモジュール内の private helper（例: kabusys.ai.news_nlp._call_openai_api）を patch して差し替えが容易にできます。
  - 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要なファイル/モジュール構成です（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                        -- 環境変数/設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                     -- ニュースの LLM ベースセンチメント集計
    - regime_detector.py              -- ETF MA200 + マクロニュース合成で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               -- J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
    - etl.py                          -- ETLResult の再エクスポート
    - news_collector.py               -- RSS 取得と前処理
    - quality.py                      -- データ品質チェック
    - calendar_management.py          -- マーケットカレンダー管理と判定ロジック
    - stats.py                         -- 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                        -- 監査ログテーブル定義と初期化
  - research/
    - __init__.py
    - factor_research.py              -- momentum / volatility / value 等
    - feature_exploration.py          -- forward returns / IC / factor summary
  - (その他)                          -- strategy / execution / monitoring 等が __all__ に想定

---

## 注意点 / 運用上のヒント

- OpenAI の呼び出しにはコストとレイテンシが伴います。バッチサイズやトークン量を設計時に調整してください。
- J-Quants API はレート制限があり、モジュール内でレート制御とリトライを実装しています。大量の同時クライアントは避けてください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、モジュール実装では空チェックを行っています。DuckDB のバージョン依存に注意してください。
- 自動 .env ロードはプロジェクトルート探索に基づきます。テストで現在の作業ディレクトリを変更する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にするか、環境を明示的に設定してください。

---

## ライセンス / 貢献

このリポジトリのライセンス情報や貢献ガイドラインはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（この README には含まれていません）。

---

README に含めるべき追加の情報（例: requirements.txt、CI 手順、実運用時の監視や Slack 通知の実装例など）があれば教えてください。必要に応じてサンプル .env.example やコマンドラインツールの使い方（もし存在すれば）も追記します。