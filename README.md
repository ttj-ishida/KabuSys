# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。ETL（J-Quants 経由の市場データ取得）、ニュース収集・NLP（OpenAI）によるセンチメント評価、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）、マーケットカレンダー管理などを提供します。

バージョン: 0.1.0

---

## 主要な特徴

- データプラットフォーム
  - J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）
  - DuckDB への冪等保存（ON CONFLICT を用いた更新）
  - データ品質チェック（欠損、重複、スパイク、日付整合性）
- ニュース収集と NLP
  - RSS からのニュース収集、前処理、raw_news / news_symbols への保存
  - OpenAI（gpt-4o-mini）の JSON Mode を使った銘柄別センチメント算出（ai_scores）
  - ニュースを使った市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等の定量ファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査テーブルを提供
  - すべての発注フローを UUID で追跡可能にする初期化ユーティリティ
- カレンダー管理
  - market_calendar に基づく営業日判定・next/prev/trading days 取得
  - JPX カレンダーの夜間差分更新ジョブ

---

## 必要条件

- Python 3.10+
- 必要な Python パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml

（実プロジェクトでは requirements.txt / pyproject.toml を用意してください。ここではソースの import から推定した主要依存を挙げています。）

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成して有効化（一例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
   （本リポジトリに `pyproject.toml` / `requirements.txt` がある場合はそれを使ってください。）

4. 環境変数設定
   - プロジェクトルートに `.env`（あるいは `.env.local`）を作成して必要な環境変数を設定します。
   - 自動読み込み: `kabusys.config` はプロジェクトルート（.git か pyproject.toml を起点）を探索して `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   重要な環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（実運用時）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - OPENAI_API_KEY: OpenAI 呼び出し用（`score_news` / `score_regime` は引数で上書き可）
   - KABUSYS_ENV: {development, paper_trading, live}
   - LOG_LEVEL: {DEBUG, INFO, WARNING, ERROR, CRITICAL}

5. データベース用ディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的なユースケース）

以下は簡単な Python スニペット例です。各関数の引数はソースコードの docstring を参照してください。

- DuckDB 接続を用意
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（J-Quants からデータ取得・保存・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントの算出（OpenAI API キーを環境変数または引数で与える）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # APIキーを引数で渡すことも可能（None なら環境変数 OPENAI_API_KEY を参照）
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"wrote {n_written} ai_scores")
  ```

- 市場レジーム判定（MA200 とマクロニュースの合成）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブル等が作成されます
  ```

- カレンダー関係ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
  ```

注意:
- OpenAI 呼び出しは API レートや料金に注意して行ってください。`score_news` / `score_regime` は内部でリトライ・失敗フォールバックの実装がありますが、API キーの設定やコスト管理は運用者で行ってください。
- 実際の発注・execution モジュールはこのコードベースの一部である可能性がありますが、実際に資金を動かす際は paper_trading / live 環境分離、テストが必須です。

---

## 設定（環境変数）一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN — 必須（ETL 用）
- KABU_API_PASSWORD — 必須（kabuステーション API を使う場合）
- KABU_API_BASE_URL — 任意（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- OPENAI_API_KEY — OpenAI 呼び出し用（score_news / score_regime で参照）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 'development' / 'paper_trading' / 'live'（デフォルト 'development'）
- LOG_LEVEL — ログレベル（'INFO' 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化するには 1 を設定

.env ファイルはプロジェクトルート（.git または pyproject.toml を基準）で自動的に読み込まれます。`.env.local` があれば `.env` を上書きで読み込みます。

---

## ディレクトリ構成（主要ファイル）

（この README は src/kabusys 以下の構成に基づく説明です）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定の読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントの収集・API 呼び出し・ai_scores への書き込み
    - regime_detector.py — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集・前処理・保存
    - calendar_management.py — market_calendar 管理、営業日判定
    - stats.py — 汎用統計（zscore_normalize 等）
    - quality.py — データ品質チェック群
    - audit.py — 監査ログテーブル作成 / 初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - その他（将来的に strategy / execution / monitoring モジュールがあることを __all__ に示唆）

---

## 運用上の注意

- ルックアヘッドバイアス対策:
  - 多くの関数は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取ることでバックテストと本番の一貫性を保つ設計になっています。バックテストや再現可能性を確保するため、必ず target_date を明示して呼び出してください。
- OpenAI/API キーはセキュアに管理してください（.env は運用環境での管理に注意）。
- 本コードベースには発注ロジックやブローカー API との統合時の安全措置（例えば二重発注防止の冪等キー等）が含まれますが、実際のライブ運用前には入念な検証・監査を行ってください。
- DuckDB の executemany 等はバージョン差異に影響を受けるため、使用する DuckDB のバージョンで動作確認を行ってください（ソース内に互換性対策の注釈があります）。

---

## さらに詳しく / 貢献

- 各モジュールの関数やクラスには docstring が豊富に記載されています。実装詳細や設計方針はソースコードのコメントを参照してください。
- バグ報告や改善提案は Issue を立ててください。Pull Request での貢献も歓迎します。

---

README に不足している情報（依存パッケージの厳密なバージョン、CI / テスト手順、パッケージ配布設定等）が必要であれば、手元の環境情報や配布方針に基づいて追記します。どの点を優先して追記しましょうか？