# KabuSys

日本株向けのデータパイプライン・リサーチ・AI支援・監査ログを備えた自動売買サブシステム群です。  
ETL（J-Quants からのデータ取得）、ニュース収集とLLMによるニュース解析、マクロレジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J‑Quants API から株価日足（OHLCV）、財務データ、JPXカレンダーを差分取得・保存（DuckDB）
  - 差分更新 / バックフィル / ページネーション対応 / トークン自動リフレッシュ
- データ品質管理
  - 欠損、重複、スパイク（急騰・急落）、将来日付や非営業日データの検出
- ニュース収集 & NLP
  - RSS フィード取得（SSRF対策・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（ai_scores テーブルへ書き込み）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 + LLM 合成）
- リサーチ / ファクター処理
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB クエリ）
  - 将来リターン計算 / IC（Spearman） / 統計サマリー / Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル等のスキーマ定義・初期化（DuckDB）
  - order_request_id による冪等化、UTC タイムスタンプ保持
- 環境設定
  - .env ファイルおよび環境変数からの設定読み込み（自動ロード、優先順位: OS 環境 > .env.local > .env）
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## セットアップ手順（開発 / 実行環境）

前提:
- Python 3.10 以上（型アノテーションや union 型表記を使用）
- Git がインストールされていること（プロジェクトルート検出に使用）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作る（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   - このコードベースで利用されている主要ライブラリ:
     - duckdb
     - openai
     - defusedxml
   例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに setup/requirements ファイルがあればそちらを利用してください: `pip install -e .` 等）

4. 環境変数（.env）を設定
   - プロジェクトルートに `.env` または `.env.local` を作成します。自動ロードが有効であれば起動時に読み込まれます（ただし OS の環境変数が優先）。
   - 主要な設定項目（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KABUSYS_ENV=development  # development | paper_trading | live
     - LOG_LEVEL=INFO

   自動読み込みを無効にするには:
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. データディレクトリを準備（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な利用例）

以下は Python REPL やスクリプトから呼び出す例です。DuckDB 接続を作り、ETL／スコアリング／監査DB初期化などを実行できます。

- 日次 ETL（株価／財務／カレンダー取得と品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメントをスコア化して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```
  - OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要。

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログDBの初期化（独立した監査DBを用いる場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn に対して監査テーブルが作成される
  ```

- ファクター計算（research）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

- デバッグ / ログレベルは環境変数 LOG_LEVEL で制御できます（DEBUG/INFO/WARNING/...）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン。jquants_client.get_id_token に使用。
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で利用）。
- KABU_API_PASSWORD (必須) — kabuステーションAPI用パスワード。
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト "http://localhost:18080/kabusapi"）。
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用。
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID。
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）。
- SQLITE_PATH — 監視用 SQLite パス（data/monitoring.db）。
- PID_FILE_PATH — プロセス監視用 PID ファイルパス。
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視しきい値（%）。
- KABUSYS_ENV — 環境指定: "development" / "paper_trading" / "live"。
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化。

config.Settings クラス経由でこれらにアクセスできます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## 推奨運用フロー（簡易）

- バッチ（cron / systemd timer）で日次 ETL を実行。
- ETL 後にニューススコアとレジーム判定を実行して、戦略評価用データを更新。
- 監査ログ（order_requests / executions）用に別 DuckDB を用意し、発注系処理から利用。
- OpenAI 呼び出しはコストとレートリミットを考慮しバッチ実行。失敗はフェイルセーフ（多くの箇所で 0.0 フォールバックやスキップを採用）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env 自動読み込みロジック含む）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（score_news）
  - regime_detector.py — マクロセンチメント + ETF MA による市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J‑Quants API クライアント（fetch / save / token管理 / レートリミット）
  - pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL 結果クラス再エクスポート
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py — RSS 収集と前処理（SSRF対策、記事ID生成）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- ai 以外に monitoring, execution, strategy 等のパッケージが __all__ 指定されている想定（現在のコードベースでは上記中心）。

---

## 注意点 / 設計方針の要点

- ルックアヘッドバイアス防止:
  - 日付計算は target_date を明示的に渡す設計（datetime.today()/date.today() を内部依存しない箇所が多い）。
  - 取得時の fetched_at を UTC で記録。
- フェイルセーフ:
  - LLM 呼び出しや外部APIが失敗した場合は多くのケースで中立値（0.0）やスキップで継続。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE / INSERT … ON CONFLICT ロジックで冪等化。
  - 発注側は order_request_id による冪等制御を想定。
- セキュリティ:
  - RSS 取得で SSRF 対策（リダイレクト検査 / プライベートIPチェック）や defusedxml を利用。

---

## よくある操作（サンプル）

- .env.example（簡易）
  ```
  JQUANTS_REFRESH_TOKEN=REPLACE_ME
  OPENAI_API_KEY=REPLACE_ME
  KABU_API_PASSWORD=REPLACE_ME
  SLACK_BOT_TOKEN=REPLACE_ME
  SLACK_CHANNEL_ID=REPLACE_ME
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO
  ```

- cron による日次実行（例: 毎朝 3:30）
  ```
  30 3 * * * /path/to/venv/bin/python -c "import duckdb; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect('data/kabusys.duckdb'); run_daily_etl(conn)"
  ```

---

README に未記載の詳細な API 使用方法や設定はコード中の docstring（各モジュール先頭のコメント）を参照してください。その他、実運用にあたっては OpenAI / J‑Quants の利用規約・レート制限、APIキーの管理にご注意ください。