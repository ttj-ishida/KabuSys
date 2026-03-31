# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリ（KabuSys）。  
ETL、データ品質チェック、ニュース収集・NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）など、量的運用システムで必要となる主要コンポーネントを提供します。

---

目次
- プロジェクト概要
- 主な機能
- 必要条件
- セットアップ手順
- 環境変数（.env）
- 使い方（主要ユースケース例）
- ディレクトリ構成
- 注意事項

---

## プロジェクト概要

KabuSys は日本株運用向けに設計された内部ライブラリ群です。J-Quants API からのデータ取得・差分 ETL、DuckDB を使ったデータ保存、ニュース RSS 収集と OpenAI（LLM）によるニュースセンチメント評価、ETF ベースの市場レジーム判定、ファクター計算・特徴量探索、そして発注フローを追跡するための監査ログ（audit）スキーマの初期化・管理などを含みます。

設計上の特徴：
- ルックアヘッドバイアス回避（内部で date.today()/datetime.today() に依存しない実装方針）
- 冪等性（ETL／保存処理は ON CONFLICT / upsert により冪等）
- フェイルセーフ：外部サービス（OpenAI、J-Quants）失敗時でもシステム全体が止まらない設計
- DuckDB を中心に軽量にデータを処理

---

## 主な機能

- データ取得・ETL
  - J-Quants からの株価（OHLCV）・財務データ・マーケットカレンダーの差分取得（pagination 対応）
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - ETL 結果を表す ETLResult クラス

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック

- ニュース収集・前処理
  - RSS 取得・クリーンアップ・記事 ID の冪等生成（URL 正規化 + SHA-256）
  - SSRF 対策、レスポンスサイズ制限、XML の安全パース（defusedxml）

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（gpt-4o-mini を想定）
  - バッチ処理・リトライ、レスポンスバリデーション
  - score_news(conn, target_date, api_key=None) を提供

- 市場レジーム判定（AI + ETF MA）
  - ETF（1321）の 200 日移動平均乖離とマクロニュース LLM センチメントを重み合成して（日次）レジーム判定
  - score_regime(conn, target_date, api_key=None)

- 監査ログ（audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
  - init_audit_schema / init_audit_db

- 研究用ユーティリティ
  - ファクター計算（momentum/value/volatility）、将来リターン計算、IC（情報係数）、Z スコア正規化等

---

## 必要条件

- Python 3.10 以上（型 | 記法を使用）
- 必須パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）
- J-Quants のリフレッシュトークンや OpenAI API キーなど外部サービスの認証情報

実行環境により追加の依存がある可能性があります。setup/requirements をプロジェクトに合わせて調整してください。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. インストール
   - 開発中にローカル編集しながら使う場合:
     ```
     pip install -e .
     ```
   - 必要パッケージ（例）:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数の設定
   プロジェクトルートに `.env` を作成するか、OS 環境変数で設定します（下記参照）。

5. DuckDB データベースの準備
   デフォルトでは `data/kabusys.duckdb` を使用するように設定されています（環境変数で上書き可）。

---

## 環境変数（.env）

config.Settings クラスで参照される主な環境変数：

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

AI 関連:
- OPENAI_API_KEY: OpenAI API 呼び出しに使用（score_news / score_regime など）。関数呼び出し時に api_key を渡すことも可能。

自動 .env ロード:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を検出）から `.env`、`.env.local` を自動で読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要ユースケース例）

以下は簡単な Python からの利用例です。各例は duckdb 接続を渡して実行します。

注意: 実行前に必要な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続を作る（ファイルパスは設定に合わせてください）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを生成（OpenAI API キーは環境変数または api_key 引数で渡す）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB データベースを初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成されます。
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))
  volatility = calc_volatility(conn, target_date=date(2026,3,20))
  ```

- カレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
  ```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（抜粋）と簡単な説明です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント評価（OpenAI 呼び出し、batch, retry, validation）
    - regime_detector.py     — ETF MA + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）、ETLResult
    - jquants_client.py      — J-Quants API クライアント／保存ロジック
    - news_collector.py      — RSS ニュース収集・前処理（SSRF 対策、XML 安全パース）
    - calendar_management.py — 市場カレンダー管理、営業日判定、calendar_update_job
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py               — Z スコア等の統計ユーティリティ
    - etl.py                 — ETL 型の再エクスポート
    - audit.py               — 監査ログスキーマ作成 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

---

## 注意事項 / 運用上のヒント

- API キー取り扱い:
  - OPENAI_API_KEY や J-Quants トークンは安全に管理してください。CI/CD や本番環境ではシークレットストアの利用を推奨します。

- 自動 .env ロード:
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索して .env を読み込みます。テスト時に自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- LLM 呼び出し:
  - gpt-4o-mini を使用する前提のプロンプト・レスポンス処理が組まれています。API レスポンスのバリデーションとリトライ（5xx/429/タイムアウト等）を実装済みですが、コストやレート制限に注意してください。

- DuckDB の互換性:
  - DuckDB のバージョン差異により executemany の挙動やリスト型バインドが変わることがあります。pipeline/news_nlp 等で空の executemany を避けるチェックを行っていますが、本番環境で使う DuckDB バージョンを固定すると安全です。

- ルックアヘッドバイアス:
  - コードはバックテストや研究でのルックアヘッドを避ける方針で設計されています。target_date を明示して呼ぶ使い方を推奨します。

---

貢献やバグ報告は Pull Request / Issue で受け付けてください。README にない追加の使い方やサンプルが必要であれば教えてください。