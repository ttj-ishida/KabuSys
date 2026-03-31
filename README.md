# KabuSys

日本株向けの自動売買／データプラットフォームライブラリ（KabuSys）。  
J-Quants や RSS／LLM を利用したデータ取得・品質管理・AI スコアリング・リサーチ用ユーティリティを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 基本的な使い方（コード例）
- 環境変数
- ディレクトリ構成

---

プロジェクト概要
----------------
KabuSys は日本株のデータ取得（J-Quants）、ニュース収集、データ品質チェック、特徴量（ファクター）計算、LLM を用いたニュースセンチメント解析／市場レジーム判定、そして監査ログ（発注・約定トレーサビリティ）といった一連の機能を提供する Python ライブラリ群です。  
設計上のポイント：
- ルックアヘッドバイアスに配慮（内部で date.today() を不用意に参照しない等）
- DuckDB をデータ基盤に採用
- J-Quants / OpenAI 呼び出しに対するリトライ・レート制御・フェイルセーフ実装
- ニュース収集における SSRF 防止・XML の安全パースなどセキュリティ考慮

主な機能
--------
- 環境設定読み込み（.env 自動ロード、必須設定チェック）
- J-Quants API クライアント（株価・財務・カレンダー取得、トークン自動リフレッシュ、レート制御）
- ETL パイプライン（差分取得、保存、品質チェック）: run_daily_etl 等
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS -> raw_news、トラッキングパラメータ除去、SSRF 対策）
- LLM ベースのニュースセンチメント解析（銘柄別スコアを ai_scores に保存）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースを組成）
- 研究用ユーティリティ（ファクター計算、forward returns、IC、Z-score 正規化）
- 監査ログスキーマ & 初期化（signal_events, order_requests, executions）
- 実行監視関連の設定（閾値・PID ファイルなど、configs）

セットアップ手順
----------------
1. Python のインストール
   - 推奨: Python 3.10 以上（ソースコードは型ヒントで前提されているため最新版推奨）

2. 依存パッケージのインストール
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip でインストール（プロジェクトに requirements.txt があればそれを利用）
     - 例: pip install duckdb openai defusedxml
   - またはパッケージとしてローカルインストール
     - pip install -e .

3. 環境変数設定
   - ルートに .env や .env.local を置くことで自動ロードされます（デフォルト）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須の環境変数は README 下部の「環境変数」参照。

4. データベース用ディレクトリ作成（必要に応じて）
   - デフォルトの DuckDB パスは data/kabusys.duckdb（settings.duckdb_path）
   - 例: mkdir -p data

基本的な使い方
--------------
以下はライブラリの代表的な API の利用例です。duckdb を利用した接続例を示します。

- ETL（日次パイプライン）実行
```py
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント解析（ai スコアの作成）
```py
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で設定可
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定
```py
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（監査用専用 DB を作る）
```py
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

主な公開 API（代表）
- kabusys.config.settings — 環境設定
- kabusys.data.pipeline.run_daily_etl — 日次 ETL
- kabusys.data.jquants_client.* — J-Quants API 関連（fetch_*/save_*）
- kabusys.data.news_collector.fetch_rss — RSS 取得ユーティリティ
- kabusys.ai.news_nlp.score_news — ニュース NLP スコアリング
- kabusys.ai.regime_detector.score_regime — 市場レジーム判定
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化
- kabusys.research.* — ファクター計算・解析ユーティリティ
- kabusys.data.stats.zscore_normalize — Zスコア正規化

環境変数（主要）
----------------
必須項目（未設定だと ValueError を送出するもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知用（Slack 統合を使う場合）
- SLACK_CHANNEL_ID — Slack 通知用チャンネルID
- KABU_API_PASSWORD — kabu API（kabuステーション）パスワード

任意またはデフォルト値あり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / regime_detector で使用）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）デフォルト data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定

注意点 / 実運用に関する事項
--------------------------
- OpenAI / J-Quants の API 呼び出しはそれぞれレート制御・リトライを行いますが、キーの管理や利用回数には注意してください。
- ETL／AI 処理はルックアヘッドバイアスを避ける設計になっていますが、実運用やバックテストでの利用時は target_date の扱いに注意してください。
- news_collector は SSRF や XML Bomb 対策（defusedxml、ホスト検査、サイズ制限等）を行っていますが、追加のネットワーク／セキュリティポリシーを設定してください。
- DuckDB の executemany 等でバージョン依存の挙動があるため、実行時の DuckDB バージョンに注意してください（コード内で互換性対策あり）。

ディレクトリ構成（主要ファイル）
-----------------------------
（リポジトリ内の src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
    - (その他 ETL 補助モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（統計/因子研究ユーティリティ）
  - (strategy/, execution/, monitoring/ はパッケージ公開対象に含まれますが、本リポジトリに対応モジュールが存在する場合に読み込み可能）

ドキュメント参照箇所（コード内設計コメント）
- 各モジュール冒頭に処理フロー、設計方針、フェイルセーフの挙動が詳細に記載されています。実装や拡張を行う際は該当コメントを参照してください。

ライセンスや貢献
----------------
本 README ではライセンス情報を含めていません。実際のリポジトリには LICENSE や CONTRIBUTING を追加してください。

その他
-----
- 開発時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして環境依存の自動読み込みを止めるとテストが容易になります。
- テーブルの初期スキーマ／マイグレーションやデータの初期投入は別途スクリプト（schema 初期化用）をご用意ください。

問題や質問があれば、どの機能について知りたいかを教えてください（ETL の挙動、AI 部分のプロンプト設計、J-Quants クライアントの挙動など）。