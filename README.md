# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
データの ETL（J-Quants からの取得→DuckDB 保存）、ニュースの収集・AI によるセンチメント評価、ファクター計算、監査ログ（発注・約定トレース）などを含むモジュール群を提供します。

---

## 主な概要

- 設計思想：ルックアヘッドバイアス防止、冪等性、フェイルセーフ（API失敗時やデータ欠損時に安全に継続）、DuckDB を中心とした軽量なオンプレ/クラウドローカルデータ基盤。
- 対象：日本株のデータ取得・前処理・研究・自動売買基盤の構築・運用向け。
- 推奨 Python バージョン：3.10 以上（| 型ヒント等を使用）。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート .git または pyproject.toml を基準）
  - 必須環境変数チェック（settings オブジェクト）
- データ ETL（kabusys.data.pipeline）
  - J-Quants API からの株価・財務・カレンダー差分取得（ページネーション対応、レートリミット管理、リトライ）
  - DuckDB への冪等保存（ON CONFLICT / INSERT … DO UPDATE）
  - 品質チェック（欠損・スパイク・重複・日付不整合検出）
  - 日次パイプライン run_daily_etl
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、前処理、raw_news / news_symbols への冪等保存
  - SSRF / Gzip-Bomb / トラッキングパラメータ対策を実装
- AI 関連（kabusys.ai）
  - ニュースセンチメント: news_nlp.score_news（gpt-4o-mini を利用した JSON Mode）
  - 市場レジーム判定: regime_detector.score_regime（ETF 1321 の MA とマクロニュースを合成）
  - OpenAI 呼び出しにリトライやエラーハンドリング実装
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（DuckDB）
  - トレーサビリティを保証する設計（UUID・冪等キー・UTC タイムスタンプ）

---

## セットアップ手順

1. リポジトリをクローン／パッケージをインストール
   - 開発環境でソースから使う場合（プロジェクトルートで）:
     - python >=3.10 を用意
     - pip install -e . （パッケージ化されている場合）
     - もしくは必要な依存だけ入れる:
       pip install duckdb openai defusedxml

2. 必要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注系）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知（任意だが多くの運用で必須）
   - OPENAI_API_KEY: OpenAI 呼び出し（news_nlp / regime_detector を使う場合）
   - 任意:
     - KABU_API_BASE_URL（kabuAPI の base URL、デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB デフォルト data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

   .env ファイル例（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   ```

3. .env 自動ロードについて
   - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して .env → .env.local を読み込みます。
   - OS 環境変数は優先され、.env は既存の環境変数を上書きしません（.env.local は上書き可）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（代表的な呼び出し例）

※ いずれも事前に必要な環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等）を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（AI）スコアを計算して ai_scores に保存する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```
  - OPENAI_API_KEY は環境変数または api_key 引数で渡せます。

- 市場レジーム判定の実行例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する例:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.db")
  # conn を使って発注監査テーブルへアクセスできます
  ```

- カレンダー更新バッチを実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn, lookahead_days=90)
  print("保存件数:", saved)
  ```

注意点：
- AI 関連関数は OpenAI の API を呼び出します。API キーと利用料に注意してください。
- DuckDB に対する executemany は空リストを与えるとエラーになる箇所があるため、関数側で空チェック済みです（ライブラリの実装参照）。

---

## 設定（settings）について

kabusys.config.settings オブジェクトから各種設定を参照できます。主なプロパティ：

- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url
- settings.slack_bot_token / settings.slack_channel_id
- settings.duckdb_path / settings.sqlite_path
- settings.env（development, paper_trading, live）
- settings.log_level
- settings.is_live / is_paper / is_dev

未設定の必須変数は読み取り時に ValueError を送出します。

---

## ディレクトリ構成（主なファイル）

（src/kabusys 以下を示します）

- kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント / 保存ロジック
    - pipeline.py                      — ETL パイプライン（run_daily_etl 他）
    - etl.py                           — ETLResult の再エクスポート
    - news_collector.py                — RSS ニュース収集
    - calendar_management.py           — 市場カレンダー管理
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py               — ファクター計算（momentum/value/volatility）
    - feature_exploration.py           — forward returns, IC, summary, rank

---

## 開発・運用上の注意

- Look-ahead バイアス対策：
  - 実装は内部で date.today()/datetime.today() を極力参照せず、呼び出し側が target_date を渡す設計の箇所が多いです。バックテストや再現性のために target_date を明示的に指定してください。
- 冪等性：
  - データ保存は基本的に ON CONFLICT / DO UPDATE を用い冪等性を保っています。
- エラーハンドリング：
  - ネットワークリトライ、API レート制御、失敗時のフォールバック（例: AI レスポンス解析失敗時はスコア 0.0 で継続）といった防御的実装が行われています。
- ロギング：
  - settings.log_level でログレベルを制御します。運用時は適切に設定してください。

---

## 依存ライブラリ（主なもの）

- duckdb
- openai
- defusedxml
- 標準ライブラリ（urllib, json, datetime, logging, 等）

パッケージ管理ファイル（requirements.txt / pyproject.toml）がある場合はそちらを参照してください。

---

## サポート / 貢献

- バグレポートや機能追加は PR / Issue を通じてお願いします。  
- 大きな設計変更を提案する場合は事前に Issue で概要を共有してください。

---

README に記載されていない詳細な API 仕様や内部設計（DataPlatform.md / StrategyModel.md 相当）はそれぞれのモジュールの docstring を参照してください。必要であれば README に追記しますので、追加で欲しい内容（例：具体的な ETL スケジュール例、Slack 通知設定例、kabuAPI 発注フローのサンプル等）を教えてください。