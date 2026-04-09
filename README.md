# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、ニュースの LLM ベース評価、ファクター計算、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存関係
- セットアップ手順
- 簡単な使い方（サンプル）
- 環境変数（主な設定）
- 主要モジュールと役割（ディレクトリ構成）
- 補足・設計方針

---

## プロジェクト概要
KabuSys は日本株のデータパイプラインとリサーチ／自動売買基盤のためのユーティリティ群です。  
主に以下を目的としています：
- J-Quants API からの株価・財務・カレンダーの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と記事の前処理、銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄ごと）およびマクロセンチメント評価
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）および特徴量探索
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）

設計上、バックテスト等でルックアヘッドバイアスが入らないように日時参照に注意して実装されています。

---

## 機能一覧
- データ取得（J-Quants）
  - 株価日足（OHLCV）
  - 財務（四半期 BS/PL）
  - JPX 市場カレンダー
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と前処理（URL 除去・正規化）
- OpenAI を用いた NLP 評価
  - 銘柄ごとのニュースセンチメント（ai_scores へ保存）
  - マクロニュース + ETF MA200 乖離から市場レジーム判定（market_regime へ保存）
- 研究用ユーティリティ
  - ファクター算出（momentum, volatility, value）
  - 将来リターン、IC、統計サマリー、Zスコア正規化
- データ品質チェック（複数の検査）
- 監査ログスキーマの初期化（DuckDB）
- JPX カレンダーの運用（営業日判定、next/prev/get_trading_days）

---

## 前提条件 / 依存ライブラリ
- Python 3.10+
- 必要ライブラリ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ以外の追加が必要な場合はプロジェクトの requirements を参照してください（無ければ上記を pip で導入）。

例:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

ローカル開発では editable インストールを推奨します:
```bash
python -m pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -e .            # または requirements.txt があれば pip install -r requirements.txt
   ```
4. 環境変数を設定
   - プロジェクトルートに `.env`（およびローカル用の `.env.local`）を置くと自動ロードされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 主な必須値：`JQUANTS_REFRESH_TOKEN`。OpenAI を使う機能は `OPENAI_API_KEY` が必要です（関数呼び出し時に引数で渡すことも可能）。
5. データベース用ディレクトリを作る（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 簡単な使い方（サンプル）

- DuckDB に接続して日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI キーを使ってニューススコアを生成する:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("scored codes:", n_written)
```

- 市場レジームスコアを付与する:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB の初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 環境変数（主な設定）
（.env に設定して自動ロード可能）

- 認証・API
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
  - KABU_API_PASSWORD: kabu ステーション API パスワード
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- データベース / パス
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- Paper Trading
  - PAPER_FILL_MODE: instant|partial|never|reject（デフォルト: instant）
- 監視 / 制御
  - PID_FILE_PATH, KILL_FLAG_PATH
  - KILL_FLAG_CLEAR_ON_START: "1" で起動時クリア
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- 実行環境
  - KABUSYS_ENV: development|paper_trading|live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

（README 内で使っているキー以外のオプションは config.Settings を参照してください）

---

## ディレクトリ構成（主要ファイル）
以下はパッケージ内の主要モジュールと役割の一覧です（src/kabusys 以下）:

- __init__.py
  - バージョン情報・公開パッケージ

- config.py
  - .env / 環境変数の読み込みと Settings 提供

- ai/
  - news_nlp.py: RSS ニュースを銘柄ごとに集約し、OpenAI でセンチメントを算出して ai_scores に書き込む
  - regime_detector.py: ETF(1321) MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を更新

- data/
  - pipeline.py / etl.py: 日次 ETL パイプライン（差分取得・保存・品質チェック）
  - jquants_client.py: J-Quants API の呼び出し・保存ロジック（レートリミット・リトライ・トークン管理）
  - news_collector.py: RSS 取得、前処理、raw_news への保存・銘柄紐付け
  - calendar_management.py: market_calendar 管理、営業日判定ユーティリティ
  - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit.py: 監査ログ（signal_events, order_requests, executions）スキーマ初期化
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - etl (thin re-export): ETLResult

- research/
  - factor_research.py: Momentum / Value / Volatility / Liquidity 等のファクター計算
  - feature_exploration.py: 将来リターン・IC・統計サマリ等

（その他、実際のプロジェクトでは追加モジュールや CLI スクリプトが存在する可能性があります）

---

## 補足・設計方針
- ルックアヘッドバイアス防止: モジュール内の主要処理は date 引数を受け取り、datetime.today()/date.today() を直接参照しない設計です（テストやバックテストでの正確な再現性を確保）。
- フェイルセーフ: 外部 API の失敗やデータ不足のケースは例外でプロセス全体を止めないようにフォールバックやログ記録を行います（例: LLM 失敗時に macro_sentiment=0.0）。
- 冪等性: DB 保存処理は基本的に ON CONFLICT DO UPDATE などで冪等（idempotent）に実行されるよう設計されています。
- セキュリティ対策: news_collector は SSRF 対策（プライベート IP 拒否、リダイレクト検査）、defusedxml を使った XML パースを行います。

---

必要であれば README にコマンドライン例（systemd サービス定義、cron ジョブ例）、より詳細な環境変数一覧やスキーマ定義、運用手順（監視・ログローテーション・バックアップ）を追加します。どの情報を優先的に追記しますか？