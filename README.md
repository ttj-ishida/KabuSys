KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ取得（J-Quants） → ETL → 品質チェック → 研究（ファクター） → AI ベースのニュース評価 → 戦略/監査ログ、といったワークフローをサポートします。

バージョン: 0.1.0

主な特徴
-------
- データETL
  - J-Quants API からの株価（日足）、財務、マーケットカレンダーの差分取得（ページネーション対応）と DuckDB への冪等保存
  - ETL パイプライン（run_daily_etl）でカレンダー取得→株価→財務→品質チェックを一括実行
  - ID トークンの自動リフレッシュ・レート制御・リトライ実装

- データ品質チェック
  - 欠損（OHLC）検出、前日比スパイク検出、重複、日付不整合（未来日や非営業日のデータ）等のチェックと QualityIssue レポート

- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、URL 正規化、サイズ制限、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄単位）スコア化（score_news）
  - マクロニュースと ETF (1321) の MA200 乖離を組み合わせた市場レジーム判定（score_regime）

- リサーチ / ファクター
  - モメンタム／ボラティリティ／バリューなどのファクター計算関数（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義・初期化（init_audit_schema / init_audit_db）
  - 発注フローの冪等性と監査保持を想定したスキーマ

- ユーティリティ
  - 市場カレンダー管理・営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - 各種 DB 操作ヘルパー、統計ユーティリティ

セットアップ
-------

前提
- Python 3.10+（型注釈の Union | などを利用）
- 必要パッケージ（代表例）：duckdb, openai, defusedxml
  - 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

ローカルでの開発インストール（例）
- リポジトリルートで:
  - pip install -e .[dev]    （実装に合わせた extras を用意している場合）
  - もしくは必要パッケージを個別に pip install duckdb openai defusedxml

環境変数
- .env または .env.local をプロジェクトルートに置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。自動ロードはプロジェクトルートを .git か pyproject.toml を起点に探索します。
- 主な必須環境変数:
  - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
  - OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime に未指定時参照）
  - KABU_API_PASSWORD      — kabuステーション API パスワード（運用時）
  - SLACK_BOT_TOKEN        — Slack 通知用トークン
  - SLACK_CHANNEL_ID       — Slack 通知先チャンネルID
- 任意 / デフォルト:
  - KABUSYS_ENV            — development / paper_trading / live（デフォルト development）
  - LOG_LEVEL              — DEBUG/INFO/...（デフォルト INFO）
  - DUCKDB_PATH            — デフォルト data/kabusys.duckdb
  - SQLITE_PATH            — デフォルト data/monitoring.db

例 .env（最小）
```env
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

使い方（基本例）
------------

1) DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイル DB
# または in-memory
# conn = duckdb.connect(":memory:")
```

2) 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- ETL は市場カレンダー → 株価 → 財務 → 品質チェック の順に処理します。エラーは個別に捕捉され、ETLResult に記録されます。

3) ニュースセンチメントを生成（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai scores")
```

4) 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査DBの初期化（発注 / 約定ログ用）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または既存接続にスキーマを追加
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

6) 研究モジュールの呼び出し例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic
from kabusys.data.stats import zscore_normalize
from datetime import date

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

主要モジュールと API（抜粋）
----------------------
- kabusys.config
  - settings: 環境変数取得用ラッパー（必須キーは _require で検証）。自動 .env ロード機能あり。

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult データクラス

- kabusys.data.quality
  - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
  - QualityIssue 型

- kabusys.data.news_collector
  - fetch_rss, preprocess_text, URL 正規化、SSRF 対策等

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize は kabusys.data.stats

設計上のポイント / 注意事項
--------------------------
- ルックアヘッドバイアス対策
  - 多くの関数（ETL / score_news / score_regime 等）は内部で datetime.today() を参照せず、必ず target_date を明示的に渡して使用する設計です。バックテスト時は必ず過去の target_date を与えてください。

- フェイルセーフ
  - AI / 外部 API 呼び出しの失敗時は例外を即座に上げずフェイルセーフな既定値（例: マクロセンチメント = 0.0）で処理を継続する箇所が多くあります（ログに警告を出力）。

- 冪等性
  - DuckDB への保存は基本的に ON CONFLICT DO UPDATE / DO NOTHING を使い冪等にしています。監査ログも order_request_id を冪等キーとして扱います。

- セキュリティ
  - news_collector は SSRF 対策（ホストのプライベート判定、リダイレクト検査等）・XML インジェクション対策（defusedxml）・最大レスポンスサイズ制限などを備えています。

ディレクトリ構成
----------------
（主要ファイル・モジュールのツリー。src/kabusys 以下）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - quality.py
    - stats.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - other modules...

（上記は主要なファイル一覧で、実際のリポジトリには追加のユーティリティやテストがある場合があります）

開発・デプロイのヒント
--------------------
- OpenAI や J-Quants の API キーは本番・ステージング・開発で分けることを推奨します（KABUSYS_ENV を使って挙動切替を実装可能）。
- ETL は Cron / Airflow / GitHub Actions などのスケジューラで夜間バッチとして実行するユースケースを想定しています（calendar_update_job 等）。
- DuckDB ファイルはバックアップを取り、監査 DB は分離して運用することを推奨します。

貢献
----
バグ報告や改善提案は issue を立ててください。プルリクエスト歓迎です。ドキュメントや型注釈・テストの拡充に協力いただけると助かります。

ライセンス
--------
リポジトリに記載されたライセンスに従ってください（ここでは省略）。

--- 

必要であれば、README にサンプルスクリプトやより詳細な API リファレンス、デプロイ手順（systemd / Docker / Kubernetes）を追記します。どの情報が必要か教えてください。