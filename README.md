# KabuSys — 日本株自動売買 / データプラットフォームライブラリ

## プロジェクト概要
KabuSys は日本株の自動売買プラットフォームおよびデータ基盤を目的とした Python パッケージです。本リポジトリはデータ ETL、ニュース収集・NLP、ファクター算出、研究ユーティリティ、監査ログ（トレーサビリティ）などの機能群をモジュール化して提供します。主要な設計方針は以下の通りです。

- ルックアヘッドバイアスを避ける（日時依存処理の禁止、データ取得条件の明確化）
- DuckDB を用いたローカルデータストア（冪等保存）
- J-Quants API との連携（レート制御・トークン自動リフレッシュ）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（冗長性・フォールバック実装）
- 監査ログ（signal → order_request → execution）の完全トレース

## 主な機能
- 環境設定管理（.env 自動読み込み、必要な環境変数の取得）
- データ ETL
  - 日次 ETL（株価 / 財務 / 市場カレンダー）
  - 差分取得、バックフィル、品質チェック
- J-Quants API クライアント
  - 株価日足、財務データ、上場情報、マーケットカレンダー取得
  - レート制限、リトライ、401 トークン自動リフレッシュ対応
- ニュース収集
  - RSS フィード取得、URL 正規化、SSRF 対策、記事保存処理
- ニュース NLP（AI）
  - 銘柄別ニュースセンチメント算出（ai_scores へ保存）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定
  - OpenAI 呼び出しはリトライ・バリデーション・フォールバックあり
- 研究支援ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）の算出、Zスコア正規化
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログスキーマ初期化（DuckDB 用テーブル・インデックス）

## セットアップ手順（クイックスタート）
1. リポジトリをクローン／チェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 本コードベースで使用される外部依存の例:
     - duckdb
     - openai
     - defusedxml
   - requirements.txt があればそれを使うか、以下のように手動インストールしてください。
   ```
   pip install duckdb openai defusedxml
   ```
   （実際の requirements はプロジェクトに合わせて調整してください）

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local がある場合はより優先）。
   - 自動ロードを無効にする場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 主要な環境変数（必須・任意）については次節を参照。

## 環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（execution 関連）

- 任意（デフォルト値あり）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（監視 / 実行制御用）
  - KABUSYS_ENV: environment ("development", "paper_trading", "live")（デフォルト development）
  - LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト INFO）

注意: config.Settings は .env 自動読み込みロジックを持ちます。必要な値が未設定だと明示的に ValueError を投げます。

## 使い方（代表的なコード例）

- 共通準備
  ```python
  import duckdb
  from kabusys.config import settings
  ```

- DuckDB 接続（デフォルトパスを利用）
  ```python
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日の日付が使われます（内部的な調整あり）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を生成して ai_scores テーブルへ書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  cnt = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None の場合は OPENAI_API_KEY 環境変数を使用
  print(f"Scored {cnt} codes")
  ```

- 市場レジーム判定（ETF1321 の MA とマクロニュースを組み合わせる）
  ```python
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログスキーマ初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ニュース RSS 取得（個別ユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

- 研究用ユーティリティ（例: モメンタム算出）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 設定値参照（コード内）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path, settings.env, settings.log_level)
  ```

注意点:
- OpenAI 呼び出しは gpt-4o-mini を想定しており、レスポンスのバリデーションとフォールバック（失敗時は中立スコア）を行います。
- J-Quants クライアントはレート制限（120 req/min）を尊重する実装と、401 発生時のトークン自動更新を持ちます。
- ETL や AI 処理は外部 API 呼び出しを含むため、API キーとネットワークが必要です。

## ディレクトリ構成
（抜粋: 主要ファイル・モジュールを示します）

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
      - etl.py (pipeline の公開ラッパー)
      - news_collector.py
      - calendar_management.py
      - stats.py
      - quality.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (パッケージ候補; README に無いが __all__ に含められている可能性あり)
    - strategy/ (戦略・モデル関連モジュールの想定)
    - execution/ (発注制御のためのモジュールの想定)

具体的なファイル一覧（主要ファイル）:
- src/kabusys/config.py — 環境設定読み込み・バリデーション
- src/kabusys/data/jquants_client.py — J-Quants API クライアント／保存ロジック
- src/kabusys/data/pipeline.py — 日次 ETL 実行ロジック（run_daily_etl 等）
- src/kabusys/data/news_collector.py — RSS 収集・正規化
- src/kabusys/ai/news_nlp.py — ニュースセンチメント算出ロジック
- src/kabusys/ai/regime_detector.py — 市場レジーム判定
- src/kabusys/research/* — ファクター計算、IC、統計ユーティリティ
- src/kabusys/data/audit.py — 監査ログスキーマ初期化

## 開発者向けメモ / 設計上の注意
- ルックアヘッドバイアス防止のため、内部で datetime.today() / date.today() を無制限に参照しない設計が各モジュールで意識されています。バックテスト用途では明示的に target_date を渡してください。
- OpenAI 呼び出しはテスト容易性のために内部呼び出し関数を patch して置き換え可能です（ユニットテストのモック化対象）。
- DuckDB の executemany の挙動（空リストが不可等）を考慮した実装があります。DB 操作は冪等（ON CONFLICT）を念頭に置いてください。
- セキュリティ: news_collector は SSRF 対策、XML パースに defusedxml を使用、RSS ペイロードの上限バイト数制限等を実装しています。

## ライセンス・貢献
- ライセンス情報や開発ルール（コントリビュート方法、コードスタイル等）はリポジトリのトップレベルに配置された LICENSE / CONTRIBUTING.md を参照してください（本 README には含まれていません）。

---

この README はコードベースの主要機能と使い方の要点をまとめたものです。詳細な API（関数引数、戻り値、例外）は各モジュールの docstring を参照してください。追加で利用例や運用手順（デプロイ、cronジョブ例、監視設定など）が必要であれば教えてください。