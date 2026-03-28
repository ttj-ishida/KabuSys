# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants からの市場データ取得）、ニュース収集と LLM によるセンチメント解析、ファクター計算、監査ログ（発注・約定追跡）などの機能を提供します。

- パッケージ名: kabusys
- 現在のバージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- J-Quants API から株価・財務・カレンダー等のデータを取得して DuckDB に保存する ETL パイプライン
- RSS でニュースを収集し raw_news に保存するニュースコレクタ
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント（ai_scores）と市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal / order_request / executions）用のスキーマ初期化ユーティリティ

設計上の注意点（抜粋）:
- ルックアヘッドバイアス対策：内部処理で現在時刻を直接参照せず、target_date ベースで判定します。
- 冪等性：ETL の保存処理や監査テーブル初期化は基本的に冪等です（ON CONFLICT / INSERT … DO UPDATE など）。
- フェイルセーフ：外部 API（OpenAI / J-Quants）失敗時に例外をそのまま投げずにフォールバックする箇所が多数あります（ログ出力で継続）。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - ニュース収集（RSS）と前処理
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news）: 銘柄ごとのセンチメントスコアを ai_scores に書き込む
  - 市場レジーム判定（score_regime）: ETF（1321）の MA とマクロニュースの LLM 評価を合成して market_regime を更新
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・評価（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込みと settings オブジェクト（自動 .env ロード、必須 env の検査）

---

## 前提条件

- Python 3.10 以上を想定（typing の記法等を使用）
- ネットワークアクセス（J-Quants API / RSS / OpenAI）
- 必要な Python パッケージ（例: duckdb, openai, defusedxml 等）をインストールしてください。

推奨（例）
- duckdb
- openai
- defusedxml

requirements.txt 等はリポジトリに合わせて用意してください。

---

## 環境変数（主要）

以下の環境変数を設定してください（必須は明記）。config.Settings により .env ファイルまたは OS 環境変数から読み込まれます。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注等で必要な場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

Optional / デフォルトあり:
- KABUSYS_ENV: environment。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL、デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

OpenAI:
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の省略時に参照）

.env の自動ロード優先順位:
OS 環境変数 > .env.local > .env
（プロジェクトルートは .git または pyproject.toml を基準に探索されます）

---

## セットアップ手順（例）

1. リポジトリをクローン / 開発環境を用意
2. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   （プロジェクトの requirements.txt があればそれを使用）
4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、OS 環境変数に設定する
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     KABU_API_PASSWORD=...
5. DuckDB 用ディレクトリを作成（必要に応じて）
   - mkdir -p data
6. 監査 DB の初期化（任意）
   - Python から init_audit_db を呼び出して監査用 DB を初期化

---

## 使い方（例）

以下はよく使う操作のサンプルです。実行前に環境変数（OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN 等）を設定してください。

- DuckDB 接続の作成例
```python
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores に書き込む
print(f"scored {written} codes")
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # market_regime に書き込む
```

- 監査ログ DB の初期化（監査用の独立 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
```

- データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意:
- OpenAI 呼び出しは課金対象です。API キーは安全に管理してください。
- 実発注ロジックは本パッケージの一部に含まれる可能性があります（kabu ステーション連携など）。実行前に env の KABUSYS_ENV を確認し、live モードでの実行は慎重に行ってください。

---

## 開発・デバッグのヒント

- 自動 .env ロードを無効化したい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロード処理をスキップします（テスト時に便利）。
- Settings の検証:
  - settings.env / settings.log_level などは値検証が入っています。不正な値を入れると ValueError が発生します。
- OpenAI API 呼び出しは内部でリトライや 5xx の扱いを設けていますが、呼び出し失敗時は各関数はロバストに 0 や空リストでフォールバックする設計が多いです。ログレベルを上げて詳細を追ってください。

---

## ディレクトリ構成（要約）

以下は主要モジュールのツリー（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research のユーティリティは kabusys.data.stats を参照

（ファイル数が多いのでここでは主要ファイルのみを列挙しています。各モジュール内に更に多くの関数・ヘルパーが実装されています。）

---

## ライセンス / 責任範囲

- 本README はコードの構造と使い方を簡潔にまとめたものです。実運用に当たっては、API キーやトークンの管理、バックテスト、リスク管理、発注ロジックの安全性などを十分に確認してください。
- 実際の売買に用いる場合、各自で動作検証・監査を行い、自己責任で運用してください。

---

### 連絡先 / 貢献
プロジェクトに関する修正提案やバグ報告はリポジトリの issue にお願いします。README の説明や usage サンプルを拡充する PR も歓迎します。