# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 連携による株価・財務・カレンダー取得）、ニュース収集と NLP スコアリング（OpenAI 使用）、研究用ファクター計算、監査ログ/発注トレーサビリティ等のユーティリティを提供します。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境設定管理
  - .env ファイル / OS 環境変数から設定を自動読み込み（自動ロードは無効化可能）
- データ ETL（J-Quants API）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得と DuckDB への冪等保存
  - レートリミット・リトライ・トークン自動リフレッシュ対応
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェックを一括実行
- ニュース収集
  - RSS フィードの安全な収集（SSRF 対策、XML 脆弱性対策、受信サイズ制限）
  - 記事正規化と冪等保存（news_symbols との紐付け想定）
- ニュース NLP（OpenAI）
  - gpt-4o-mini を用いた銘柄別センチメント集約（JSON Mode）
  - レート制限・5xx/429 等のリトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次レジーム判定（bull/neutral/bear）
- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC（スピアマン）・統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - シグナル → 発注 → 約定 までのトレーサビリティ用テーブルを DuckDB に初期化
  - 発注の冪等キー・ステータス管理を想定

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型記法に `X | Y` を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの実際の requirements.txt / pyproject.toml があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン / ソースを準備
2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトに requirements.txt がある場合: pip install -r requirements.txt
4. 環境変数 / .env を準備
   - プロジェクトルート（pyproject.toml または .git がある場所）に `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須（代表例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key (AI 機能を使う場合)
     - KABU_API_PASSWORD=your_kabu_password (kabu API を使う場合)
   - 推奨 / 任意:
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=DEBUG|INFO|...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LINE_CHANNEL_ACCESS_TOKEN= (通知用)
     - LINE_USER_ID=
5. データディレクトリ作成（必要なら）
   - mkdir -p data

例 `.env`（参考）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=xxxx
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要な利用例）

以下は簡単な利用例です。実際にはログ設定や例外処理、ID トークンの注入などを行ってください。

- DuckDB コネクションの作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 単体 ETL ジョブ（株価・財務・カレンダー）:
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from datetime import date

run_prices_etl(conn, date(2026,3,20))
run_financials_etl(conn, date(2026,3,20))
run_calendar_etl(conn, date(2026,3,20))
```

- ニューススコア付与（OpenAI 必須）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026,3,20), api_key="sk-xxx")
print(f"scored {count} codes")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key="sk-xxx")
```

- 監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- RSS フィード取得（ニュース収集一部）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- KABU_API_PASSWORD: kabu ステーション API パスワード（執行系）
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite path（監視用）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用のファイルパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読み込みを無効化

（Settings クラスで参照されるプロパティは kabusys.config.settings から確認可能です）

---

## ディレクトリ構成

以下はソースツリーの主要ファイルと概要（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境設定の読み込み・Settings 定義（.env 自動ロード機能）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約し OpenAI でセンチメントを算出、ai_scores に保存する
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、リトライ、レートリミット）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
    - news_collector.py
      - RSS フィードの安全な収集と前処理
    - quality.py
      - データ品質チェック（欠損、重複、スパイク、日付不整合）
    - audit.py
      - 監査ログスキーマ定義と初期化（signal_events, order_requests, executions）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC, 統計サマリー、rank
  - ai/ (上記)
  - research/ (上記)

---

## 設計上の注意点 / ポリシー（抜粋）

- ルックアヘッドバイアス対策
  - 日付計算や DB クエリは target_date を明示し、datetime.today()/date.today() を不必要に参照しない設計。
- フェイルセーフ
  - AI / API でのエラー時は致命的に停止させず、フォールバック値（例: マクロセンチメント 0.0）を用いる箇所がある。
- 冪等性
  - DB への保存は基本的に ON CONFLICT DO UPDATE・INSERT/DELETE の冪等操作を採用している。
- セキュリティ / 安全性
  - RSS 収集は SSRF 対策、defusedxml で XML 攻撃対策、応答サイズ制限を実施。

---

## 追加 / 開発

- テストや CI:
  - 環境変数により自動 .env 読み込みを無効化できるため、ユニットテスト時の環境制御が容易です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- 拡張ポイント:
  - kabu ステーション連携（execution モジュール）やモニタリング / 通知（LINE）連携は設定により有効化できます。
  - OpenAI モデルやプロンプトは現状の設計に基づき JSON Mode を使う想定ですが、必要に応じて変更可能です。

---

もし README に追記したい具体的な使用例（cron / systemd 起動例、docker 化、CI 環境での実行方法など）があれば教えてください。必要に応じてその用途向けにセクションを追加します。