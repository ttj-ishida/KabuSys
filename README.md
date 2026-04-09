# KabuSys

日本株向け自動売買 / データパイプライン基盤ライブラリ

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量/ファクター計算、ニュースの NLP による銘柄センチメント評価、マーケットレジーム判定、監査ログ（トレーサビリティ）などを含む自動売買基盤のライブラリ群です。バックテストや本番運用のデータ基盤（DuckDB）や監視・発注周りの基礎機能を提供します。

設計上の要点：
- Look-ahead バイアス回避（内部で date.today() 等を不用意に参照しない）
- ETL / 保存 は冪等（ON CONFLICT 等）に対応
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価、レトライ・フェイルセーフ実装
- J-Quants API からの差分取得とレートリミット制御
- DuckDB ベースのローカルデータレイク構成

---

## 主な機能一覧

- 環境設定管理（自動 .env 読み込み、必須項目の取得）
  - 自動ロード順序: OS 環境変数 > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- データ取得 / ETL（J-Quants 経由）
  - 日次株価（OHLCV）、財務データ、取引カレンダーの差分取得と保存
  - run_daily_etl を中心とした日次パイプライン
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue）
- ニュース収集 & NLP
  - RSS からのニュース収集（SSRF対策、URL 正規化）
  - OpenAI を用いた銘柄ごとのセンチメント評価（score_news）
- マーケットレジーム判定
  - ETF(1321) の MA200 とマクロニュースのセンチメントを合成して日次レジーム判定（score_regime）
- ファクター計算 / 研究ユーティリティ
  - Momentum / Value / Volatility 等のファクター計算、将来リターンやIC計算、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions といった監査用テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
- ユーティリティ
  - データベース初期化、統計ユーティリティ（zscore_normalize）など

---

## セットアップ手順

1. Python 環境作成（推奨: 仮想環境）
   - macOS / Linux:
     - python3 -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml
   - 実運用では requirements.txt / pyproject.toml がある想定でそちらを使ってください。
   - （ローカル開発インストール）
     - pip install -e .

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（省略可）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須で使用する場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE: paper trading の fill モード（instant|partial|never|reject）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード DB パス（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH / KILL_FLAG_PATH: 実行監視関連
   - KABUSYS_ENV: environment（development | paper_trading | live）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   簡易 .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

以下は Python から各主要機能を呼ぶ簡単な例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を作成して日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数に設定するか、api_key 引数に指定する
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム（bull/neutral/bear）をスコアリングして書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化する:
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# 以後 conn を使って監査テーブルにアクセスできます
```

注意事項:
- OpenAI 呼び出しを行う機能（score_news, score_regime）は OPENAI_API_KEY が必要です。api_key 引数で明示的に渡すこともできます。
- ETL / J-Quants 連携には JQUANTS_REFRESH_TOKEN が必要です（get_id_token が自動で処理します）。
- データベース操作は DuckDB のスキーマに依存します。初回はスキーマ初期化手順（別モジュールに実装想定）を実行してください。

---

## ディレクトリ構成（主要ファイルと説明）

（パッケージルート: src/kabusys）

- __init__.py
  - パッケージのバージョンなどを定義
- config.py
  - 環境変数読み込み・設定管理
  - .env 自動ロードの実装、必須変数チェック（settings オブジェクト）
- ai/
  - __init__.py
    - AI 関連の API を公開
  - news_nlp.py
    - ニュースを銘柄ごとに集約し OpenAI でスコア化して ai_scores テーブルへ保存
  - regime_detector.py
    - ETF の MA とマクロニュースの LLM センチメントを合成して market_regime に保存
- data/
  - __init__.py
  - calendar_management.py
    - JPX カレンダー管理、営業日判定、next/prev_trading_day 等
  - etl.py
    - ETLResult の公開（pipeline の戻り型）
  - pipeline.py
    - 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損、重複、スパイク、日付整合性）
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）の DDL と初期化ユーティリティ
  - jquants_client.py
    - J-Quants API クライアント（レート制御、リトライ、保存関数）
  - news_collector.py
    - RSS 収集、URL 正規化、SSRF 対策、raw_news への保存
- research/
  - __init__.py
    - 研究用 API エクスポート（ファクター/統計）
  - factor_research.py
    - Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py
    - 将来リターン計算、IC（Information Coefficient）、統計サマリー等

---

## 運用上の注意 / ヒント

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います。パッケージ化して配布後でも正しく動作するよう設計されています。
- J-Quants API のレートリミット（120 req/min）をモジュール内で守る実装がありますが、多数の並列プロセスから同一 API を叩く場合は運用側でも注意してください。
- OpenAI 呼び出しはエラーやレート制限に対してリトライ・フォールバック（スコア=0）を行う設計です。ログを参照して API 状況を監視してください。
- DuckDB のバージョンや SQL 機能差による挙動（リストバインドの扱いなど）に依存する箇所があるため、開発環境と本番環境の DuckDB バージョンを合わせることを推奨します。
- paper_trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）によりペーパートレードの振る舞いを切り替えられます。

---

## さらに詳しく / 貢献

- 各モジュールの docstring に主要なアルゴリズムと設計方針が詳細に記載されています。実装を読むことで動作や制約を理解しやすくなっています。
- バグ修正や機能追加の際は、まず該当モジュールのテストを追加してください（ユニットテストで外部 API 呼び出しはモック推奨）。
- セキュリティ面（API キー管理、SSRF、XML パーシング）に注意して実装されていますが、外部フィード追加時は入力検証を忘れないでください。

---

必要ならば README に含めるコマンド実行例（cron / systemd / Docker の起動例）、詳細な .env.example、スキーマ初期化スクリプトのサンプルなども追記できます。どの部分をより詳しく載せたいか教えてください。