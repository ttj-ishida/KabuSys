# KabuSys

日本株向けのデータプラットフォーム＆自動売買補助ライブラリ。  
J-Quants からのデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを一貫して提供します。

---

## 主な機能

- ETL（データ取得・保存）
  - J-Quants API から株価日足、財務データ、マーケットカレンダーを差分取得して DuckDB に冪等保存
  - 差分更新／バックフィル対応、ページネーション対応、トークン自動リフレッシュ、レートリミット制御
- データ品質チェック
  - 欠損、重複、将来日付、スパイク（前日比）などのチェックと QualityIssue レポート
- ニュース収集・NLP スコアリング
  - RSS 取得（SSRF 対策・サイズ制限・前処理）→ raw_news に保存
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメント分析（ai_scores）およびマクロニュースを使った市場レジーム判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman ランク相関）、統計サマリー、Zスコア正規化
- カレンダー管理（JPX）
  - 営業日判定、前後営業日の取得、カレンダー差分更新ジョブ
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを確保するテーブル群と初期化関数
- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）

---

## 動作要件

- Python 3.10+
- 主な外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他、標準ライブラリのみで実装されている箇所も多数）

実際の環境では pyproject.toml / requirements に従って必要パッケージをインストールしてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成 & 有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

3. 依存関係をインストール
   - pyproject.toml / requirements.txt がある前提で以下など：
   ```bash
   pip install -e .
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みは既定で有効）。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

   必要となる主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite パス（監視用、デフォルト: data/monitoring.db）
   - KABUSYS_ENV: environment（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

   簡単な .env の例：
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主な例）

前提: DuckDB 接続を作成し、settings を利用する方法。

- 基本的な接続準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア算出（OpenAI 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（ETF 1321 + マクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")  # :memory: も可
  ```

- 研究用: モメンタム等の計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

---

## 注意点 / 設計上のポイント

- Look-ahead bias（ルックアヘッドバイアス）を防ぐ設計が随所に組み込まれています：
  - 関数は内部で datetime.today() を参照せず、必ず target_date を引数で受け取ります。
  - J-Quants 等から取得したデータには fetched_at を付与し「いつ知り得たか」を明示します。
- OpenAI API 呼び出しはリトライやフォールバック（失敗時にスコア 0.0）を行い、処理の頑健性を高めています。
- DuckDB へ保存する際は冪等（ON CONFLICT DO UPDATE / DO NOTHING）でデータの再投入に耐えます。
- RSS の収集は SSRF・XML Bomb・レスポンスサイズ上限などのセキュリティ対策が実装されています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py        — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存）
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - etl.py                    — ETL 結果クラス再エクスポート
    - news_collector.py         — RSS ニュース取得・前処理
    - quality.py                — データ品質チェック
    - calendar_management.py    — JPX カレンダー管理（営業日判定等）
    - stats.py                  — 共通統計ユーティリティ（zscore 等）
    - audit.py                  — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py        — Momentum / Volatility / Value 等
    - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - monitoring/, strategy/, execution/ （パッケージ公開はされているが実装は別ファイル群に依存）

（上記はコードベースの主要なファイルを抜粋したものです）

---

## 環境変数の自動読み込み

- プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` がある場合、自動で読み込まれます。
- 読み込み順序: OS 環境変数 > .env.local (override=True) > .env (override=False)
- 自動読み込みを無効にするには:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## テスト・開発時のヒント

- AI 関連や外部 API 呼び出しはテストでモックする設計になっています（例: news_nlp._call_openai_api を patch）。
- DuckDB をインメモリで使えばファイルの作成を不要にしてユニットテストを書けます（db_path=":memory:"）。
- ETL の各ステップは独立しているため、パイプラインを部分的に実行して問題箇所を切り分けられます。

---

## ライセンス / 貢献

- （ここにプロジェクトのライセンスやコントリビューションガイドを追記してください）

---

README には以上です。必要なら「セットアップ手順を CI 用スクリプトに落とし込む例」や「よく使う SQL スキーマ定義（raw_prices / ai_scores 等）」を追記できます。どの追加情報が欲しいか教えてください。