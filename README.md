# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、リサーチ（ファクター計算）、監査ログ、マーケットカレンダー管理、API クライアント等を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要なデータ基盤・解析・監査機能群を提供する Python パッケージです。主な目的は以下です。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL
- RSS ベースのニュース収集と OpenAI によるニュースセンチメント（銘柄別）スコアリング
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック、マーケットカレンダー管理、J-Quants クライアント

設計上のポイント:
- ルックアヘッドバイアス防止（内部では date 引数を受け、date.today() を不用意に参照しない）
- 冪等性（DB 保存は ON CONFLICT / INSERT/DELETE/BEGIN/COMMIT を意識）
- 外部 API 呼び出しにはリトライやレート制御を実装
- DuckDB を主要 DB として使用

---

## 機能一覧

- data
  - jquants_client: J-Quants API からの fetch / save（daily_quotes, financial_statements, market_calendar 等）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ（run_prices_etl 等）、ETLResult を返却
  - news_collector: RSS 収集、テキスト前処理、raw_news への保存（SSRF 対策・サイズ制限あり）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定、next/prev_trading_day、calendar_update_job
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 共通統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で評価して ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュース LLM を合成して market_regime を作成
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理: kabusys.config.Settings（環境変数 / .env の自動ロード）

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントで union 表記等を使用しているため近年の Python を想定）
- 必要な外部ライブラリ（例: duckdb, openai, defusedxml）をインストールしてください。

例:
```bash
# 仮想環境作成（任意）
python -m venv .venv
source .venv/bin/activate

# パッケージインストール（プロジェクトルートに pyproject.toml/setup.py がある想定）
pip install -e .

# 依存が別途必要なら例:
pip install duckdb openai defusedxml
```

環境変数（重要）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL / jquants_client 用）
- KABU_API_PASSWORD : kabuステーション API のパスワード（注文連携がある場合）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（オプション）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID（オプション）
- OPENAI_API_KEY : OpenAI API キー（ai.news_nlp / regime_detector 実行時）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等（監視設定）
- KABUSYS_ENV : development / paper_trading / live（環境モード）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL

自動 .env ロード:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例の .env（プロジェクトルートに置く）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な API と実行例）

基本的には DuckDB 接続を作り、目的の関数を呼びます。以下は簡単なサンプルです。

DuckDB 接続の作成:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # デフォルトパスを使用する場合
```

ETL（日次パイプライン）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（None の場合は today）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースのセンチメント (銘柄別 ai_scores 書き込み):
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
written_count = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {written_count}")
```

市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブル・インデックスが作成されます
```

ニュース収集（RSS）:
- `kabusys.data.news_collector.fetch_rss(url, source)` を呼び、得られた記事を DB に保存するロジックを作成して利用します。
- ニュース保存部分はプロジェクト内の別関数（news_collector 内の保存ロジック）を利用してください。

設定（config）の利用:
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- OpenAI 呼び出しは `api_key` 引数で注入可能（テスト容易化）
- 各種 API 呼び出しはリトライ実装があるものの、API キー・ネットワークの設定は事前に整えてください
- DuckDB の executemany は空リストを渡すとエラーになるバージョンがあるため、ライブラリ内で対策されています

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュール（src/kabusys 配下）:

- kabusys/
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
    - calendar_management.py
    - news_collector.py
    - stats.py
    - audit.py
    - (その他: export ETLResult, etc.)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - data/*（上記各モジュール）

主要なテーブル（コード中で参照される想定スキーマ）
- raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily, market_regime, signal_events, order_requests, executions, etc.

---

## 追加情報 / 運用上の注意

- ログレベルや環境（KABUSYS_ENV）で動作モードが変わるため、運用時は KABUSYS_ENV を適切に設定してください（development / paper_trading / live）。
- OpenAI の利用はコストがかかるため、バッチサイズやバッチ頻度を調整してください（news_nlp は銘柄をチャンク化して API を呼ぶ実装）。
- J-Quants API はレート制限があります（120 req/min）。jquants_client は内部でスロットリング・リトライを実装していますが、運用時は API 利用上限を考慮してください。
- 自動 .env ロードは便利ですが、CI/CD やテスト環境で挙動を固定したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動で設定を注入してください。
- DuckDB ファイルはバックアップ・スキーマ管理を検討してください（監査ログは削除しない運用を想定）。

---

以上がこのコードベースの README.md の日本語版概略です。必要であれば、README に以下の追加情報を付け加えます:
- 開発用の依存リスト（requirements.txt / pyproject.toml の抜粋）
- 各テーブルのスキーマ定義（DDL の抜粋）
- 実運用でのデプロイ手順（systemd / コンテナ / cron ジョブ例）
- 簡易のユニットテスト・モック戦略（OpenAI / ネットワーク呼び出しの差し替え方法）