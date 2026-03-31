# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集とAIによるニュース解析、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを提供します。

---

## プロジェクト概要

- DuckDB を内部データベースとして用い、J-Quants API や RSS からデータを取得・保存します。
- ニュースを LLM（OpenAI）でセンチメント解析し、銘柄ごとのAIスコアや市場レジームを算出します。
- ETL パイプライン・データ品質チェック・マーケットカレンダー管理など、データプラットフォーム機能を備えます。
- 監査ログテーブルによりシグナル→発注→約定までのフローを UUID で追跡可能にします。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得（ページネーション・リトライ・レート制御付き）
  - raw_prices / raw_financials / market_calendar への冪等保存（ON CONFLICT）
- ETL
  - run_daily_etl：市場カレンダー → 株価 → 財務 → 品質チェックの一括実行
  - 個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出（QualityIssue を返す）
- ニュース収集
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、前処理）と raw_news 保存ロジック
- ニュースNLP（OpenAI）
  - score_news：銘柄ごとのニュースをまとめて LLM へ送り ai_scores を生成・保存
  - レート制御・バッチサイズ・リトライ・レスポンスバリデーションを実装
- 市場レジーム判定（regime_detector）
  - 1321（ETF）200日MA 乖離 + マクロニュース LLM センチメントを合成して daily market_regime を算出
- リサーチ / ファクター解析
  - calc_momentum / calc_value / calc_volatility 等のファクター計算
  - calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルの初期化・インデックス作成 helper

---

## セットアップ手順

前提: Python 3.10+ 推奨

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール  
   （requirements.txt がある場合はそれを使う想定。ない場合は主要依存のみ）
   ```
   pip install duckdb openai defusedxml
   # 他に必要なパッケージがあれば追加でインストールしてください
   ```

4. パッケージをインストール（開発モード）
   ```
   pip install -e .
   ```

5. 環境変数設定（.env をプロジェクトルートに配置することを推奨）
   - config モジュールは自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（後述）を設定してください。

---

## 環境変数（主なもの）

config.Settings で参照される代表的な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT：監視設定
- KABUSYS_ENV: environment（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

簡易の .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は Python REPL やスクリプトから呼び出す最小例です。

- DuckDB 接続を用意して ETL を実行する
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しなければ今日（settings.env により動作は変わる）を使用
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが環境変数 OPENAI_API_KEY にある想定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（別DBに分ける場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査テーブルを操作できます
```

- .env の自動ロードを無効化したい（テスト等）
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## よく使うモジュール / API

- kabusys.config.settings: 環境設定アクセス
- kabusys.data.pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl / ETLResult
- kabusys.data.jquants_client: J-Quants API の低レベルラッパ（fetch_* / save_*）
- kabusys.data.news_collector: fetch_rss / RSS 前処理
- kabusys.ai.news_nlp: score_news（ニュースを LLM でスコアリング）
- kabusys.ai.regime_detector: score_regime（市場レジーム判定）
- kabusys.research.*: ファクター計算・解析ユーティリティ
- kabusys.data.audit: init_audit_schema / init_audit_db（監査テーブル初期化）

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なディレクトリ/ファイル構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                       : 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    : ニュースの LLM スコアリング
    - regime_detector.py             : 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              : J-Quants API クライアント（取得 / 保存）
    - pipeline.py                    : ETL パイプライン（run_daily_etl 等）
    - quality.py                     : データ品質チェック
    - news_collector.py              : RSS 収集・前処理
    - calendar_management.py         : マーケットカレンダー管理
    - stats.py                       : 汎用統計ユーティリティ
    - audit.py                       : 監査ログ（テーブル定義・初期化）
    - etl.py                         : ETLResult エクスポート
  - research/
    - __init__.py
    - factor_research.py             : Momentum / Value / Volatility 計算
    - feature_exploration.py         : 将来リターン、IC、統計サマリー
  - ai/、monitoring/、execution/ 等の他サブパッケージ（プロジェクトによって拡張）

実際のツリーは src/kabusys 以下をご参照ください。

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定等は target_date より未来のデータを参照しないよう設計されています（datetime.today() を直接参照しない等）。
- 冪等性:
  - ETL の保存は ON CONFLICT / UPDATE ベースで冪等化。
- 外部API 呼び出し:
  - OpenAI / J-Quants の呼び出しはリトライ・バックオフ・タイムアウト等を実装しています。
- セキュリティ:
  - RSS 取得時の SSRF 対策、XML パースの defusedxml 使用、レスポンスサイズ制限などが実装されています。
- テスト:
  - 一部の内部関数（例えば OpenAI 呼び出し）をモックしやすいように実装されています。

---

## 貢献 / ライセンス

- コントリビュート歓迎です。Issue / PR を通して提案してください。  
- ライセンス表記はリポジトリの LICENSE を参照してください（本 README に明記されていない場合は管理者に確認してください）。

---

README の補足や実際の運用手順（cron / systemd / 監視・アラート連携等）や、CI / テストの詳細を追加したい場合は指示ください。