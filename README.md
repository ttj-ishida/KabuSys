# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得・DuckDB 保存）、ニュース収集・NLP（OpenAI によるセンチメント）、リサーチ用ファクター計算、監査ログスキーマなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本市場向けに設計されたデータ基盤とリサーチ／戦略用ユーティリティ群を収めた Python パッケージです。主な目的は次のとおりです。

- J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）
- ニュース収集（RSS）と LLM（OpenAI）を用いた記事ベースの銘柄センチメント算出
- 市場レジーム判定（MA 乖離 + マクロニュース）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と探索用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレース）

設計上、バックテストでのルックアヘッドバイアスを避けるように日付扱い（target_date）に注意した実装になっています。

---

## 主な機能一覧

- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: トークン自動更新、ページネーション、レート制御、DuckDB へ冪等保存
- データ品質:
  - 欠損・スパイク・重複・日付不整合チェック（kabusys.data.quality）
- ニュース収集:
  - RSS 取得と前処理、安全対策（SSRF/サイズ制限/トラッキング削除）（kabusys.data.news_collector）
- ニュース NLP:
  - 銘柄別センチメント算出と ai_scores への保存（kabusys.ai.news_nlp::score_news）
- 市場レジーム判定:
  - ETF (1321) の MA200 乖離とマクロニュースを合成して市場レジームを算出・保存（kabusys.ai.regime_detector::score_regime）
- リサーチ:
  - ファクター計算（momentum/volatility/value）およびファクター解析・IC 計算（kabusys.research）
- 監査ログ（audit）:
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（kabusys.data.audit）
- 共通設定:
  - 環境変数および .env 自動ロード（kabusys.config）

---

## セットアップ手順

前提:
- Python 3.9+（動作確認は 3.10+ を推奨）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. レポジトリをクローン（またはパッケージを配置）
   - 例: git clone <repo>

2. 仮想環境の作成とアクティベート
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール
   - 開発時: pip install -e .
   - 依存パッケージ（代表例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ プロジェクトが setuptools/pyproject を提供していれば pip install -e . で必要パッケージをまとめてインストールできます。

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須 / 推奨変数例（.env）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # OpenAI (API呼び出しを行う場合)
     OPENAI_API_KEY=sk-...

     # kabuステーション API (必要であれば)
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # DB / ファイルパス
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 実行監視
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag

     # 環境 / ログ
     KABUSYS_ENV=development    # development | paper_trading | live
     LOG_LEVEL=INFO
     ```

---

## 使い方（基本例）

以下は Python REPL またはスクリプトから呼び出す代表的な例です。すべて DuckDB の接続を渡して動作します。

1. DuckDB 接続を作る（設定のパスを使用）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

2. 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日（内部で営業日に調整）
print(result.to_dict())
```

3. ニュースセンチメントを算出して ai_scores に保存する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数または api_key 引数で指定
print("written count:", written)
```

4. 市場レジームを算出して market_regime に保存する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

5. 監査ログスキーマを初期化する（別 DB を使う例）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn が返るので、以後監査ログの読み書きに使用
```

6. RSS を取得して raw_news に保存するワークフロー（概要）
- fetch_rss() で記事を取得、前処理 → DB に保存 → news_symbols で銘柄紐付け
- この保存ロジックはプロジェクト側でラッパーを実装して利用します（news_collector モジュール参照）。

---

## 設定と環境変数

kabusys.config.Settings がアプリ設定を提供します。重要なプロパティ:

- jquants_refresh_token (JQUANTS_REFRESH_TOKEN) — 必須
- kabu_api_password (KABU_API_PASSWORD) — 必須（kabu API を使う場合）
- kabu_api_base_url (KABU_API_BASE_URL) — デフォルト http://localhost:18080/kabusapi
- line_channel_access_token / line_user_id — 通知用（任意）
- duckdb_path (DUCKDB_PATH) — デフォルト data/kabusys.duckdb
- sqlite_path (SQLITE_PATH) — デフォルト data/monitoring.db
- PID_FILE_PATH / KILL_FLAG_PATH — 監視用
- KILL_FLAG_CLEAR_ON_START — "1" にすると起動時に kill flag をクリア
- CPU/MEM/DISK 閾値 — 監視閾値
- KABUSYS_ENV — development | paper_trading | live
- LOG_LEVEL — DEBUG|INFO|...

