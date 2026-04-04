# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント算出）、ファクター計算、監査ログ（発注→約定のトレース）、マーケットカレンダー管理などを含む一連のユーティリティを提供します。

---

## 特徴（概要）

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・自動リフレッシュ・リトライ付き）
- DuckDB を利用したローカルデータ保存（冪等保存・ON CONFLICT 処理）
- RSS ベースのニュース収集と前処理（SSRF対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA乖離 + マクロセンチメントの合成）
- ファクター計算（モメンタム／ボラティリティ／バリュー等）と特徴量探索ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合など）
- 監査ログスキーマ（signal → order_request → execution の追跡可能なテーブル群）
- 環境変数 / .env の自動読み込み（プロジェクトルート検出による）

設計上の注意点：バックテスト時のルックアヘッドバイアスを避けるため、多くの処理で現在時刻を直接参照しない実装方針を取っています。

---

## 機能一覧（モジュール別）

- kabusys.config
  - .env / 環境変数読み込み、自動ロード（プロジェクトルートに .env/.env.local）
  - settings オブジェクト経由で設定を参照可能
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline: ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集・前処理・raw_news への保存支援
  - quality: データ品質チェック（各種 QualityIssue を返す）
  - calendar_management: 市場カレンダー管理（営業日判定・next/prev など）
  - audit: 監査ログテーブル初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントの算出と ai_scores への保存
  - regime_detector.score_regime: マクロセンチメントと ETF MA 乖離を合成した市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 前提（Prerequisites）

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 外部サービス
  - J-Quants API（リフレッシュトークン）
  - OpenAI API（OPENAI_API_KEY） — AI 機能を使う場合

インストール例（仮）:
```bash
python -m pip install duckdb openai defusedxml
# またはローカルのパッケージ化された依存ファイルがあればそれに合わせてください
```

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（settings.jquants_refresh_token）
- AI / 通知
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- kabu ステーション（注文用）
  - KABU_API_PASSWORD, KABU_API_BASE_URL（任意）
- データベース / ファイルパス（デフォルトを用いる場合は省略可）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH
- 実行環境設定
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を起点に `.env` と `.env.local` を自動読み込みします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成して必要なキーを配置（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）
5. DuckDB データベース初期化（監査DB を別途初期化する例）
   - Python REPL / スクリプトで:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # :memory: も可
     conn.close()
     ```

---

## 使い方（よく使う例）

1) 設定を取得する
```python
from kabusys.config import settings
print(settings.duckdb_path)    # Path オブジェクト
print(settings.env, settings.log_level)
```

2) 日次 ETL を実行（例: DuckDB に接続して run_daily_etl を呼ぶ）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定することも可
print(result.to_dict())
conn.close()
```

3) ニュースセンチメントを算出して ai_scores に保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
conn.close()
```

4) 市場レジーム判定（1321 MA200 等を使う）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
conn.close()
```

5) 監査ログスキーマを初期化（既存 DB にテーブル追加）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
conn.close()
```

6) ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
factors = calc_momentum(conn, target_date=date(2026,3,20))
# その後 zscore_normalize で正規化など
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(factors, ["mom_1m", "mom_3m", "ma200_dev"])
```

---

## 実装上の注意点 / 設計ポリシー

- ルックアヘッドバイアス防止: 多くの関数が内部で date.today() を直接参照せず、必ず target_date を受け取るか明示的に制御します。
- 冪等性: ETL / 保存ロジックは重複を上書きする（ON CONFLICT DO UPDATE）ことで冪等に設計されています。
- リトライ & レート制御: J-Quants の API 呼び出しには固定間隔のレートリミッタと指数バックオフを実装しています。
- フェイルセーフ: AI API の失敗時はスコアを 0 にフォールバックするなど、運用で致命的な停止を起こさない設計です（ログは出力）。
- セキュリティ: RSS 取得では SSRF 対策、XML パースは defusedxml を使用、URL 正規化・トラッキング除去を行います。

---

## ディレクトリ構成

src/kabusys/
- __init__.py — パッケージメタ情報（__version__ 等）
- config.py — 環境変数 / .env の読み込みと settings
- ai/
  - __init__.py
  - news_nlp.py — 銘柄別ニュースNLPスコアリングと ai_scores への保存
  - regime_detector.py — ETF MA とマクロセンチメント合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存用）
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 収集と前処理ユーティリティ
  - quality.py — データ品質チェック
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - audit.py — 監査ログスキーマ定義 / 初期化
  - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- その他（strategy / execution / monitoring などのパッケージを想定するエクスポートが __all__ に含まれていますが、該当実装はこのコードベース内で随所に分かれています）

---

## 追加情報 / トラブルシューティング

- .env のパースはシェル風 (export KEY=val 等) にも対応しており、クォート内のエスケープや行末コメントの取り扱いを考慮しています。
- 自動で .env を読み込めない（プロジェクトルート未検出・テスト時等）場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、自分で環境変数を注入してください。
- OpenAI を用いる関数は api_key を引数で渡すことも可能です（テスト時の差し替えや複数キー運用に便利です）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、ライブラリ側で注意して扱われています。

---

必要であれば、README に追加すべき CLI 実行方法、ユニットテストの実行手順、具体的な .env.example のテンプレート、または運用手順（cron / systemd での ETL バッチ実行例）を追記します。どの情報を優先的に追加しますか？