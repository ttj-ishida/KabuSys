# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォームと調査・AI 支援を組み合わせた自動売買／リサーチ基盤です。J-Quants・kabuステーション・各種ニュースソース・OpenAI（LLM）と連携し、ETL、データ品質チェック、ニュースセンチメント計算、マーケットレジーム判定、ファクター計算、監査ログなどを提供します。

---

## 主な特徴

- J-Quants API からの差分 ETL（株価日足 / 財務 / JPX カレンダー）と DuckDB への冪等保存
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と記事前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）スコアリング
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）
- 研究用ファクター計算モジュール（Momentum / Volatility / Value 等）と統計ユーティリティ（Z-score 等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ初期化ユーティリティ
- 設定は環境変数 / .env(.local) で管理。自動ロード機能あり

---

## 必要条件

- Python 3.10+
- 推奨ライブラリ（インストール例は下段参照）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで事足りる部分が多いですが、上記は明示的に使用します）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化：

   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール（最低限）：

   ```
   pip install duckdb openai defusedxml
   # または開発モードでインストール
   pip install -e .
   ```

   ※ 実プロジェクトでは requirements.txt / poetry 等で依存管理してください。

3. 環境変数の設定（.env / .env.local をプロジェクトルートに配置）

   主要な環境変数（最低必要なもの）：
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
   - KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト development）
   - LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")（デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

   .env 読み込みの優先度:
   - OS 環境変数 > .env.local > .env
   - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベースフォルダ作成（必要に応じて）:

   ```
   mkdir -p data
   ```

---

## 使い方（主要ユースケース）

以下は代表的な Python スニペットです。プロジェクトルートで仮想環境が有効な状態で実行してください。

- 設定取得と DuckDB 接続:

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）スコアリング（OpenAI必須）:

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- マーケットレジーム判定（ETF 1321 を使う）:

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用データベース初期化:

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダーや営業日ユーティリティ:

  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 研究用ファクター計算:

  ```python
  from kabusys.research import calc_momentum, zscore_normalize
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

---

## 設定（config）について

モジュール: `kabusys.config.Settings` 経由で環境変数を参照します。主なプロパティ：

- settings.jquants_refresh_token → JQUANTS_REFRESH_TOKEN
- settings.kabu_api_password → KABU_API_PASSWORD
- settings.kabu_api_base_url → KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- settings.slack_bot_token → SLACK_BOT_TOKEN
- settings.slack_channel_id → SLACK_CHANNEL_ID
- settings.duckdb_path → DUCKDB_PATH (Path オブジェクト)
- settings.sqlite_path → SQLITE_PATH (Path オブジェクト)
- settings.env → KABUSYS_ENV (development | paper_trading | live)
- settings.log_level → LOG_LEVEL
- settings.is_live / is_paper / is_dev

注意: 環境変数が未設定の場合、必須項目は ValueError が発生します。

---

## トラブルシューティング

- OpenAI API キー・J-Quants トークン未設定で LLM / データ取得が失敗します。環境変数を確認してください。
- DuckDB ファイルへの書き込み権限が必要です。パスや権限を確認してください。
- 自動 .env 読み込みを無効にしたいとき: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API はレート制限があります。jquants_client 内で固定間隔制御・リトライが実装されていますが、過度の並列呼び出しは避けてください。
- NewsCollector は RSS のサイズ・リダイレクト先のプライベート IP 等を制限しています。外部サイトの RSS を加える場合は URL が公開されているか確認してください。

---

## 主要ディレクトリ構成（src/kabusys）

- __init__.py
  - パッケージのエクスポート: data, strategy, execution, monitoring（将来的に利用）
- config.py
  - 環境変数 / .env ロード、Settings クラス
- ai/
  - __init__.py
  - news_nlp.py: ニュースの LLM スコアリング（銘柄別 ai_scores への書き込み）
  - regime_detector.py: マーケットレジーム判定（ETF + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得・保存・認証・レート制御）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - calendar_management.py: マーケットカレンダー管理・営業日ロジック
  - news_collector.py: RSS 収集・前処理・raw_news保存
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py: z-score など汎用統計ユーティリティ
  - audit.py: 監査ログスキーマ定義と初期化ユーティリティ
  - etl.py: ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py: forward returns, IC, 統計サマリー、rank
- research/* はバックテスト・因子研究で利用する関数群

---

## 開発メモ / 設計上のポイント

- Look-ahead bias を避ける設計（target_date 未満のデータのみ使用、datetime.today() を直接参照しない等）
- DuckDB をデータストアとして採用（分析向け高速クエリ）
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスのバリデーションを厳格に実施
- ニュース収集における SSRF / XML Bomb 対策（スキーム検証・プライベート IP 検査・defusedxml）
- ETL は冪等に保存（ON CONFLICT DO UPDATE）し、部分的失敗や再実行を想定

---

## 参考 / 付記

- パッケージバージョンは `src/kabusys/__init__.py` の `__version__` を参照 (0.1.0)
- この README はコードベースから主要な使用法・設計を抽出した概要です。実運用時は各モジュール内の docstring・ログを参照してください。

ご希望があれば、README にサンプル .env.example を追加したり、具体的な ETL 運用手順（cron / 異常検知フロー）や CI 用のテスト手順を追記します。必要な追加項目を教えてください。