.env の自動読み込みはプロジェクトルート（.git または pyproject.toml により特定）から行われます。

---

## ディレクトリ構成

ソースは src/kabusys 以下に配置されています。主要ファイルと役割は次のとおりです。

- src/kabusys/
  - __init__.py : パッケージ初期化（__version__）
  - config.py : 環境変数解決・Settings
  - ai/
    - __init__.py
    - news_nlp.py : ニュースの LLM センチメント処理（score_news）
    - regime_detector.py : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント、保存関数（save_*）
    - pipeline.py : ETL パイプライン（run_daily_etl 等）、ETLResult
    - calendar_management.py : 市場カレンダー管理（is_trading_day, next_trading_day...）
    - news_collector.py : RSS 取得 / 前処理 / 保存ユーティリティ
    - quality.py : データ品質チェック（check_missing_data, check_spike...）
    - stats.py : z-score 正規化等の統計ユーティリティ
    - etl.py : ETLResult の公開再エクスポート
    - audit.py : 監査ログスキーマ定義・初期化 (signal_events / order_requests / executions)
  - research/
    - __init__.py
    - factor_research.py : ファクター計算（momentum/value/volatility）
    - feature_exploration.py : 将来リターン / IC / 統計サマリー
  - execution, strategy, monitoring ... （パッケージ __all__ に含まれるが、このスナップショットには未掲載のモジュールが存在する可能性があります）

---

## 開発上の注意

- Look-ahead バイアス対策:
  - 多くの関数は datetime.today() を直接使わず、呼び出し側が target_date を明示することを想定しています。
  - データ取得や集計では target_date 未満（排他）や取得ウィンドウの調整でルックアヘッドを防止します。
- API 呼び出し:
  - OpenAI（gpt-4o-mini）や J-Quants へのリクエストはリトライ・バックオフや 401 リフレッシュ（J-Quants）などを備えています。
- トランザクション:
  - テーブル書き込みは基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識していますが、複数ステップをまとめる場合はトランザクション管理に注意してください（DuckDB のトランザクション制限あり）。
- テスト:
  - モジュール内の外部呼び出し（OpenAI 呼び出しや URL オープン等）はテスト時にモックしやすいよう設計されています（内部呼び出しをラップした関数経由など）。

---

## よくある質問（簡易）

- .env を読み込まないようにしたいときは?
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI のキーを引数で渡せますか?
  - score_news / score_regime などは api_key 引数で明示できます。指定がない場合は環境変数 OPENAI_API_KEY を参照します。
- DuckDB のスキーマやテーブルはどう作る?
  - この README に含まれないスキーマ初期化のユーティリティが別途ある想定です。監査ログは kabusys.data.audit.init_audit_schema / init_audit_db で初期化できます。その他スキーマは ETL 実装やプロジェクトの schema 初期化スクリプトを利用してください。

---

## 貢献/拡張

- 新しい RSS ソースを追加する: DEFAULT_RSS_SOURCES に URL を追加し、news_collector のラッパーで保存処理を呼ぶ。
- 新しいファクターを追加する: kabusys.research に関数を追加し、zscore_normalize/feature_exploration と組み合わせる。
- 実運用: KABUSYS_ENV を paper_trading / live に切り替え、監視・安全制御（kill flag / PID 管理）を導入してください。

---

必要であれば、README に「実際のテーブル定義」「サンプル .env.example」「デプロイスクリプト例」「cron / systemd ユニット例」などを追加できます。どの情報を優先して追加しますか？