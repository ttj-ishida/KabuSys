KabuSys — 日本株自動売買 / データプラットフォーム
================================================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。本コードベースは以下の機能群を提供します。

- データ収集・ETL（J-Quants API 経由の株価・財務・市場カレンダー）
- ニュース収集と NLP による銘柄別センチメントスコアリング（OpenAI）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM 評価の融合）
- 研究用ファクター計算・特徴量解析（モメンタム、バリュー、ボラティリティ、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ初期化
- ニュース収集（RSS）と安全対策（SSRF 対策、トラッキング除去、サイズ制限）

特徴（抜粋）
-------------
- Look-ahead bias 対策が設計上に組み込まれている（target_date を明示、datetime.now の乱用を回避）
- ETL は差分更新・バックフィルをサポートし冪等保存を行う
- J-Quants API 呼び出しに対してレート制御・リトライ・トークン自動リフレッシュを実装
- OpenAI 呼び出しは JSON モード + 再試行・サニティチェックを実装（レスポンスの堅牢な検証）
- DuckDB を中心に設計（ローカルな分析・監査ログ保存に適合）
- RSS 収集で SSRF や XML 攻撃へ対策済み

必要な環境・依存
----------------
- Python 3.10+
  - ソース内で union 型（X | Y）等を使用しているため 3.10 以降が必要です。
- 外部パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- （任意/運用による）Slack 連携用ライブラリ等

簡単なセットアップ例
-------------------
1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （運用時に必要な追加パッケージがあれば別途インストール）

3. 環境変数（.env）を準備
   - プロジェクトルートに .env / .env.local を配置すると自動で読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（コード内 Settings を参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack Bot トークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 利用時）
   - その他（デフォルト値あり／任意）:
     - KABU_API_BASE_URL（既定: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（既定: data/kabusys.duckdb）
     - SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL 等

例 .env（最小）
---------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=xxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

基本的な使い方（コード例）
-------------------------

DuckDB 接続の用意（ファイル DB）
- import duckdb
- conn = duckdb.connect("data/kabusys.duckdb")

ETL（日次全体）
- from kabusys.data.pipeline import run_daily_etl
- from datetime import date
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- print(result.to_dict())

ニューススコアリング（ai/news_nlp）
- from kabusys.ai.news_nlp import score_news
- from datetime import date
- written = score_news(conn, target_date=date(2026, 3, 20))
- print(f"書き込み銘柄数: {written}")

市場レジーム判定（ai/regime_detector）
- from kabusys.ai.regime_detector import score_regime
- from datetime import date
- score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または api_key 引数で渡す

監査ログスキーマ初期化
- from kabusys.data.audit import init_audit_db
- audit_conn = init_audit_db("data/audit.duckdb")  # 帳票用 DB を初期化して接続を返す

研究用ファクター計算 / 解析
- from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
- from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
- 各関数に conn と target_date を渡して利用

運用・ジョブ例
- calendar_update_job(conn) を夜間バッチで実行して market_calendar を更新
- run_daily_etl を毎朝実行して価格・財務・カレンダーを差分取得
- score_news を夜間に実行して ai_scores を更新
- score_regime を ETL 後に実行して市場レジームを算出

設計上の注意点（重要）
---------------------
- Look-ahead bias: 多くの関数は target_date を引数で受け取り、内部で datetime.today() や date.today() を参照しない設計。バックテストでは必ず適切な target_date を渡してください。
- OpenAI 呼び出し: API エラーやパース失敗時は fail-safe としてデフォルト値（0.0 等）にフォールバックする設計ですが、キー未設定時は ValueError を送出します。
- J-Quants API: リトライ・レート制御・トークン自動リフレッシュ等を実装していますが、運用時は API 制限などを確認してください。
- DuckDB executemany の制約（空リスト不可）に対応するため、保存処理で空チェックを行っています。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                — ニュースセンチメント & score_news
  - regime_detector.py         — 市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py     — マーケットカレンダー管理・判定ロジック
  - etl.py                     — ETL インターフェース
  - pipeline.py                — 日次 ETL パイプライン / run_daily_etl
  - stats.py                   — 統計ユーティリティ（zscore_normalize）
  - quality.py                 — データ品質チェック
  - audit.py                   — 監査ログスキーマ初期化 / init_audit_db
  - jquants_client.py          — J-Quants API クライアント（fetch / save）
  - news_collector.py          — RSS 収集（SSRF/サイズ対策）
  - etl.py (再エクスポート)    — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py         — Momentum/Value/Volatility 計算
  - feature_exploration.py     — 将来リターン, IC, rank, factor_summary
- その他（strategy / execution / monitoring 等のパッケージは __init__ で公開予定）

開発・貢献
-----------
- コードのスタイルやテストはプロジェクト方針に従ってください（未記載部分は PR で相談）。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml がある階層）を基準に探索します。テスト時等は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。

付録: よく使う API のサンプル（短縮）
---------------------------------
- ETL 実行:
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.data.pipeline import run_daily_etl
  - run_daily_etl(conn)

- ニューススコア:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date)

- レジームスコア:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date)

- 監査 DB 初期化:
  - from kabusys.data.audit import init_audit_db
  - init_audit_db("data/audit.duckdb")

問い合わせ
---------
実装や利用上の質問は README を元に issue / PR を作成してください。README にない運用のベストプラクティスや追加の運用スクリプトは別途ドキュメント化を推奨します。

---  
以上がこのコードベースの概要と利用方法のまとめです。必要であれば、README に加える実行スクリプト例（systemd や cron 用）や CI 設定、詳しい .env.example のテンプレートも作成します。どの情報を補足しますか？