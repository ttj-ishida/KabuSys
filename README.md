KabuSys — 日本株向けデータプラットフォーム兼自動売買基盤
======================================================

概要
----
KabuSys は日本株のデータ収集（J-Quants / RSS）、データ品質チェック、特徴量（ファクター）計算、AI（OpenAI）を使ったニュースセンチメント評価、マーケットレジーム判定、監査ログ（取引フロー追跡）などを含むデータプラットフォーム/研究基盤です。DuckDB をストレージに用い、J-Quants API や各種 RSS、OpenAI を組み合わせて ETL → 研究 → 実行 のワークフローをサポートします。

主な特徴
--------
- J-Quants API 経由の差分 ETL（株価・財務・市場カレンダー）
  - レート制御 / リトライ / トークン自動リフレッシュを内蔵
- ニュース収集（RSS）と前処理（URL 正規化・SSRF 対策・サイズ制限）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別）およびマクロセンチメント合成による市場レジーム判定
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量探索ツール（将来リターン計算、IC、統計サマリ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）用の冪等かつトレーサブルなテーブル構成
- DuckDB を中心とした軽量で高速なオンプレ DB 利用
- Look-ahead bias 回避設計（現在時刻参照を最小化、ETL/評価は指定日ベース）

セットアップ手順
----------------

前提
- Python 3.10+（コードは型ヒントに依存）
- ネットワークアクセス（J-Quants, OpenAI, RSS ソース）

1. リポジトリをチェックアウト
   - 例: git clone <repo> && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要依存例:
     - pip install duckdb openai defusedxml

   （プロジェクト配布方法に応じて pip install -e . など）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を検出）に .env / .env.local を配置すると自動で読み込みます（自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — （通知を使う場合）Slack Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注等で使用）
     - OPENAI_API_KEY — OpenAI 呼び出しに必要（score_news / regime）
   - 任意・デフォルト
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

使い方（簡単な利用例）
--------------------

基本的な DuckDB 接続
```
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path object
conn = duckdb.connect(str(db_path))
```

日次 ETL の実行（株価・財務・カレンダー・品質チェック）
```
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None で今日を基準に実行
print(result.to_dict())
```

ニュースセンチメント（銘柄別）をスコア化して ai_scores テーブルへ書き込む
```
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written}")
```

市場レジーム判定（ma200 と マクロセンチメント合成）
```
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログスキーマの初期化（監査用 DB を作る）
```
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル(signal_events, order_requests, executions) が作成されます
```

研究用ファクター計算例
```
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

ディレクトリ構成（主なファイル・モジュール）
----------------------------------------

src/kabusys/
- __init__.py
- config.py                        — 環境変数・設定の読み込み（.env 自動読み込み含む）
- ai/
  - __init__.py
  - news_nlp.py                     — ニュースの OpenAI ベースセンチメント解析（銘柄別）
  - regime_detector.py              — マクロセンチメント + ETF MA200 で市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py               — J-Quants API クライアント + DuckDB 保存ロジック
  - pipeline.py                     — 日次 ETL パイプライン（差分取得・保存・品質チェック統合）
  - etl.py                          — ETLResult の再エクスポート
  - news_collector.py               — RSS 収集 & 前処理（SSRF 対策等）
  - calendar_management.py          — 市場カレンダー管理（営業日判定など）
  - stats.py                        — 共通統計ユーティリティ（z-score 等）
  - quality.py                      — データ品質チェック群
  - audit.py                        — 監査ログ（テーブル作成・初期化）
- research/
  - __init__.py
  - factor_research.py              — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py          — 将来リターン計算 / IC / 統計サマリ
- research から data.stats を参照する形で研究機能が提供されます

設計上の注意点 / 補足
--------------------
- Look-ahead bias 回避:
  - 多くの関数は内部で datetime.today() を使わず、target_date を引数に取る設計です。バックテスト/再現可能性を重視しています。
- 冪等性:
  - ETL の保存処理は ON CONFLICT DO UPDATE / INSERT … DO UPDATE のような冪等保存を行います。
- エラーハンドリング:
  - 外部 API 呼び出しはリトライ・フェイルセーフが組み込まれ、API 失敗時はゼロ値で続行したり、部分スキップして他の処理は継続します（ログに記録）。
- 安全対策:
  - RSS 取得: SSRF 対策、受信サイズ制限、defusedxml 利用などを行っています。
  - J-Quants クライアント: レート制御、401 時のトークン自動リフレッシュ、再試行バックオフを実装。

よくある質問
------------
- Q: OpenAI の呼び出しに必要なキーの指定方法は？
  - A: score_news / score_regime などは api_key 引数でキー注入可能。引数を省略した場合は環境変数 OPENAI_API_KEY を参照します。
- Q: .env の自動読み込みを無効にしたい
  - A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みをスキップします（テスト等で便利です）。
- Q: DuckDB のデータファイルの場所は？
  - A: settings.duckdb_path がデフォルトで data/kabusys.duckdb を返します。環境変数 DUCKDB_PATH で変更可能です。

貢献・開発
----------
- 開発中は KABUSYS_ENV=development, LOG_LEVEL=DEBUG を推奨します。
- テストでは外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックすることを推奨します。モジュール内で API 呼び出し部分を差し替えやすく設計されています（例: news_nlp._call_openai_api を patch してテスト）。

ライセンス
----------
- （ここに実際のライセンス情報を記載してください）

---

この README はコードベースの公開仕様を要約したものです。詳細な API 仕様やデータスキーマ、運用手順（監視 / ログ / 再試行方針）はプロジェクト内のドキュメント（Design docs / DataPlatform.md / StrategyModel.md 等）を参照してください。必要なら README を拡張して具体的な実運用手順や CI/CD の設定例も追加できます。