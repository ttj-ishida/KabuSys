# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買/リサーチ基盤のライブラリ群です。本リポジトリは以下のような機能を提供します：J-Quants からのデータ ETL、ニュース収集と LLM によるニュース/マクロセンチメントスコアリング、ファクター計算・特徴量探索、マーケットカレンダー管理、監査ログ（トレーサビリティ）など。DuckDB をデータレイヤに用い、OpenAI（gpt-4o-mini 等）でテキスト解析を行います。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 型安全な Settings API（`kabusys.config.settings`）

- データ ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・保存
  - レートリミット対応・リトライロジック・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合などを検出（QualityIssue オブジェクトで返却）

- ニュース収集と NLP
  - RSS 取得、前処理、raw_news への保存（SSRF 対策／最大サイズ制限／トラッキングパラメータ除去）
  - OpenAI（JSON mode）を用いた銘柄ごとのニュースセンチメント（ai_scores）算出
  - マクロニュースの LLM 判定を用いた市場レジーム判定（bull/neutral/bear）

- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）算出、Zスコア正規化、統計サマリー

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
  - DuckDB ベースで監査 DB を初期化・管理

---

## 要求環境

- Python 3.10+
- 主要依存パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime 等）を多用

（実際の requirements.txt がある場合はそちらを参照してください。開発環境では Poetry や pip-tools を使用することを推奨します。）

---

## セットアップ手順

1. リポジトリをクローン / コピー

   ```bash
   git clone <this-repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate.bat # Windows
   ```

3. 依存パッケージをインストール（例）

   ```bash
   pip install duckdb openai defusedxml
   ```

   ※ プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。

4. 環境変数の設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると、自動で読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用途）。

   最低限必要な環境変数（主要なもの）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（実行層で使用）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必要な場合）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

   （.env には `.env.example` を参考に必要なキーを記載してください。）

---

## 使い方（主要ユースケース例）

以下はライブラリを直接インポートして使う例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の返り値）を受け取ります。

- DuckDB 接続を作成する例

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）

  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄ごとの ai_scores）を算出して書き込む

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n}")
  ```

- 市場レジーム（マクロ + ETF MA200）をスコアリングして書き込む

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（audit DB）の初期化

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db はテーブルを作成して接続を返します
  ```

- 環境設定（Settings）の利用例

  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## 注意点 / 運用上のポイント

- Look-ahead bias（未来情報漏れ）対策:
  - 各処理は可能な限り target_date 未満のデータのみを参照する・datetime.today() を直接参照しない設計になっています。バックテスト等で使用する場合は ETL 時点で取得済みデータのみを使う運用を推奨します。

- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI の JSON Mode を利用します。API の失敗時はフェイルセーフ（スコア 0.0）で継続する設計ですが、API キーが必須です（引数で注入可）。

- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を自動読み込みします。テスト時などで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB executemany の挙動:
  - 一部の関数は DuckDB のバージョン依存性（executemany に空リストを渡せない等）を考慮して実装されています。DuckDB のバージョン互換性に注意してください（0.10 系を想定した実装）。

---

## ディレクトリ構成（概要）

プロジェクトの主要なファイル/モジュール構成は以下のとおりです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数 / Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュースセンチメント算出（LLM）
    - regime_detector.py           # マクロ + ETF MA200 で市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py       # マーケットカレンダー（営業日判定等）
    - etl.py                       # ETL インターフェース再エクスポート
    - pipeline.py                  # ETL パイプライン実装（run_daily_etl 等）
    - stats.py                     # 統計ユーティリティ（Z スコア等）
    - quality.py                   # データ品質チェック
    - audit.py                     # 監査ログ（テーブル定義・初期化）
    - jquants_client.py            # J-Quants API クライアント（fetch/save など）
    - news_collector.py            # RSS 収集・前処理・保存
  - research/
    - __init__.py
    - factor_research.py           # モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py       # 将来リターン・IC・統計サマリー

（実際のツリーはさらに細分化されたファイルが含まれます）

---

## 開発 / テストについて

- テスト用に環境変数の自動読み込みを無効化できます:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- OpenAI / 外部 API 呼び出しはモック可能な設計になっています（内部の `_call_openai_api` を patch してテストする等）。
- news_collector は外部ネットワークアクセス・RSS パースに対して SSRF 対策や Gzip サイズ上限チェック等を実装しています。テスト時は `_urlopen` をモックしてください。

---

## ライセンス / 貢献

- （この README では具体的なライセンス情報は含めていません。実際のリポジトリでは LICENSE ファイルを参照してください。）
- バグ報告や機能拡張の提案は Issue を立ててください。プルリクエスト歓迎。

---

以上が KabuSys の概要、セットアップ、主要な使い方とディレクトリ構成の説明です。詳細な関数仕様やパラメータは各モジュールの docstring を参照してください。README の内容をプロジェクトに合わせて調整（依存関係ファイルやサンプル .env の追加）することを推奨します。