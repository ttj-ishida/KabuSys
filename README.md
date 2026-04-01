# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、データ品質チェック、ニュース収集・NLP（LLM評価）、市場レジーム判定、ファクター計算、監査ログなどを提供します。

主な目的は「バックテスト・リサーチ環境と運用環境で共通に使える堅牢なデータ処理／判定ロジック」をライブラリ化することです。

---

## 機能一覧

- 環境変数・設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラップ（settings オブジェクト）

- データ取得・ETL（J-Quants API）
  - 株価日足、財務データ、上場銘柄情報、JPX カレンダーの取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - レート制限・リトライ・401 自動リフレッシュ対応

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック
  - 問題は QualityIssue オブジェクトで収集（Fail-Fast ではなく集約報告）

- カレンダー管理（JPX）
  - 営業日判定 / 前後営業日検索 / 期間内営業日取得
  - 夜間バッチで J-Quants から差分取得・保存

- ニュース収集
  - RSS フィードの取得と前処理（URL正規化、SSRF対策、サイズ制限）
  - raw_news / news_symbols への冪等保存

- ニュースNLP（LLM）
  - 複数銘柄のニュースをバッチで OpenAI に送信して銘柄ごとのセンチメントを ai_scores に保存
  - JSON Mode（厳密JSON）を利用、リトライ/フォールバックあり

- 市場レジーム判定
  - ETF（1321）の200日移動平均乖離 + マクロニュースのLLMセンチメントを合成して日次で 'bull'/'neutral'/'bear' を算出
  - DuckDB への冪等書き込み

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（スピアマン）、ファクターサマリ、Zスコア正規化

- 監査・トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - すべて UTC タイムスタンプ保存、冪等に初期化可能

---

## 必要条件 / 前提

- Python 3.10+（型注釈で | を使用するため 3.10 以上を想定）
- 推奨パッケージ（最低限）
  - duckdb
  - openai (OpenAI の v1 SDK を想定、OpenAI クライアントの OpenAI クラスを使用)
  - defusedxml
  - （運用時）requests や slack_sdk 等、別モジュールで必要なら追加
- ネットワークアクセス（J-Quants / OpenAI / RSS）および適切な API キー

---

## 環境変数（主なもの）

アプリ設定は環境変数から取得します。自動で .env / .env.local をプロジェクトルートから読み込みます（無効化可: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API のパスワード（kabu 関連モジュール利用時）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI API キー（news_nlp/regime_detector 等で必要）

オプション・例:
- KABUSYS_ENV — development / paper_trading / live（既定: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（既定: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視DB等（既定: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

.env のパースはシェルの export 形式、クォート、行末コメントなどを考慮した独自実装です。

---

## セットアップ手順（例）

1. リポジトリをクローン / 作業ディレクトリへ移動

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば）
   - pip install -r requirements.txt

4. .env を作成（.env.example を参考に必要なキーを設定）
   例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABU_API_PASSWORD=yourpassword
   KABUSYS_ENV=development
   ```

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な例）

前提: 環境変数を設定し、依存パッケージをインストール済みとする。

- DuckDB 接続を作り日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアを付与する（ai_scores へ書き込む）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数から OPENAI_API_KEY を読む
  print(f"scored {count} codes")
  ```

- 市場レジーム判定を行う（market_regime テーブルへ）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリ自動作成
  ```

- RSS を取得（ニュースコレクタのユーティリティ単体利用）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- LLM 呼び出し（OpenAI）は JSON Mode を期待しています。API エラー時は安全にフォールバックする実装がありますが、API キーは必須です。
- 各関数は「ルックアヘッドバイアス」を避ける設計（内部で date.today() を参照しない等）になっています。バックテスト用途でも安全に使えるよう設計されています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env の自動ロード、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM センチメント付与（ai_scores へ保存）
    - regime_detector.py — マクロセンチメント＋ETF MA200 乖離で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - pipeline.py — ETL パイプラインのエントリ（run_daily_etl など）
    - etl.py — ETL 結果用の型再エクスポート（ETLResult）
    - news_collector.py — RSS 収集 / 前処理 / 保存ロジック
    - quality.py — データ品質チェック（QualityIssue を返す）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - calendar_management.py — JPX カレンダー管理・営業日判定
    - audit.py — 監査ログ（signal_events / order_requests / executions）DDL と初期化
  - research/
    - __init__.py
    - factor_research.py — momentum/value/volatility 等ファクター計算
    - feature_exploration.py — 将来リターン、IC、rank、factor_summary 等
  - （パッケージの __all__ に strategy, execution, monitoring が示されるが、
     この README 作成時点ではコード断片に含まれていないモジュールがある可能性があります）

---

## 開発・運用上の注意

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。CI やテストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し・J-Quants API 呼び出しは外部ネットワークに依存します。テストでは各呼び出し関数（内部の _call_openai_api や _urlopen 等）をモックすることを想定しています。
- DuckDB に対する executemany に空リストを渡すと互換性の問題があるため、ライブラリ側で空チェックを行っています。アプリ側でも同様の注意をしてください。
- 監査ログは削除しない前提（ON DELETE RESTRICT 等）で設計されています。データ保持ポリシーに注意してください。

---

この README はコードベースの主要モジュールから要点をまとめたものです。実装の詳細や API 仕様は各モジュール（src/kabusys/**/*.py）を参照してください。必要なら利用例・CLI スクリプト・テスト手順を別途追加します。