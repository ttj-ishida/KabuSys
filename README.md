# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）です。  
データ取得（J-Quants）→ ETL（DuckDB）→ 特徴量生成 → シグナル生成 → 発注・監査までを想定したモジュール群を含みます。  
（本リポジトリはライブラリ/バッチ実行向けの内部ロジックを提供します。運用環境での発注実行部分は環境に応じた実装が必要です。）

---

## プロジェクト概要

- データ層（Raw / Processed / Feature / Execution）を DuckDB 上に定義・管理するスキーマを提供
- J-Quants API クライアントを通じた差分 ETL（株価、財務、マーケットカレンダー）
- 特徴量計算（モメンタム / バリュー / ボラティリティ 等）、クロスセクション Z スコア正規化
- 特徴量と AI スコアを統合した売買シグナル生成ロジック（BUY / SELL 判定、エグジット条件）
- ニュース収集（RSS → raw_news / news_symbols）と市場カレンダー管理
- 監査ログ（signal_events / order_requests / executions 等）用のDDLを含む
- 設計方針として「ルックアヘッドバイアス排除」「冪等性（ON CONFLICT）」「外部 API へのリトライ／レート制御」「SSRF 等の安全対策」を重視

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・トークン自動更新・レート制御）
  - pipeline: 差分 ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - schema: DuckDB スキーマ定義 / init_schema
  - news_collector: RSS 取得・正規化・DB保存（SSRF対策・gzip/size制限）
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - stats: zscore_normalize など統計ユーティリティ
  - features: データ層用の再エクスポートユーティリティ
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）、統計サマリー等
- strategy/
  - feature_engineering.build_features: research の生ファクターを統合・フィルタ・正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成して signals テーブルへ保存
- config: 環境変数読み込み・settings インターフェース（必須トークン等の取得・バリデーション）
- audit: 監査ログ用 DDL（signal_events / order_requests / executions）
- その他: execution, monitoring（拡張ポイント）

---

## 前提 / 必要環境

- Python >= 3.10（型ヒントや構文に依存）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- 例: pip install duckdb defusedxml

（他に urllib / datetime / 標準ライブラリのみで多くの処理を実装しています。実行環境によっては追加のユーティリティが必要になる場合があります。）

---

## 環境変数 / 設定

パッケージは実行時にプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）から `.env` / `.env.local` を自動読み込みします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（Settings クラスで参照・必須のものは明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション等の API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 連携用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト: INFO）

注意: Settings は未設定の必須変数に対して ValueError を送出します。`.env.example` を参照して `.env` を作成してください。

.env 読み込み仕様：
- 優先順位: OS 環境変数 > .env.local > .env
- export KEY=val 形式やクォート、インラインコメント等に対応
- プロジェクトルートが見つからない場合は自動ロードをスキップ

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows では .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで requirements.txt があれば pip install -r requirements.txt）
4. `.env` をプロジェクトルートに作成して必須環境変数を設定
5. DuckDB スキーマを初期化

例: DuckDB 初期化
```bash
python - <<'PY'
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
print("DuckDB schema initialized")
PY
```

---

## 使い方（主要な API と実行例）

以下は簡単な Python スニペット例です。`data/kabusys.duckdb` を使う想定。

- DuckDB 接続を取得（初回は init_schema を呼ぶこと）
```python
from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")  # 既に初期化済みでも安全
# あるいは既存 DB に接続
conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL を実行（J-Quants 認証は settings が .env から読み込み）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

- 特徴量を構築（features テーブルに UPSERT）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, target_date=date(2024, 1, 10))
print("features upserted:", count)
```

- シグナル生成（features + ai_scores → signals テーブル）
```python
from kabusys.strategy import generate_signals
from datetime import date
total = generate_signals(conn, target_date=date(2024, 1, 10))
print("signals generated:", total)
```

- ニュース収集ジョブを実行（RSS 収集 → raw_news + news_symbols）
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新バッチ（夜間ジョブ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("market_calendar saved:", saved)
```

注意点:
- research モジュールの関数（calc_momentum 等）は DuckDB の prices_daily/raw_financials を参照するため、本番口座や発注 API へのアクセスはありません（分析専用）。
- ETL / save_* 関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計されています。
- J-Quants クライアントはレート制限（120 req/min）と再試行ロジックを持ち、401 時はリフレッシュトークンで自動更新します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - stats.py               — zscore_normalize 等統計ユーティリティ
    - features.py            — features の再エクスポート
    - news_collector.py      — RSS 収集・保存
    - calendar_management.py — 市場カレンダー管理 / calendar_update_job
    - audit.py               — 監査ログ用 DDL（signal_events 等）
    - audit.py
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features
    - signal_generator.py    — generate_signals
  - execution/               — 発注/約定処理（拡張点）
  - monitoring/              — 監視 / メトリクス（拡張点）

（README で紹介した以外にも補助モジュールやユーティリティが含まれます。コードを参照してください。）

---

## 開発上の注意 / トラブルシューティング

- Settings が必須環境変数を見つけられない場合、ValueError を送出します。`.env` を用意して値を設定してください。
- DuckDB 操作時にパーミッションエラーが出る場合はデータディレクトリの権限を確認してください。
- RSS フェッチでは SSRF 対策やレスポンスサイズ制限を行います。外部 URL を利用する際はアクセスできることを事前に確認してください。
- J-Quants API のレート制限により大量リクエストはバックオフされます。大量取得時は時間をとって実行してください。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装です。大量データでのパフォーマンス必要な場合は別途集約処理や最適化を検討してください。

---

必要であれば README に実行スクリプト例・CI 設定・運用手順（cron / Airflow 等）や SQL スキーマの ER 図、テスト実行方法を追加できます。どの情報を優先して追記するか教えてください。