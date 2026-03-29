# KabuSys — 日本株自動売買基盤ライブラリ

KabuSys は日本株向けのデータプラットフォーム、研究（リサーチ）、AIベースのニュース解析、監査ログ／ETL を含む自動売買基盤向けユーティリティ群を提供する Python パッケージです。本リポジトリは DuckDB をデータストアに利用し、J-Quants / JPY 市場カレンダー / RSS ニュース / OpenAI（LLM）などと連携するモジュールを含みます。

---

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存パッケージ
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（設定）
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は次の目的を持つライブラリ群です。

- J-Quants API からの株価・財務・マーケットカレンダー等の差分 ETL（DuckDB へ冪等保存）
- RSS ニュース収集とニュース／銘柄ごとの LLM ベースセンチメント付与
- 市場レジーム判定（ETF MA とニュースセンチメント合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索（IC 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用スキーマ定義と初期化ユーティリティ

設計方針の特徴:
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB + SQL を多用して高速に集計・再現可能な ETL を実現
- 外部 API 呼び出しはリトライ・バックオフや保護（SSRF 対策、サイズ制限等）付き

---

## 主な機能一覧

- data:
  - ETL パイプライン（run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl）
  - J-Quants クライアント（fetch/save 系・認証・レート制御）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS fetch / 前処理 / 保存ロジック）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai:
  - ニュースセンチメント（score_news） — LLM（gpt-4o-mini）を用いた銘柄別スコアリング
  - 市場レジーム判定（score_regime） — ETF 1321 の MA と LLM マクロセンチメントの合成
- research:
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）

---

## 前提・依存パッケージ

（実行に必要と思われる主要パッケージ。実際の requirements.txt を用意してください）

- Python 3.10+（型ヒントに union 型などを使用）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

例:
```bash
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # macOS/Linux
   .venv\Scripts\activate       # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt
   # または最低限:
   pip install duckdb openai defusedxml
   ```
4. 開発モードでインストール（パッケージとして利用する場合）
   ```bash
   pip install -e .
   ```
5. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml の親ディレクトリ）を自動検出して `.env` / `.env.local` を自動的に読み込みます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（例は後述）を設定してください。

---

## 環境変数（主要）

このパッケージは多数の環境変数を参照します。主なもの：

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- kabu ステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- OpenAI
  - OPENAI_API_KEY (score_news / score_regime で使用。引数で直接渡すことも可能)
- DB パス（デフォルト値あり）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- 実行モード / ログ
  - KABUSYS_ENV (development | paper_trading | live) デフォルト: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) デフォルト: INFO

.env の例（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意: 自動ロードは .git または pyproject.toml を基準にプロジェクトルートを判定します。

---

## 使い方（主要 API）

以下は代表的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の返り値）を受け取る設計です。

1) DuckDB 接続を作る
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルが無ければ作成
```

2) 日次 ETL を実行（市場カレンダー / 株価 / 財務 / 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのセンチメントスコアを作成（LLM を呼ぶ）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"written scores: {written} 件")
```

4) 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```
- 注意: score_news / score_regime は OpenAI API を呼びます。OPENAI_API_KEY を設定するか、関数に api_key を渡してください。API 呼び出し失敗時はフェイルセーフ（スコア 0.0 等）する設計です。

5) 監査ログ DB を初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作られ、UTC タイムゾーン設定が行われます
```

6) ファクター / リサーチ利用例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

mom = calc_momentum(conn, date(2026, 3, 20))
fwd = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

---

## 実装上の注意点 / 動作仕様

- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml の存在）から `.env` と `.env.local` を自動的に読み込みます。
  - 読み込み順: OS 環境変数 > .env.local (override=True) > .env (override=False)
  - テスト環境などで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定し、JSON mode を利用して構造化出力を期待します。
  - RateLimit, Timeout, 5xx などに対してリトライ実装あり。致命的な失敗時にも処理継続（フェイルセーフ）するよう設計。
- J-Quants クライアント:
  - レート制限（120 req/min）に合わせた RateLimiter を内包。401 時は自動トークンリフレッシュを行うロジックがあります。
  - 保存は DuckDB 側で冪等になるよう ON CONFLICT DO UPDATE を使用。
- データ品質:
  - 品質チェックは Fail-Fast ではなく、検出した問題をリストで返します。呼び出し側で判断できます。
- 日付の扱い:
  - ほとんどの API は内部で date オブジェクトを受け取り、UTC naive datetime を扱う／UTC を明示的に使う箇所があります。ルックアヘッドバイアス防止のため、現在時刻を直接参照しない設計が多く採用されています。

---

## ディレクトリ構成（主要ファイルと説明）

（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings クラス（settings オブジェクト）を提供
    - 自動 .env/.env.local 読み込みのロジック
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None): ニュースを LLM でスコアリングして ai_scores に書込
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None): ETF（1321）MA とマクロニュースから市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API 用クライアント（fetch/save/get_id_token 等）
    - pipeline.py
      - ETL のメイン処理（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
      - ETLResult データクラス
    - news_collector.py
      - RSS フィードのフェッチ・前処理・保存ロジック（SSRF/サイズ制限等の対策あり）
    - calendar_management.py
      - market_calendar の取得・営業日判定ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize（クロスセクション正規化）
    - audit.py
      - 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）
    - etl.py
      - ETLResult の再エクスポート（互換用）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_value / calc_volatility
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank

---

## 推奨ワークフロー（簡易）

1. DuckDB を初期化（必要であればスキーマ作成コードを用意）
2. .env を準備して J-Quants / OPENAI / Slack 等のキーをセット
3. nightly のジョブで run_daily_etl を実行してデータ基盤を更新
4. 毎朝ニューススコア（score_news）とレジーム判定（score_regime）を実行
5. 研究ワークフローでは research モジュールの関数を使ってファクター集計・IC 計算を行う
6. 発注フローを組む場合は audit スキーマを初期化し、信号 → 発注 → 約定の監査を保存

---

## 貢献 / ライセンス

本 README には記載していませんが、実際のリポジトリでは CONTRIBUTING.md / LICENSE を用意してください。

---

以上がこのコードベースの概要・セットアップ・使い方・構成説明です。必要であれば、README に含める実行サンプル（cron/times）や schema 初期化スクリプト、requirements.txt の雛形、CI 実行手順なども追加できます。どの内容を優先して追記しますか？