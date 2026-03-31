# KabuSys

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants からのデータ ETL、ニュース収集と LLM によるニュース評価、ファクター計算、監査ログ（トレーサビリティ）や市場カレンダー管理など、取引システム／リサーチ環境で必要となる機能群を提供します。

主な設計方針
- ルックアヘッドバイアスの排除（内部で date.today() を無暗に参照しない等）
- DuckDB を中心とした軽量なローカル分析基盤
- 外部 API 呼び出しはリトライやレート制御、エラー時のフェイルセーフを実装
- 冪等性を重視（DB 保存は ON CONFLICT / idempotent な処理）
- テスト容易性を考慮した依存注入（APIキーなど引数で注入可能）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の明示的チェック（settings オブジェクト）

- データ ETL（jquants_client + pipeline）
  - J-Quants API から株価（OHLCV）、財務、マーケットカレンダーを差分取得
  - DuckDB への冪等保存（save_* 関数）
  - 日次 ETL パイプライン（run_daily_etl）

- ニュース収集 & NLP
  - RSS 収集（SSRF 対策、URL 正規化、前処理）
  - raw_news → 銘柄紐付け → ai_scores へセンチメント書き込み（score_news）
  - LLM を用いたマクロセンチメント＋MA200 乖離による市場レジーム判定（score_regime）

- 研究（Research）ユーティリティ
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- データ品質チェック（quality）
  - 欠損・スパイク（急騰急落）・重複・日付不整合チェック（run_all_checks）

- マーケットカレンダー管理（calendar_management）
  - 営業日判定、next/prev_trading_day、カレンダー更新バッチ（calendar_update_job）

- 監査ログ / トレーサビリティ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.10+（ソースの型注釈で Python 3.10 系の構文を使用）
- ネットワークアクセス（J-Quants / OpenAI 等）や DuckDB を利用可能な環境

1. リポジトリをチェックアウト
   - 例: git clone <your-repo>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要な主な依存:
     - duckdb
     - openai (openai ライブラリ、OpenAI クライアント用)
     - defusedxml
   - 例（requirements.txt がある場合）:
     - pip install -r requirements.txt
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（ただしテスト等で無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主な必須環境変数（コード内で _require によって必須扱い）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD      — kabu API パスワード（注文関連に使用する場合）
     - SLACK_BOT_TOKEN        — Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID       — Slack チャネル ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
     - KABU_API_BASE_URL — default: http://localhost:18080/kabusapi
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

5. サンプル .env（プロジェクトルート/.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方（簡単なサンプル）

下記は Python REPL / スクリプトからライブラリを呼び出す例です。実際の運用では job / cron / Airflow などでスケジューリングして使います。

- DuckDB 接続の作成（settings からパスを利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

- ニュースのスコアリング（LLM を利用）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を参照
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n}")
```

- 市場レジームの評価（MA と マクロニュースの合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB の初期化（監査専用ファイルを作る）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブルとインデックスを作成して接続を返す
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

注意点
- OpenAI にアクセスする機能（score_news, score_regime）は API 利用料が発生します。OPENAI_API_KEY を適切に設定してください。
- J-Quants API 呼び出しは認証とレート制御（120 req/min）を行います。JQUANTS_REFRESH_TOKEN を設定してください。
- 実運用（live）では KABUSYS_ENV を "live" に切替え、発注周りの慎重な確認を行ってください。

---

## ディレクトリ構成（概要）

以下は主要なモジュールと役割の一覧です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード (.env / .env.local)
    - settings オブジェクト（J-Quants / kabu / Slack / DB パス / 環境）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores へ書き込み
    - regime_detector.py    — MA200 と マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - pipeline.py           — ETL パイプラインのメイン処理（run_daily_etl 等）
    - etl.py                — ETLResult の再エクスポート
    - news_collector.py     — RSS 取得・前処理・raw_news 保存
    - quality.py            — データ品質チェック群
    - stats.py              — zscore_normalize 等の汎用統計ユーティリティ
    - calendar_management.py— マーケットカレンダー管理（営業日判定・更新ジョブ）
    - audit.py              — 監査ログスキーマ定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py— 将来リターン計算・IC・統計サマリー等
  - monitoring/ (コードベース内に監視系モジュールがあればここに)
  - strategy/, execution/, monitoring/ などは __all__ に含まれています（将来的な拡張箇所）

（上記は主要ファイルの抜粋です。プロジェクト全体のファイル一覧はリポジトリを参照してください）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 がセットされていないか確認してください。
  - プロジェクトルートは .git または pyproject.toml を基準に検出されます。配置場所に注意してください。

- OpenAI への接続やレスポンスパースで失敗する
  - API のレート制限やレスポンス形式の違いをログで確認してください。score_news / score_regime はフォールバックやリトライを実装していますが、レスポンスフォーマット変化でパースエラーが発生する場合があります。

- DuckDB の接続や SQL 実行でエラーが出る
  - スキーマ（テーブル）が未作成のケースがあります。data.audit.init_audit_schema 等の初期化関数を使ってテーブルを作成してください。
  - DuckDB の executemany は空リストを受け付けないバージョンの制約に注意（コード内でも考慮済み）。

---

本 README はコードベースの主要機能と利用方法を簡潔にまとめたものです。さらに詳細な API 仕様・スキーマ定義・運用手順は各モジュールの docstring（コード内コメント）およびプロジェクトの設計ドキュメント（存在する場合）を参照してください。必要であれば README にデプロイ手順や CI/CD、監視・ロギング設計などを追加します。