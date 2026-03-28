# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
データ収集（J-Quants / RSS）、品質チェック、ファクター計算、ニュースNLP（OpenAI）、市場レジーム判定、監査ログなどを含む一連の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API を利用した株価・財務・上場情報・マーケットカレンダーの差分 ETL
- RSS を用いたニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント解析（銘柄毎）およびマクロセンチメントによる市場レジーム判定
- DuckDB を用いた高速なオンディスク分析と品質チェック
- 戦略・発注フローのための監査ログ（監査テーブルの初期化 / DB 操作ユーティリティ）
- 研究用のファクター計算・特徴量探索ユーティリティ

設計上の特徴:
- ルックアヘッドバイアス対策（内部で date.today() に依存しない設計、DB クエリで明示的に範囲制御）
- API 呼び出しに対する堅牢なリトライ・バックオフ・レート制御（J-Quants、OpenAI）
- DuckDB を中心とした冪等保存（ON CONFLICT / DELETE→INSERT パターン）
- RSS の SSRF・サイズ攻撃対策（ホスト検証・サイズ上限・defusedxml）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants からのデータ取得（株価、財務、マーケットカレンダー）と DuckDB への保存関数
  - pipeline / etl: 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - news_collector: RSS からの記事収集、前処理、raw_news への保存
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 発注／約定の監査ログテーブル定義と初期化ユーティリティ
  - stats: z-score 正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出＆ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM スコアを合成して市場レジームを判定・保存
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー、ランク付けユーティリティ
- config:
  - settings: 環境変数からの設定読み込み（.env 自動ロード機能付き）

---

## 前提 / 必要環境

- Python 3.10 以上（型ヒントに union 型等を使用）
- 主要依存ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml

実際の requirements ファイルはリポジトリに合わせて用意してください。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして仮想環境を作る:
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要パッケージをインストール（例）:
   ```bash
   pip install duckdb openai defusedxml
   # またはパッケージ配布用に pip install -e .
   ```

3. 環境変数設定:
   プロジェクトルートに `.env` を作成してください（.env.example を参考に）。
   必須環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
   - KABU_API_PASSWORD : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID : Slack チャンネル ID
   オプション / デフォルト:
   - KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL （デフォルト: INFO）
   - KABU_API_BASE_URL : kabu API の base URL（デフォルトは http://localhost:18080/kabusapi）
   - DUCKDB_PATH : デフォルト data/kabusys.duckdb
   - SQLITE_PATH : デフォルト data/monitoring.db

   注意:
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml がある場所）から `.env` を自動で読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - settings オブジェクトで必須変数が未設定だと ValueError が出ます。

4. DB フォルダ作成（必要なら）:
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な API 例）

以下は基本的な利用例です。DuckDB 接続は kabusys.data.jquants_client などで想定している DuckDB と互換性のある接続を渡してください。

- 設定（settings）:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト等
  ```

- 日次 ETL の実行:
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=None)  # None -> 今日（ただし内部処理はルックアヘッドを避ける）
  print(result.to_dict())
  ```

- ニュースセンチメントの算出（OpenAI API キーを環境変数 OPENAI_API_KEY に設定しておく）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジームスコアの算出:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（監査 DB 初期化）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルが作成されます
  ```

---

## ディレクトリ構成

（主要ファイル・パッケージを抜粋）

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
      - news_collector.py
      - quality.py
      - calendar_management.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/  (パッケージ候補 — コードベースに監視用モジュールを想定)
    - research/
    - ai/
  - pyproject.toml / setup.py など（プロジェクトルートに存在する想定）

---

## 設定関連の注意点

- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- settings のバリデーション:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかでなければなりません。
  - LOG_LEVEL は標準のロギングレベル文字列のみ有効です。
- OpenAI 関連:
  - score_news と regime_detector は OPENAI_API_KEY を参照します（引数で上書き可能）。
  - OpenAI 呼び出しはリトライ・バックオフやフェイルセーフ（失敗時はスコア 0 で継続）を備えています。

---

## 開発者向け補足

- ルックアヘッドバイアス対策がコード各所に組み込まれているため、バックテスト用に過去データを取り込む場合は ETL の適切な時点でデータを格納してから分析ループを回してください。
- DuckDB への bulk INSERT は executemany を多用しています。DuckDB のバージョンによっては executemany に空リストを渡せない制約に対応するコードが含まれています。
- external API（J-Quants / OpenAI）呼び出しはテスト容易性のため内部関数をパッチしやすい構造になっています（例: news_nlp._call_openai_api をモック）。

---

## ライセンス / 貢献

ライセンス情報・コントリビューションガイドはリポジトリルートの LICENSE / CONTRIBUTING.md を参照してください（存在する場合）。

---

README に書かれている内容はコードベースと説明の要約です。実行環境の構成や secrets の管理には十分ご注意ください。必要であれば README にサンプル .env.example の雛形や CI / デプロイ手順の追加を行います。