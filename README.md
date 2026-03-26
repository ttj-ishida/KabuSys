# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
ETL（J-Quants）・ニュース収集・LLMによるニュースセンチメント・市場レジーム判定・研究用ファクター計算・監査ログなど、トレーディングシステム構築に必要なコンポーネントを提供します。

バージョン: 0.1.0

---

## 主要な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPXマーケットカレンダーを差分取得・保存（DuckDB）
  - 差分取得／バックフィル、ページネーション、トークン自動リフレッシュ、レートリミット制御
- ニュース収集
  - RSS フィード取得、前処理（URL除去、トラッキングパラメータ削除、SSRF対策）、raw_news / news_symbols への冪等保存
- ニュースNLP（LLM）
  - OpenAI（gpt-4o-mini）を使った銘柄毎のニュースセンチメント算出および ai_scores への保存（バッチ／リトライあり）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離 + マクロニュース LLM スコアを合成して日次レジーム（bull/neutral/bear）を算出
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン計算、IC（Spearman）計算、Zスコア正規化など
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
- 監査ログ（audit）
  - signal → order_request → executions の監査テーブル定義と初期化処理（DuckDB）
- 設定管理
  - .env または環境変数を自動読み込み（プロジェクトルート検知）し、必要な設定を Settings オブジェクトとして提供

---

## セットアップ手順

推奨: Python 3.10+ の仮想環境を作成してから以下を実行してください。

1. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（最低限の依存）
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ 実プロジェクトでは pyproject.toml / requirements.txt があればそちらを利用してください。

3. リポジトリをパッケージとしてインストール（開発時）
   ```bash
   pip install -e .
   ```
   （プロジェクトルートに pyproject.toml がある前提のコマンド例）

4. 環境変数 / .env の準備  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限必要な環境変数（本プロジェクトで参照される主なキー）:
   - JQUANTS_REFRESH_TOKEN：J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY：OpenAI API キー（score_news / score_regime 使用時に必須）
   - KABU_API_PASSWORD：kabu ステーション API のパスワード（本システムの一部で使用）
   - SLACK_BOT_TOKEN：Slack 通知用 Bot トークン（通知機能がある場合）
   - SLACK_CHANNEL_ID：Slack チャンネル ID
   - DUCKDB_PATH：デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH：監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV：環境 ("development" / "paper_trading" / "live")
   - LOG_LEVEL：ログレベル ("DEBUG","INFO",...)

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主なコード例）

以下はライブラリの代表的な利用例です。

- DuckDB 接続を作る：
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（市場カレンダー更新 → 株価・財務取得 → 品質チェック）:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを生成して ai_scores に書き込む:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定を実行:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- 設定を参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- LLM（OpenAI）呼び出しを行う関数は API キーを引数で渡すこともできます（引数を省略すると環境変数 OPENAI_API_KEY を使用）。
- 時刻や日付の取り扱いはルックアヘッドバイアス対策が施されており、内部で date.today() 等を不用意に使用しない設計になっています（関数には target_date を明示的に渡すことを推奨します）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（LLM）
    - regime_detector.py       — 市場レジーム判定（MA + マクロLLM）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント・保存処理
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult の再エクスポート
    - news_collector.py        — RSS ニュース収集
    - calendar_management.py   — マーケットカレンダー管理（営業日判定 他）
    - stats.py                 — 汎用統計ユーティリティ（zscore 等）
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py       — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py   — 将来リターン・IC・統計サマリー 等

---

## 注意事項 / 運用上のヒント

- 環境変数の自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読み込みします。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に有用）。
- OpenAI の呼び出し
  - レートや料金に注意してください。失敗時はフェイルセーフ（ゼロスコア）で継続する実装です。
- J-Quants
  - API レートリミット（120 req/min）を遵守するための内部 RateLimiter が実装されています。ID トークンの自動リフレッシュにも対応しています。
- データベース
  - デフォルトの DuckDB ファイルは `data/kabusys.duckdb`。監査ログ専用 DB を分けて運用することを推奨します。
- テスト
  - LLM 呼び出しや外部 I/O はモックしやすいよう内部呼び出しを分離しています（ユニットテストで差し替え可能）。

---

## ライセンス / コントリビューション

この README はコードベースの説明を目的として自動生成されています。実際のライセンス・コントリビューション規約はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

---

何か追加で README に載せたい情報（例: 実運用での Cron ジョブ例、Slack 通知の使い方、SQL スキーマ定義のリンクなど）があれば教えてください。README の補足や英語版も作成できます。