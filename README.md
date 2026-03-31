# KabuSys

日本株向けのデータプラットフォーム＆自動売買支援ライブラリ群。  
ETL（J-Quants からの株価／財務／カレンダー取得）、ニュース収集・NLP による銘柄センチメント、ファクター計算、監査ログ（トレーサビリティ）などを提供します。

現在のバージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムやリサーチ基盤でよく使う処理群を集めた Python パッケージです。主要な責務は以下のとおりです。

- J-Quants API からの差分 ETL（株価日足、財務データ、マーケットカレンダー）
- ニュース収集（RSS）と OpenAI を使ったニュースセンチメント（銘柄別）スコアリング
- 市場レジーム判定（ETF とマクロニュースを組み合わせた日次判定）
- ファクター計算 / 特徴量探索（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution までのトレーサビリティ）
- 設定管理（環境変数 / .env の自動読み込み、保護された上書きルール）

設計上の注意点として「ルックアヘッドバイアスを避ける」「冪等性を重視する」「外部 API 呼び出しはリトライ＋レート制御を実装する」といった方針が各モジュールに反映されています。

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants からの株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務データ取得（fetch_financial_statements / save_financial_statements）
  - JPX マーケットカレンダー取得（fetch_market_calendar / save_market_calendar）
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- ニュース処理
  - RSS 収集（fetch_rss、URL 正規化、SSRF 対策、gzip 対応）
  - ニュース前処理（URL 除去・空白正規化）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコア（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM による合成 → score_regime）
- 研究・リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）
  - IC 計算 / ランク変換 / 統計サマリー（calc_ic, rank, factor_summary）
  - Z スコア正規化ユーティリティ（zscore_normalize）
- 品質管理
  - 欠損・スパイク・重複・日付不整合検出（quality.run_all_checks 等）
- 監査ログ
  - signal_events / order_requests / executions テーブル定義・初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 環境変数経由での設定参照（kabusys.config.settings）

---

## セットアップ手順

※以下はパッケージ配布方法や pyproject.toml に依存します。最低限の手順を示します。

1. リポジトリをクローン
   ```
   git clone <このリポジトリのURL>
   cd <リポジトリ>
   ```

2. Python 仮想環境の作成（推奨）
   - Python 3.10 以上を推奨（型ヒントに | 型を使用）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 必須ライブラリ（例）
     ```
     pip install duckdb openai defusedxml
     ```
   - その他、プロジェクトが依存するパッケージがある場合は requirements.txt / pyproject.toml に従ってください。

4. 環境変数設定
   - 必須の環境変数（少なくとも以下は設定が必要な関数あり）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（fetch 等で必要）
     - SLACK_BOT_TOKEN — （Slack 統合を行う場合）
     - SLACK_CHANNEL_ID — （Slack 統合を行う場合）
     - KABU_API_PASSWORD — kabuステーション API を使う場合
   - データベースパス（任意）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   - .env 自動読み込み
     - パッケージはプロジェクトルート（.git または pyproject.toml のある場所）を探し、.env → .env.local を自動で読み込みます。
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env の最小例
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単なコード例）

以下はモジュールを使うときの代表例です。duckdb を使ってローカル DB に接続して関数を呼ぶパターンが多くあります。

- 共通インポートと DB 接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API キーを環境変数に設定している場合）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(mom), mom[:3])
```

- 監査ログ DB の初期化（専用 DB ファイル）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査ログを記録できます
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.env, settings.log_level)
```

注意:
- OpenAI を使う関数（score_news, score_regime 等）は api_key 引数で明示的にキーを渡すこともできます。渡さない場合は環境変数 `OPENAI_API_KEY` を参照します。
- 多くの関数は副作用（DB への書き込み）を持つため、テスト時はモックやインメモリ DB（duckdb.connect(":memory:")）を使うと良いです。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要なファイル／モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの OpenAI スコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 収集（fetch_rss 等）
    - calendar_management.py — マーケットカレンダー管理（is_trading_day など）
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（calc_momentum, calc_value, calc_volatility）
    - feature_exploration.py — 将来リターン・IC・サマリー等
  - research/（その他ファイル）
  - (その他) strategy/, execution/, monitoring/ など（環境により追加モジュール）

---

## 設定・環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (score_news / score_regime で使用可能)
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

.env 自動読み込みの仕様:
- プロジェクトルート（.git または pyproject.toml を基準）を見つけて `.env` → `.env.local` の順で読み込みます。
- `.env.local` は `.env` の上書き（override=True）を行いますが、既存 OS 環境変数は保護されます。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 開発・テストに関する注意

- DuckDB を利用しているため、ローカルでのテストは duckdb のインメモリ DB が便利です（duckdb.connect(":memory:")）。
- OpenAI 呼び出しはリトライや JSON モードを使ったパースを行っていますが、ユニットテストでは _call_openai_api をモックして外部ネットワークコールを回避してください（各モジュールに差し替えポイントあり）。
- J-Quants API 呼び出しは rate limiter とリトライを持ちます。テストでは jquants_client._request や fetch_* をモックしてください。
- news_collector は SSRF 対策・受信サイズ制限・XML サニタイズ（defusedxml）を実装しています。外部 RSS の取り扱いは慎重に行ってください。

---

## ライセンス・貢献

（この README はコードベースからの自動生成に基づく簡易ドキュメントです。実際のプロジェクトの LICENSE、CONTRIBUTING ガイドラインをリポジトリに追加してください。）

---

必要であれば、README に入れるサンプル .env.example、requirements.txt、または個別モジュール（ETL の実行スクリプトや systemd / cron の設定例）を追加で作成します。どの情報を優先して詳述しますか？