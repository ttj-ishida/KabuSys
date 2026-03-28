# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、品質チェック、研究用ファクター計算、ニュースのLLMによるセンチメント評価、監査ログ（監査テーブル）などを統合的に提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 動作要件
- 環境変数（設定）
- セットアップ手順
- 使い方（簡易サンプル）
  - DuckDB 接続の初期化
  - 日次 ETL 実行
  - ニュースセンチメント付与（AI）
  - 市場レジーム判定（AI）
  - 監査DB初期化
- ディレクトリ構成
- 開発・テストのヒント
- 注意事項

---

## プロジェクト概要
KabuSys は日本株の自動売買・リサーチ基盤として設計された Python パッケージです。J-Quants API 等からマーケットデータ、財務データ、マーケットカレンダー、RSS ニュースを取得して DuckDB に蓄積し、品質チェック・ファクター計算・LLM を用いたニュースセンチメント評価・市場レジーム判定・監査ログ管理などの機能を提供します。バックテストや本番運用のためのデータプラットフォーム／研究ツールとして利用できます。

---

## 主な機能
- J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レートリミット）
- 日次 ETL パイプライン（市場カレンダー、株価日足、財務データ）
- raw_news（RSS）収集・前処理・銘柄紐付け（SSRF対策、トラッキングパラメータ削除、gzip対応）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 研究ユーティリティ（モメンタム／バリュー／ボラティリティなどのファクター計算、将来リターン、IC計算、Zスコア正規化）
- LLM を用いたニュースNLP（gpt-4o-mini など、JSON Mode を想定）による銘柄別スコアリング
- LLM を用いた市場レジーム検出（ETF 1321 の MA200 とマクロニュースの組合せ）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- DuckDB ベースの冪等保存ロジック（ON CONFLICT DO UPDATE 等）

---

## 動作要件
- Python 3.10 以上（ユニオン型 `|` を利用）
- 必要な主なライブラリ（例）:
  - duckdb
  - openai （OpenAI SDK）
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード、OpenAI API）

パッケージ依存はプロジェクト毎に requirements.txt / pyproject.toml で管理する想定です。

---

## 環境変数（設定）
KabuSys は環境変数（または .env / .env.local）から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に利用する環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 関連処理で使用）
- DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視用途など）
- KABUSYS_ENV: 環境 ("development", "paper_trading", "live")（デフォルト development）
- LOG_LEVEL: ログレベル ("DEBUG", "INFO", ...)

.env ファイルのパースは Bash 風の簡易仕様に対応（export プレフィックス、クォート、行末コメントなど）。

---

## セットアップ手順（ローカル開発向け / 例）
1. リポジトリをクローン
   - git clone ...
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール（例）
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトの requirements.txt / pyproject.toml に従ってインストール
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、シェルでエクスポート
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C12345678
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development
5. （任意）DuckDB 用データディレクトリを作成
   - mkdir -p data

---

## 使い方（簡易サンプル）

以下は Python REPL / スクリプトからの利用例です。事前に上記環境変数を設定してください。

- DuckDB 接続を作る / ETL を実行する
  - from datetime import date
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026,3,20))
    print(result.to_dict())

- ニュースセンチメントを生成する（ai.news_nlp）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を参照

- 市場レジームを判定する（ai.regime_detector）
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を参照

- 監査データベースの初期化
  - import duckdb
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/monitoring.duckdb")
    # conn は監査ログ用の DuckDB 接続（UTC タイムゾーンに設定済み）

- J-Quants API から株価を直接取得する（低レベル）
  - from kabusys.data.jquants_client import fetch_daily_quotes
    records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,1))
    # 保存は save_daily_quotes(conn, records)

注意:
- AI 関連（score_news / score_regime）は OpenAI API を使用します。API キーは引数に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- 多くの関数は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。

---

## ディレクトリ構成（主要ファイル）
プロジェクトの主要モジュールは src/kabusys 以下に配置されています。主な構成は以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定管理（.env 自動読み込みロジック含む）
  - ai/
    - __init__.py
    - news_nlp.py  — ニュースの LLM スコアリング（ai_scores へ書込）
    - regime_detector.py  — ETF MA200 とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - etl.py  — ETLResult の再エクスポート
    - news_collector.py  — RSS 収集と前処理（SSRF 対策・gzip 等）
    - calendar_management.py  — 市場カレンダー管理（営業日判定）
    - quality.py  — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py  — Zスコア正規化等の統計ユーティリティ
    - audit.py  — 監査ログ（テーブル／インデックス定義、初期化）
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility ファクター
    - feature_exploration.py — 将来リターン・IC・統計サマリー 等

（上記は主要ファイルのみの抜粋です。詳細は src/kabusys 以下を参照してください。）

---

## 開発・テストのヒント
- OpenAI / ネットワーク呼び出しのある関数は内部の API 呼び出しヘルパーをモックしてテストできます。実装内にモックポイント（例: kabusys.ai.news_nlp._call_openai_api）があります。
- .env の自動読み込みはプロジェクトルートの判定に .git または pyproject.toml を使用します。テスト時に自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany は空リストを渡すとエラーになるバージョンがあるため、実装は空チェックを行っています。テスト用にインメモリ DB を使う場合は `duckdb.connect(":memory:")` を使用できます。

---

## 注意事項
- OpenAI / J-Quants などの外部 API を使う処理は課金やレート制限の対象です。API キー管理・呼び出し頻度には注意してください。
- 本ライブラリの一部は本番注文・取引系と連携する前提の設計が含まれます（監査ログ、order_requests 等）。実際の発注ロジックや証券会社 API 連携部分はここに含まれていないか、別モジュールで実装する必要があります。
- LLM を使ったスコアリングは外部APIの挙動やプロンプトに依存するため、結果の検証・監査が重要です。
- DuckDB に保存される全 TIMESTAMP は UTC を前提とした設計になっています（監査DB 初期化時に TimeZone を UTC に固定する実装あり）。

---

README に記載の情報はコードベースのコメント／実装に基づく要約です。詳細な利用法や追加のコマンドは実際のリポジトリのドキュメント（.env.example、DataPlatform.md / StrategyModel.md 等）やソースコードの docstring を参照してください。