KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ（ファクター計算）および監査ログ（約定トレース）などの機能を提供します。

主な特徴
--------
- J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）と品質チェック
- RSS を用いたニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）とマクロセンチメントの合成による市場レジーム判定
- Research 用ファクター計算（Momentum / Value / Volatility）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）のための DuckDB スキーマ初期化ユーティリティ
- 設定管理（.env 自動読み込み、環境切替、ログレベル制御）

必要条件（依存）
----------------
最低限の実行に必要な主要ライブラリ（環境に応じて追加）:
- Python 3.9+（型注釈や構文に依存）
- duckdb
- openai
- defusedxml

インストール例:
- 開発環境へローカルインストール（src 配置を想定）:
  - pip install -U pip
  - pip install duckdb openai defusedxml
  - pip install -e .  （パッケージセットアップがある場合）

設定（環境変数）
----------------
設定は環境変数かプロジェクトルートの .env / .env.local から読み込まれます。  
自動読み込みはパッケージ初期化時に行われ、優先度は OS 環境 > .env.local > .env です。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN       : Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先のチャンネル ID

任意（デフォルト有り）:
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視等で使う SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : 環境 ("development" | "paper_trading" | "live"), デフォルト "development"
- LOG_LEVEL             : ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL"), デフォルト "INFO"
- OPENAI_API_KEY        : OpenAI の API キー（score_news / score_regime に None を渡した場合に使用）

簡易 .env 例 (.env.example)
--------------------------
例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01XXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

セットアップ手順
----------------
1. リポジトリをクローン（プロジェクトルートに .git または pyproject.toml を置くと .env 自動読み込みが有効になります）
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて追加のライブラリをインストール）
4. .env をプロジェクトルートに作成して必須の設定を記載
5. DuckDB の格納先ディレクトリがなければ作成（例: mkdir -p data）

主要な使い方（コード例）
-----------------------

- 共通: 設定と DB 接続取得
```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー / 株価 / 財務 / 品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースの NLP スコア付与（OpenAI API キーは OPENAI_API_KEY 環境変数か引数で指定）
```
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None なら環境変数を参照
print(f"scored {written} symbols")
```

- 市場レジーム評価（ETF 1321 の MA200 とマクロセンチメントの合成）
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ用 DB の初期化（監査専用 DB を作る）
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- RSS フィード取得（ニュース収集ユーティリティ）
```
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点と設計方針（要点）
-----------------------
- ルックアヘッドバイアス防止:
  - 日付計算や選択クエリは target_date を明示的に受け取り、datetime.today()/date.today() を内部で参照しない設計が多く採用されています（バックテスト向け安全設計）。
- 外部 API 呼び出しの堅牢化:
  - J-Quants/API や OpenAI への呼び出しはレート制御・再試行・バックオフ・401 リフレッシュなどの処理を実装してあります。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスバリデーションを行います。失敗時はフェイルセーフ（ゼロ化、もしくは該当処理スキップ）で継続します。
- データ品質:
  - quality モジュールで欠損・重複・スパイク・日付不整合を検出します。ETL は Fail-Fast にせず問題を収集して報告する設計です。
- セキュリティ:
  - RSS 収集では SSRF 対策（リダイレクト検査・プライベートアドレス検出）、defusedxml を利用した XML パース、安全な最大応答サイズ制限などを実装しています。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE や INSERT … ON CONFLICT を用いて冪等に実行されます。監査ログは削除しない前提です。

主なディレクトリ構成
-------------------
（src/kabusys 配下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py               — ニュースセンチメント解析（OpenAI）
    - regime_detector.py       — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult の再エクスポート
    - calendar_management.py   — 市場カレンダー管理 / 営業日判定
    - news_collector.py        — RSS 収集・前処理・保存ユーティリティ
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize 等）
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログスキーマ初期化（signal/order_requests/executions）
  - research/
    - __init__.py
    - factor_research.py       — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py   — 将来リターン・IC・統計サマリ
  - ai/, research/ 以下に示した以外にも strategy / execution / monitoring などのパッケージ想定

追加情報・運用メモ
-----------------
- OpenAI を用いる処理（score_news, score_regime）は API 呼び出し回数・コストに注意してください。バッチサイズやチャンク設定・最大記事数制限を調整することでコストを制御できます。
- 本ライブラリは「データ取得・処理・スコアリング・監査ログ」の基盤を提供します。実際の発注ロジック（kabuステーションへの送信やリスク管理ポリシー）は別モジュール／上位アプリケーションで実装して連携してください。
- DuckDB によるデータ永続化はローカルファイルを想定しています。運用環境ではバックアップや権限管理を検討してください。

ライセンス / 貢献
-----------------
リポジトリの LICENSE を参照してください。バグ報告・機能提案は issue を起票してください。

最後に
------
この README はコードベースの構成と使用方法の概要をまとめたものです。詳細な API や実装要件は各モジュールの docstring（ソース内コメント）を参照してください。必要に応じて README を拡張しますので、追加で記載してほしい項目があれば教えてください。