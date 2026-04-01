# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。ETL、ニュースNLP（LLM）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどの機能を提供します。

主な想定用途：
- J-Quants API からのデータ収集（株価・財務・市場カレンダー）
- ニュースを用いた銘柄センチメント評価（OpenAI）
- ETF とマクロニュースを組み合わせた市場レジーム判定
- リサーチ用ファクター計算と特徴量解析
- 監査トレース（シグナル→発注→約定）のための DuckDB スキーマ

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API と実行例）
- 環境変数（.env）
- ディレクトリ構成

---

プロジェクト概要
- パッケージ名: kabusys
- 目的: 日本株自動売買システムのためのデータプラットフォーム、NLP/LLM ベースのシグナル生成補助、リサーチ用ツール群を提供すること。
- 設計方針（コード内注記より）
  - ルックアヘッドバイアスを防ぐ（target_date ベースの設計、datetime.today() の不使用）
  - DuckDB を中心としたローカル DB 管理（冪等保存・トランザクション制御）
  - 外部 API 呼び出しはリトライ / バックオフ、レート制限、フェイルセーフを実装
  - LLM 呼び出しは JSON mode を使い、レスポンス検証を厳密に行う

---

機能一覧
- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）、必須設定の検証（kabusys.config.settings）
- Data（kabusys.data）
  - J-Quants クライアント（fetch / save）：株価日足、財務、上場情報、マーケットカレンダー
  - ETL パイプライン（日次差分 ETL、バックフィル、品質チェック）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar update job）
  - ニュース収集（RSS → raw_news、SSRF 対策、トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（Z-score 正規化）
- AI（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとにニュースを集約して OpenAI でセンチメントを算出、ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM を合成して market_regime テーブルに保存
- Research（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリー
- 監視・実行（パッケージ内に監視用設定が存在、監視閾値や pid ファイルパスを settings で管理）

---

セットアップ手順（ローカル開発向け）
前提：Python 3.10 以上を推奨（| 型アノテーション使用、from __future__ annotations）

1. リポジトリをチェックアウト
   - 例: git clone <repo>

2. 仮想環境を作成・起動
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が無い場合は最低限以下を入れてください:
     - duckdb
     - openai
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml

   （プロジェクトで別途 requirements を用意している場合はそちらを利用してください）

4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

5. 環境変数 / .env を用意
   - プロジェクトルート（.git や pyproject.toml がある場所）に .env を置くと自動ロードされます。
   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

主要な環境変数（.env 例）
以下は主要なキー。プロジェクトによって追加の設定が必要です。

- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C0123456789
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

注意:
- settings 内で必須（_require）となっている環境変数があり、未設定だと ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。

---

使い方（コード例）
以下の例は Python REPL やスクリプトから実行します。日付には datetime.date オブジェクトを渡してください。

- 共通: DB 接続の取得
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- ETL（日次 ETL を実行）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニューススコアリング（OpenAI 必須）
  from kabusys.ai.news_nlp import score_news
  cnt = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {cnt} codes")

- 市場レジーム判定（OpenAI 必須）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,3,20))
  # market_regime テーブルに書き込まれる

- 監査 DB 初期化（監査ログ用の DuckDB を作る）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # 以後 audit_conn を使って監査テーブルへ書き込み可能

- 設定の参照
  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)

備考
- OpenAI 呼び出しを含む処理（score_news, score_regime）は OPENAI_API_KEY が必要です。api_key を明示的に引数で渡すことも可能。
- J-Quants API を呼ぶ ETL 系は JQUANTS_REFRESH_TOKEN（リフレッシュトークン）による認証が必須です。
- ETL は複数ステップ（calendar → prices → financials → quality checks）で例外を適切にハンドリングしつつ継続します。結果は ETLResult に集約されます。

---

ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py
  - 環境変数ロード / settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py         — ニュースの集約・LLM スコアリング、ai_scores への書込
  - regime_detector.py  — ETF (1321) MA200 とマクロニュースで市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ等）
  - etl.py                 — ETL インターフェース再エクスポート
  - pipeline.py            — 日次 ETL パイプライン（run_daily_etl 等）
  - stats.py               — zscore_normalize 等の統計ユーティリティ
  - quality.py             — データ品質チェック（欠損・重複・スパイク・日付整合性）
  - audit.py               — 監査ログ（DDL / 初期化関数）
  - jquants_client.py      — J-Quants API クライアント（fetch/save 等）
  - news_collector.py      — RSS 収集と raw_news への保存
- research/
  - __init__.py
  - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー / ランク変換

（補足）その他ファイル
- プロジェクトルートに .env / .env.local / .env.example を配置して利用
- settings はプロジェクトルートを .git または pyproject.toml から検索して .env を自動ロードします

---

運用上の注意
- LLM/API 呼び出しはレート制限・コストが発生します。開発環境では API 呼び出しをモックするか KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境を固定してください。
- DuckDB に対する executemany の空パラメータ等、DuckDB 特有の挙動に注意（実装内で考慮済み）。
- 監査スキーマは冪等（IF NOT EXISTS）で作成されますが、init_audit_schema の transactional オプションは呼び出し環境のトランザクション状況に注意して切り替えてください。
- ニュース取得は SSRF 対策を実装していますが、運用で追加ソースを指定する場合は URL の妥当性を確認してください。

---

トラブルシューティング / 開発時のヒント
- テストや一時的に .env 自動ロードを無効にしたい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しをユニットテストで差し替えたい場合、ニュース・レジームモジュール内の _call_openai_api を patch してモックできます（コードにパッチ想定）。
- DuckDB の接続先は settings.duckdb_path によるデフォルト（data/kabusys.duckdb）を使うのが簡単です。

---

ライセンス / 貢献
- 本 README にはライセンス情報が含まれていません。実際のリポジトリの LICENSE を参照してください。
- 貢献手順やコードスタイルはリポジトリの CONTRIBUTING.md を参照してください（ある場合）。

---

以上が簡易 README です。実行例や環境変数のテンプレート（.env.example）などをリポジトリに追加すると、初期セットアップがさらにスムーズになります。必要であれば README に含める具体的なコマンド例や .env.example のテンプレートを作成します。どの程度の詳細を追加しますか？