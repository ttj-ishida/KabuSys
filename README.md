# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / RSS / OpenAI 等を活用してデータ収集（ETL）、データ品質チェック、ニュースのAIセンチメント評価、マーケットレジーム判定、ファクター計算、監査ログ管理などを行うモジュール群を含みます。

---

## 主要機能

- 環境変数 / .env 管理
  - プロジェクトルートから `.env` / `.env.local` を自動読み込み（優先度: OS 環境変数 > .env.local > .env）
  - 自動読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
- データ取得・ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPXマーケットカレンダーの差分取得・保存（ページネーション対応・冪等保存）
  - レート制限 / リトライ / トークン自動リフレッシュ対応
- データ品質チェック（quality）
  - 欠損・スパイク・重複・日付不整合チェックの一括実行
- カレンダー管理（market_calendar）
  - 営業日判定、前後営業日の取得、期間内営業日リストの取得
  - JPX カレンダーの夜間バッチ更新ジョブ
- ニュース収集（RSS）
  - RSS フィード取得、前処理、SSRF 対策、トラッキングパラメータ除去、raw_news テーブルへの冪等保存
- AI ベース解析
  - ニュースセンチメント解析（OpenAI: gpt-4o-mini を利用、JSON mode）
  - マクロニュース + ETF MA200 による市場レジーム判定（bull / neutral / bear）
  - API 呼び出しのリトライ / フォールバックロジック
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ（DuckDB）
  - 発注の冪等キー・トレーサビリティ設計
- Research ツール
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化

> 補足: パッケージ上位レベルでは `strategy`, `execution`, `monitoring` を公開していますが、今回のコードベースの一部には実装が含まれていません。これらは戦略実行や監視側のモジュールとして想定されています。

---

## 動作要件

- Python 3.10 以上（`|` 型ヒント / 一部最新構文を使用）
- 主な依存ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリのみで実装されている箇所も多数あります（urllib 等を使用）。

依存関係はプロジェクトの requirements.txt / pyproject.toml に合わせてください。

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール（例: requirements.txt がある場合）
   ```
   pip install -r requirements.txt
   ```
   または開発中に編集したい場合は editable install:
   ```
   pip install -e .
   ```

4. 必要な環境変数を設定
   - 環境変数は OS 環境、`.env.local`、`.env` の順で読み込まれます（OS > .env.local > .env）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API パスワード（kabuステーション用）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（AI処理実行時に使用）
   - データベースパス（任意、デフォルト有り）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

5. サンプル `.env`（プロジェクトルートに配置）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

以下は主要ユースケースの最小例（Python スクリプト内で実行）。

- DuckDB 接続の作成（デフォルトのパスを settings から取得）
  ```py
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行
  ```py
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアを取得して ai_scores に書き込む
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", written)
  ```

- 市場レジーム（日次）をスコアリング
  ```py
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化
  ```py
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit 上でテーブルが作成されます
  ```

- リサーチ系: モメンタム計算例
  ```py
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print("算出銘柄数:", len(records))
  ```

補足:
- OpenAI API を使用する関数は `api_key` 引数で明示的にキーを渡すことができます。引数が None の場合は環境変数 `OPENAI_API_KEY` を参照します。
- 多くの関数はルックアヘッドバイアス防止のために内部で `date.today()` や `datetime.today()` を安易に参照しない設計になっています。テスト時は対象日を明示してください。

---

## 環境変数の自動読み込みの挙動

- 自動ロードはパッケージ import 時に行われます（`kabusys.config`）。
- 読み込み優先順位:
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env（未設定のキーを補完）
- 自動ロードを無効化するには、起動前に環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・ディレクトリ構成を抜粋で示します:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント解析（OpenAI）
    - regime_detector.py       — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント、保存ロジック
    - pipeline.py              — ETL パイプライン / run_daily_etl 等
    - etl.py                   — ETLResult 再エクスポート
    - calendar_management.py   — マーケットカレンダー管理
    - news_collector.py        — RSS 収集・前処理
    - quality.py               — データ品質チェック
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Value/Volatility 等
    - feature_exploration.py   — forward returns / IC / summary / rank
  - (strategy/, execution/, monitoring/) — 上位公開名として存在する想定（未実装部分あり）

各モジュールは DuckDB 接続を受け取り SQL＋Python で処理を行う設計です（外部発注 API に直接触れないモジュールも多く、テストがしやすくなっています）。

---

## ロギング・エラー処理

- 各モジュールは標準 logging を利用して情報/警告/エラーを出力します。`LOG_LEVEL` 環境変数でログレベルの設定が可能です（`DEBUG/INFO/WARNING/ERROR/CRITICAL`）。
- AI / 外部 API 呼び出しはリトライ・フォールバックの仕組みを持ち、致命的な失敗を避ける設計（例: OpenAI 呼び出し失敗時はスコアを 0.0 にフォールバックする等）です。

---

## テスト / 開発メモ

- 外部 API 呼び出し部分（OpenAI / J-Quants / HTTP）はモックしやすい設計になっています（内部 `_call_openai_api` 等はテストで patch 可能）。
- ETL の結果は ETLResult で集約され、品質チェックの結果も把握できます。
- DuckDB を用いるため、ローカルで軽量にデータ処理を実行できます（":memory:" でインメモリ DB も利用可能）。

---

以上が README の概要です。必要であれば以下も作成します:
- requirements.txt の推奨内容
- サンプル .env.example ファイル
- よくあるトラブルシュート（OpenAI レート制限、J-Quants 認証エラーなど）

どれを追加しますか？