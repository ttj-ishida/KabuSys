# KabuSys

日本株向けのデータプラットフォームと自動売買/リサーチ用ライブラリ群です。  
ETL（J-Quants からのデータ取得・保存）、データ品質チェック、ニュースに対する AI ベースのセンチメントスコアリング、ファクター計算、監査ログ（発注→約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 特徴（概要）

- J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）
  - ページネーション・レート制限・トークン自動リフレッシュ・リトライ対応
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（RSS）と前処理（正規化・SSRF 対策）
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄毎センチメント）と市場レジーム判定
  - JSON Mode を利用し、レスポンスを厳格に検証
  - レート制限・ネットワーク障害・5xx に対する指数バックオフ等のリトライ処理
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- 環境変数ベース設定管理（.env/.env.local の自動読み込み機能あり）

---

## 主な機能一覧

- data
  - ETL pipeline（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - market calendar 管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - news_collector（RSS 取得と前処理）
  - quality（品質チェック：missing_data, spike, duplicates, date_consistency）
  - stats（zscore_normalize）
  - audit（監査スキーマ初期化、init_audit_db）
- ai
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
- research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib 等を使用

（プロジェクトに requirements.txt があればそちらを利用してください。なければ例として下記をインストールします）

例:
```bash
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` として配置するか、OS の環境変数を利用します。
   - 自動読み込みの仕組み: デフォルトでプロジェクトルートの `.env` → `.env.local` の順で読み込みます。
     - 自動ロードを無効化するには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
   - オプション / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視用設定
5. データディレクトリの準備
   - デフォルトでは `data/` 配下に DuckDB ファイル等が作成されます。必要に応じて作成：
     ```bash
     mkdir -p data
     ```

---

## 使い方（主な例）

以下はパッケージ内 API をプログラムから呼ぶ際の例です（簡易例）。すべての関数は DuckDB 接続オブジェクトを受け取ります。

- 基本設定と接続
```python
from datetime import date
import duckdb
from kabusys.config import settings

# デフォルトパスは settings.duckdb_path
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリングを実施（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数を使う場合は None
print("書き込んだ銘柄数:", written)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ（監査 DB）初期化
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path とは別に監査専用DBを用意することも可能
audit_conn = init_audit_db(settings.duckdb_path)
# または init_audit_db(":memory:") でインメモリ DB を作る
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(factors, ["mom_1m","mom_3m","mom_6m","ma200_dev"])
```

- RSS フィードの取得（news_collector）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
# raw_news テーブルへ挿入するロジックはプロジェクト内の保存関数を利用してください
```

注意:
- ai モジュールは OpenAI の API キーを必要とします。API 呼び出しはコストとレート制限があるため実行環境での取り扱いに注意してください。
- すべての「日付」はルックアヘッドバイアスを避けるため、関数に明示的に target_date を渡す設計です。内部で date.today() の参照を最小化しています。

---

## 環境変数の詳細

主要な設定（例）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

自動.env ロードの仕様:
- プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` を読み込み、続けて `.env.local` を上書きで読み込みます。
- OS 環境変数は保護され、.env による上書きを防止します（ただし .env.local は上書き可能）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主なファイルと説明）

以下は src/kabusys 配下の主要モジュールと概略です。

- __init__.py
  - パッケージのエクスポート（data / strategy / execution / monitoring）
- config.py
  - 環境変数読み込み／Settings クラス（各種設定プロパティ）
- ai/
  - __init__.py
  - news_nlp.py — ニュースを銘柄ごとに集約し OpenAI でセンチメントを算出、ai_scores に書き込み
  - regime_detector.py — ETF（1321）MA200 乖離とマクロニュースの合成で市場レジーム判定
- data/
  - __init__.py
  - pipeline.py — ETL のメイン実装（run_daily_etl 等）と ETLResult
  - etl.py — ETLResult の再エクスポート
  - jquants_client.py — J-Quants API クライアント（fetch_* / save_*）
  - news_collector.py — RSS 収集 / 前処理 / SSRF 対策
  - calendar_management.py — マーケットカレンダー管理（is_trading_day, next_trading_day 等）
  - quality.py — データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログスキーマ定義と初期化（signal_events / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility / Liquidity 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー等

（上記は主要部分のみ。実際のプロジェクトではさらに strategy / execution / monitoring 等のモジュールが存在します。）

---

## 注意事項 / 運用上のヒント

- DuckDB の executemany はバージョンによって挙動が異なる点に注意（pipeline モジュールで空リスト処理を回避する対策あり）。
- OpenAI 呼び出しは失敗時にフォールバック（スコア=0.0）する設計が多いですが、実行コストやレート制限を考慮して運用してください。
- ニュース収集は外部 HTTP を行うため、運用環境ではネットワーク制御・DNS 解決やプロキシ設定、SSRF 対策を適切に構成してください。
- 監査ログテーブルは削除しない前提で設計されています。マイグレーションやスキーマ変更は慎重に行ってください。

---

## 貢献 / 開発

- ローカルでの開発時は `.env.local` にテスト用の設定を書き、`KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して自動ロードを制御すると便利です。
- テスト時には OpenAI / J-Quants への実際の API 呼び出しをモックすることを推奨します（コード内に差し替え用のフックが用意されています）。

---

必要であれば README に「実行例（CLI あるいは cron スクリプト）」「.env.example のテンプレート」「ユニットテストの実行方法」などを追加できます。どの情報を優先して追記したいか教えてください。