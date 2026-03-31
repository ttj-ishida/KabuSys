# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ / コンポーネント群です。  
ETL（J-Quants → DuckDB）、ニュース収集とAIセンチメント評価、研究用ファクター計算、監査ログ（発注→約定トレース）、マーケットカレンダー管理などを提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価日足、財務データ、JPX マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル・品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS フィード収集、テキスト前処理、raw_news への冪等保存、記事と銘柄の紐付け
  - SSRF 対策、gzip サイズ制限、トラッキングパラメータ除去などの堅牢化
- AI（LLM）連携
  - ニュースを銘柄単位でまとめ、OpenAI (gpt-4o-mini を想定) でセンチメントスコア化（ai_scores テーブルへ保存）
  - マクロニュースと ETF (1321) の MA200 乖離を合成して市場レジーム（bull/neutral/bear）を判定
  - API 呼び出しに対するリトライ / フェイルセーフロジック
- 研究用 (Research)
  - モメンタム、ボラティリティ、バリューなどのファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - 発注→約定のトレーサビリティを UUID で保持
- マーケットカレンダー管理
  - market_calendar の更新 / 営業日判定 / next/prev trading day 取得

---

## 前提条件

- Python 3.10+（型アノテーションに union 型記法などを使用）
- 主要依存パッケージ（プロジェクトに requirements.txt があることを想定）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API / OpenAI / RSS）

（実行環境に合わせて適宜パッケージやバージョンを固定してください。）

---

## セットアップ手順（開発向け）

1. リポジトリをクローン / ソースを配置

2. 仮想環境を作成・有効化（例）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください。
   ```
   pip install -r requirements.txt
   ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると、自動で読み込まれます（自動ロードはデフォルト有効）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu ステーション API のパスワード（発注連携がある場合）
- SLACK_BOT_TOKEN : Slack通知用（必要に応じて）
- SLACK_CHANNEL_ID : Slack チャンネル ID
- OPENAI_API_KEY : OpenAI API キー（AI 機能を使う場合）

任意（デフォルトあり）
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 をセットすると .env 自動読み込みを無効化
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : SQLite 監視 DB パス（デフォルト data/monitoring.db）
- KABUSYS_ENV による is_live / is_paper フラグが各所で使用されます。

.env の書き方は config モジュールのパーサに準拠（export で始まる行やクォート・コメントをサポートします）。

---

## 使い方（主要な例）

以下は Python REPL / スクリプトからライブラリを利用する最低限の例です。実運用ではログ設定やエラーハンドリング等を適切に行ってください。

- DuckDB 接続を作り ETL を日次実行する（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアを生成する（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数に設定済みであれば api_key=None で動作
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って発注ログ等を記録
  ```

- RSS フィードを取得（ニュースコレクタの fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注:
- AI 呼び出しは OpenAI SDK を利用します。API エラー時のフェイルセーフ（多くの場合 0.0 にフォールバック）やリトライが組み込まれています。
- ETL / API 呼び出し系はネットワーク・認証情報が必要です。実行前に必ず環境変数を設定してください。

---

## 開発・運用上のポイント

- 環境変数自動読み込み
  - パッケージ起点で .env / .env.local をプロジェクトルートから自動ロードします（OS 環境変数が優先、.env.local が .env を上書き）。
  - テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定してください。

- Look-ahead bias の防止
  - AI モジュールや ETL は内部で datetime.today()/date.today() を直接参照しないよう設計されています。常に target_date を明示して呼び出してください。

- リトライとフェイルセーフ
  - J-Quants や OpenAI の API 呼び出しにはリトライと指数バックオフを実装。AI レスポンスパース失敗や API 障害時は安全側の値（0.0 など）で継続する設計です。

- DuckDB への書き込みは冪等（ON CONFLICT ... DO UPDATE）を多用しています。ETL は部分失敗時に既存データを不用意に消さないように配慮されています。

---

## ディレクトリ構成（概要）

（リポジトリ内の src/kabusys を基準に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py               — ニュースセンチメント（銘柄単位）
    - regime_detector.py        — 市場レジーム判定（ETF MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント / DuckDB 保存
    - pipeline.py               — ETL パイプライン / run_daily_etl など
    - etl.py                    — ETL 型や再エクスポート
    - news_collector.py         — RSS 取得・前処理・冪等保存
    - calendar_management.py    — マーケットカレンダー管理 / 営業日判定
    - audit.py                  — 監査ログスキーマ初期化 / init_audit_db
    - quality.py                — データ品質チェック
    - stats.py                  — 統計ユーティリティ（z-score 等）
  - research/
    - __init__.py
    - factor_research.py        — Momentum / Value / Volatility 等の計算
    - feature_exploration.py    — 将来リターン計算 / IC / 統計サマリー

---

## ライセンス / コントリビューション

（このリポジトリの LICENSE 情報やコントリビューションポリシー、CONTRIBUTING.md があれば追記してください）

---

README に記載の内容はコード中の設計コメントや docstring を元にまとめています。実行や本番運用前に、環境依存設定・API キー・DB パスなどを適切に確認して下さい。必要なら、README を環境や CI/CD に合わせてカスタマイズして下さい。