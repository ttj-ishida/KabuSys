# KabuSys

日本株向け自動売買／データ基盤ライブラリ KabuSys のリポジトリ README。  
このドキュメントはコードベース（src/kabusys 以下）をもとに、プロジェクト概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（ETL）、データ品質チェック、ニュース NLP による銘柄センチメント評価、マーケットレジーム判定、研究用のファクター計算、および監査ログ（発注〜約定のトレース）などを含む一連のコンポーネントを備えた自動売買 / データプラットフォーム向けの Python ライブラリです。

設計上の特徴:
- DuckDB を主なデータストアとして使用（オンプレ／ファイルDBを想定）
- J-Quants API からの差分取得・保存（レートリミット・リトライ対応）
- ニュースの収集と OpenAI（gpt-4o-mini 等）による JSON モードでのスコアリング
- ルックアヘッドバイアスを避ける日付取り扱い（バックテスト適合）
- ETL・品質チェックは失敗時も全項目を収集する設計（Fail-Fast しない）
- 監査ログでシグナル → 発注 → 約定を UUID で追跡可能にする

パッケージトップ:
- kabusys.__version__ = "0.1.0"
- __all__ に data, strategy, execution, monitoring などのサブパッケージを含む

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - ETL パイプライン run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- データ品質チェック
  - 欠損データ検出（OHLC 欠損）
  - スパイク検出（前日比閾値）
  - 重複チェック（主キー重複）
  - 日付整合性チェック（未来日付・非営業日のデータ検出）

- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 対策、gzip 上限、URL 正規化）
  - raw_news への冪等保存、news_symbols との紐付け

- ニュース NLP / AI スコアリング
  - 銘柄ごとのニュース統合センチメント score_news（OpenAI JSON モードを使用）
  - マクロニュースを用いた市場レジーム判定 score_regime（ETF 1321 の MA + マクロ NLP 合成）

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）
  - IC（Information Coefficient）計算・統計サマリー（calc_ic, factor_summary）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルのスキーマ初期化
  - init_audit_schema / init_audit_db による冪等初期化

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化
  - Settings クラスによる環境変数アクセス（settings.jquants_refresh_token 等）

---

## セットアップ手順（ローカル開発向け）

前提:
- Python 3.10 以上（PEP 604 の | 型などを使用）
- Git およびネットワークアクセス（J-Quants / OpenAI 使用時）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージと依存インストール
   - pip install -e .              # パッケージを開発モードでインストール
   - pip install duckdb openai defusedxml  # 必要な外部依存
   もし requirements.txt / pyproject.toml があればそれに従ってください。

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（および任意で .env.local）を置くと自動ロードされます。
   - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime などで利用）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

   例 .env（抜粋）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方（代表的な例）

以下は Python REPL / スクリプト内での利用例です。実行の前に必要な環境変数を設定してください。

- DuckDB 接続を開く:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- ETL（日次パイプライン）を実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（ai/news_nlp）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーは環境変数 OPENAI_API_KEY に設定済みであること
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"Written scores: {written}")
  ```

- 市場レジーム判定（ai/regime_detector）:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # または既存 conn に対して init_audit_schema(conn)
  ```

- カレンダーヘルパー利用例:
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 環境設定値にアクセス:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.kabu_api_base_url)
  print(settings.is_live)
  ```

注意点:
- OpenAI の呼び出しはレートや API 変化に依存します。テストでは内部の _call_openai_api をモックして置き換える想定です。
- DuckDB の executemany はバージョン依存の挙動があるため、コード内で空リストチェック等を行っています（そのまま利用してください）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの src/kabusys 配下の主な構成:

- src/kabusys/__init__.py
  - パッケージエントリ（version, __all__）

- src/kabusys/config.py
  - .env 自動ロード、Settings クラス（環境変数アクセス）

- src/kabusys/ai/
  - news_nlp.py: ニュース NLP（score_news）
  - regime_detector.py: マクロ + MA による市場レジーム判定（score_regime）
  - __init__.py

- src/kabusys/data/
  - pipeline.py: ETL の中核（run_daily_etl など）
  - jquants_client.py: J-Quants API クライアント（取得 + 保存）
  - calendar_management.py: 市場カレンダーの管理
  - news_collector.py: RSS 収集と前処理
  - quality.py: データ品質チェック（QualityIssue 等）
  - stats.py: 共通統計ユーティリティ（zscore_normalize）
  - audit.py: 監査ログ（schema の初期化 / init_audit_db）
  - etl.py: ETLResult の再エクスポート
  - __init__.py

- src/kabusys/research/
  - factor_research.py: モメンタム/バリュー/ボラティリティ等の計算
  - feature_exploration.py: forward returns / IC / summary / rank
  - __init__.py

- その他（存在する可能性のあるサブパッケージ）
  - strategy, execution, monitoring など（__all__ に列挙）

（上記はコードベース内の主要モジュールの説明です。実際のファイル・追加モジュールはリポジトリを参照してください。）

---

## 運用上の注意・ベストプラクティス

- .env の自動読み込み:
  - プロジェクトルートの .env → .env.local の順で読み込まれます（.env.local が上書き）。
  - OS 環境変数が優先され、.env による上書きを防ぐ仕組みあり。
  - テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- ルックアヘッドバイアス対策:
  - AI スコアリングやファクター計算、ETL は内部で明示的に target_date を受け取り、
    date.today() 等を直接参照しない実装になっています。バックテスト時は target_date を明示してください。

- リトライ・フォールバック:
  - 外部 API（J-Quants / OpenAI）はリトライ・バックオフ処理が組み込まれており、失敗時はフェイルセーフ（部分スキップ）する箇所が多くありますが、運用では監視とアラートを設定してください。

- 監査ログ:
  - 発注系の監査テーブルは削除前提ではなく、履歴保存を目的としています。テーブルスキーマやインデックスは init_audit_schema / init_audit_db で作成してください。

---

## さらに確認する箇所（開発者向け）

- テスト: 各 API 呼び出し（OpenAI / J-Quants / ネットワーク）をモックしてユニットテストを用意することを推奨します。コード内にモックポイント (_call_openai_api, _urlopen 等) があるためテスト容易性が考慮されています。
- 依存管理: pyproject.toml / requirements.txt を確認して適切な OpenAI SDK / duckdb のバージョンを固定してください。
- 運用: 本番運用（live 環境）では KABUSYS_ENV を `live` に設定し、ログレベルや Slack 通知などを適切に設定してください。

---

必要があれば README に以下を追加可能です:
- CI / テスト実行方法
- pyproject.toml / packaging による配布手順
- 具体的な .env.example の完全テンプレート
- 各テーブルスキーマの一覧（DDL 抜粋）
- API レートやコスト見積もり（OpenAI / J-Quants）

追加で欲しい情報があれば（例えば .env.example の完全テンプレートやサンプル DB 初期化スクリプトなど）、教えてください。