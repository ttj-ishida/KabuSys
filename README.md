# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。  
DuckDB をデータストアに用い、J-Quants API からのデータ取得・ETL、RSS ニュース収集、LLM を用いたニュースセンチメント評価、マーケットレジーム判定、リサーチ用ファクター計算、データ品質チェック、監査ログスキーマ等を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API失敗時はスキップして継続）」「外部 API 呼び出しのリトライ／レート制御」です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API / 実行例）
- 環境変数 / 設定
- ディレクトリ構成（ファイル一覧と簡単な説明）
- トラブルシューティング（よくある注意点）

---

## プロジェクト概要

KabuSys は、日本株のデータパイプラインとリサーチ／戦略開発を支援する Python モジュール群です。  
主に以下用途を想定しています。

- J-Quants API から株価・財務・カレンダー等を差分取得する ETL パイプライン
- RSS ニュースの収集と銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（銘柄別 ai_scores / マクロセンチメント）
- ETF を用いた市場レジーム判定（株式市場全体の bull/neutral/bear）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution）スキーマの初期化ユーティリティ

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（fetch/save の冪等実装・レート制御・リトライ）
  - market_calendar / raw_prices / raw_financials / stocks などの保存関数
- ETL
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- ニュース処理
  - RSS フィード取得（SSRF 対策・レスポンスサイズ制限・トラッキングパラメータ除去）
  - news → raw_news テーブル保存、news_symbols による銘柄紐付け
- LLM ベースの解析
  - 銘柄別ニュースセンチメント（score_news）
  - マクロセンチメント + ETF MA200 乖離を合成した市場レジーム判定（score_regime）
- リサーチ
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー、Zスコア正規化
- データ品質
  - 欠損・重複・スパイク・未来日付 / 非営業日データ検出（run_all_checks）
- 監査ログ
  - 監査用テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings クラス（settings）

---

## セットアップ手順

※ 下記は典型的な開発環境構築手順です。プロジェクトの配布方法や requirements.txt に依存して調整してください。

1. Python 環境を用意（推奨: 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - 追加でテストや開発に必要なものがあれば適宜インストール
4. パッケージを editable インストール（開発時）
   - pip install -e .
5. 環境変数を準備
   - プロジェクトルートに .env を作成（下記「環境変数」を参照）
   - 自動ロードは既定で有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

---

## 環境変数 / 設定

Settings クラス（kabusys.config.settings）から設定値を取得します。主なキー:

- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KabuStation API（株発注等）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OpenAI / LLM
  - OPENAI_API_KEY（score_news / score_regime のデフォルト取得元）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB パス（デフォルトを使用する場合は .env 不要）
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, 例: data/monitoring.db)
- 実行監視／閾値
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- システム環境
  - KABUSYS_ENV = development | paper_trading | live
  - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

注意:
- settings のプロパティは必須が未設定だと ValueError を送出します（例: JQUANTS_REFRESH_TOKEN）。
- 自動 .env ロードの挙動:
  - OS 環境 > .env.local > .env の順で読み込み（protected：既存 OS 環境変数は上書きされません）
  - プロジェクトルートは .git または pyproject.toml の位置から検索
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## 使い方（主要 API / 実行例）

以下は最小限の例です。DuckDB 接続は `duckdb.connect(path)` を使います。

- Settings の利用例
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- 日次 ETL を実行する（例: 当日を対象）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> OPENAI_API_KEY を参照
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
n = score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # または ":memory:"
```

- ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum
records = calc_momentum(conn, target_date=date(2026,3,20))
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for issue in issues:
    print(issue)
```

注意:
- score_news / score_regime は OpenAI API を呼び出します。環境変数 OPENAI_API_KEY を設定してください。
- ETL 実行時には JQUANTS_REFRESH_TOKEN が必要です（get_id_token → J-Quants の id token を得る）。

---

## ディレクトリ構成（主なファイルと説明）

以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py  — パッケージ定義（version 等）
  - config.py    — .env / 環境変数の自動ロードと Settings クラス
- kabusys/ai/
  - __init__.py
  - news_nlp.py      — 銘柄別ニュースセンチメント（score_news）
  - regime_detector.py — マクロセンチメント + ETF MA200 乖離による市場レジーム判定（score_regime）
- kabusys/data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（fetch / save / 認証 / rate limit）
  - pipeline.py         — ETL パイプラインと run_daily_etl 等
  - etl.py              — ETLResult 再エクスポート
  - news_collector.py   — RSS フィード取得・記事前処理・raw_news 保存ロジック
  - calendar_management.py — 市場カレンダー管理（営業日判定・update ジョブ）
  - stats.py            — Zスコア等の統計ユーティリティ
  - quality.py          — データ品質チェック
  - audit.py            — 監査ログ（signal/order_requests/executions）DDL と初期化
- kabusys/research/
  - __init__.py
  - factor_research.py  — モメンタム / バリュー / ボラティリティ等の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリーなど

（上記以外にも strategy / execution / monitoring 等の名前空間が __all__ に含まれる想定です。詳細はコードベースを参照してください。）

---

## トラブルシューティング / 注意点

- 環境変数未設定で ValueError が出るケース
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須です。settings のプロパティが未設定だと ValueError を送出します。
- OpenAI API 呼び出しについて
  - ネットワーク障害やレート制限、5xx に対しては内部でリトライを実装しています。LLM のレスポンスパース失敗は 0.0 等のデフォルト値へフォールバックする設計です（例: macro_sentiment=0.0）。
- DuckDB executemany の空リスト
  - 古い DuckDB バージョンでは executemany に空のパラメータが渡せないためコード内でガードしています。
- 自動 .env ロード
  - プロジェクトルートが .git または pyproject.toml の位置から探索されます。パッケージ配布後も予期せぬ動作がある場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で env を読み込んでください。
- SSRF / RSS
  - news_collector は SSRF 対策（リダイレクト検査・プライベートアドレス拒否）、レスポンスサイズ制限、XML パースの安全化（defusedxml）などを行っています。

---

この README はコードベースの主要な機能と使い方、構成をまとめたものです。実運用や詳細な設定（CI/cron による定期実行、発注ロジック、監視設定など）は各プロジェクトの運用方針に応じて追加してください。必要であれば、README に入れるサンプル .env.example、requirements.txt、運用手順（cron/サービス化）なども作成いたします。必要があればお知らせください。