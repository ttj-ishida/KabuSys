# KabuSys

日本株向けのデータ基盤・研究・自動売買サブシステム群を集めたライブラリコレクションです。  
主に J-Quants / kakabu 等のデータを取り込み、ETL・品質チェック・ファクター計算・ニュースのAI分析、監査ログ（発注トレース）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の領域をカバーするモジュール群を含みます。

- データ取得・ETL（J-Quants API 経由の株価・財務・マーケットカレンダー）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集・前処理・LLM による銘柄別センチメントスコア化
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価の合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計）
- 監査ログ（signal → order_request → executions を辿れる DB スキーマ）
- 環境変数 / 設定管理（.env 自動読み込みなど）

設計上の要点:
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない設計）
- DuckDB を主なローカル DB として利用
- OpenAI（gpt-4o-mini）を JSON mode で利用する実装（リトライ・フォールバックあり）
- 冪等性（保存処理は ON CONFLICT で上書き）とログの完全性を重視

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（トークン自動リフレッシュ、レートリミット、retry）
  - ニュース収集（RSS 取得、防SSRF、前処理、raw_news 保存）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - マーケットカレンダー操作（営業日判定、next/prev/get_trading_days）
  - 監査ログスキーマ / 初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとにまとめて LLM に投げ、ai_scores を更新
  - regime_detector.score_regime: ETF(1321) の MA100/200 指標とマクロニューススコアの合成で市場レジームを判定・保存
- research/
  - factor_research: momentum, value, volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）、統計サマリー、rank 関数
- config.py
  - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml で判定）
  - settings オブジェクト経由で設定を取得

---

## セットアップ手順（開発環境向け）

前提:
- Python 3.10+ を推奨（type union 表現等を利用）
- DuckDB を使用するのでネイティブ拡張が不要な pip パッケージを利用

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 例（requirements.txt が無い場合の最低限）:
     - pip install duckdb openai defusedxml

   実際にはプロジェクトに合わせて追加パッケージが必要です（logging 等は標準ライブラリ）。

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config.py）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN     （J-Quants 用リフレッシュトークン）
   - SLACK_BOT_TOKEN           （Slack 通知を使う場合）
   - SLACK_CHANNEL_ID          （Slack 通知対象チャンネル）
   - KABU_API_PASSWORD         （kabu API を使う場合）
   オプション / デフォルトあり:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
   - LOG_LEVEL (DEBUG/INFO/...)

   .env の例（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB データベースの初期化（監査ログ用など）
   - Python から init_audit_db を呼び出すと必要なテーブルを作成します（UTC タイムゾーンをセット）。
   - 例:
     ```python
     import kabusys.data.audit as audit
     conn = audit.init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な例）

以下はライブラリをプログラムから利用する基本例です。実行は Python スクリプトやジョブで行います。

- 日次 ETL を実行する（duckdb 接続を渡して run_daily_etl を呼ぶ）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date を省略すると今日が対象（ただし設計上は明示が推奨）
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリングを実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込み銘柄数: {n}")
  ```

- 市場レジーム判定を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

- 監査ログスキーマの初期化（別 DB で管理する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

注意:
- OpenAI API を利用するメソッド（score_news, score_regime 等）は OPENAI_API_KEY 別途必要です（引数で注入可）。
- DuckDB のスキーマ（raw_prices, raw_financials, raw_news, ai_scores, market_regime など）が存在する前提で動作します。ETL で自動作成/挿入を行いますが、初期スキーマはプロジェクトの別のスクリプトで定義されているはずです（必要に応じて schema 初期化をご確認ください）。

---

## 典型的な運用フロー例

1. 毎晩 ETL ジョブを実行（run_daily_etl）
2. ETL 後にデータ品質チェックを実行し、警告/エラーを Slack へ通知
3. ニュース収集 → score_news で銘柄スコア更新
4. 研究ジョブでファクターを計算・正規化（zscore_normalize）→ シグナル生成
5. シグナルを audit.signal_events に記録 → order_requests に冪等キーで登録 → ブローカーへ送信
6. 約定を executions に取り込み、トレースを保持

---

## 環境設定・ヒント

- config.Settings は .env ファイル（プロジェクトルートの .env / .env.local、OS 環境変数）から読み込みます。優先順位: OS 環境 > .env.local > .env。
- テスト時に自動 .env 読み込みを無効にしたい場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB のパスは Settings.duckdb_path から取得できます（デフォルト data/kabusys.duckdb）。
- OpenAI 呼び出しはリトライ・フォールバック（失敗時は 0.0 を返す等）を備えていますが、API キーを適切に管理してください。
- news_collector は RSS の SSRF 対策（リダイレクト時の検査、プライベートホスト拒否）や受信サイズ制限を実装しています。

---

## ディレクトリ構成

主要なファイル・モジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュースの LLM スコアリング
    - regime_detector.py            # マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント、保存ロジック
    - pipeline.py                   # ETL パイプラインと run_daily_etl
    - etl.py                        # ETL 主要インターフェース（ETLResult 再エクスポート）
    - news_collector.py             # RSS 取得・前処理
    - quality.py                    # データ品質チェック
    - stats.py                      # zscore_normalize 等の統計ユーティリティ
    - calendar_management.py        # 市場カレンダーの管理（営業日判定等）
    - audit.py                      # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            # momentum/volatility/value 等
    - feature_exploration.py        # forward_returns, calc_ic, factor_summary, rank

各モジュールには docstring に設計方針や処理フローが詳細に書かれているので、実装を読みながら理解を深めてください。

---

## ライセンス / 責任

- 本 README はコードベースの構造と利用方法の概要をまとめたものです。実運用では API キー・証券会社接続・発注ロジックに関して十分なテストとリスク管理を行ってください。
- 実際の売買に用いる場合は paper_trading モード等で十分に検証した上で live モードに移行してください（KABUSYS_ENV 設定）。

---

もし README に追加したい項目（例: CI / テスト手順、具体的なスキーマ DDL、requirements.txt の内容、サンプル .env.example）などがあれば教えてください。必要に応じて追記します。