# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリ群です。  
データ収集（J-Quants）, ETL, データ品質チェック、特徴量計算、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、監査ログ（トレーサビリティ）など一連の処理を提供します。

---

## 概要

KabuSys は以下を目的としたコンポーネント群を含みます。

- J-Quants API を用いた日次株価・財務・マーケットカレンダーの差分取得（ETL）と DuckDB への保存
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS）と LLM による銘柄センチメント付与（ai_scores）
- マクロニュース + ETF（1321）の MA200 乖離を用いた市場レジーム判定
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- 発注／約定に関する監査ログスキーマの初期化ユーティリティ（監査トレーサビリティ）

設計方針としては「バックテスト等でのルックアヘッドバイアス防止」「外部 API 呼び出しは明示的に行う」「フェイルセーフ（API失敗時は継続）」「DuckDB を中心とした冪等保存」等を採用しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API からのデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / fetch_listed_info）
  - DuckDB への保存（save_daily_quotes / save_financial_statements / save_market_calendar）
  - レートリミット制御・トークン自動リフレッシュ・リトライ
- data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl：差分取得＋保存＋品質チェック
  - ETLResult：実行結果の集約
- data.quality
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）
- data.news_collector
  - RSS 取得、テキスト前処理、raw_news への保存（SSRF 回避、サイズ制限、正規化）
- ai.news_nlp
  - raw_news を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に保存（score_news）
- ai.regime_detector
  - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して day 単位で market_regime を生成（score_regime）
- research
  - calc_momentum / calc_value / calc_volatility：ファクター計算
  - feature_exploration：将来リターン計算、IC（スピアマン）計算、統計サマリー
- data.audit
  - 監査テーブル（signal_events, order_requests, executions）の初期化（init_audit_schema / init_audit_db）
- config
  - .env ファイルまたは環境変数から設定を自動ロード（プロジェクトルート検出）し settings オブジェクトを提供

---

## セットアップ手順（ローカル開発向け）

前提
- Python >= 3.10（PEP 604 の union 型表記や型ヒントを使用）
- システムに pip がインストール済み

1. リポジトリをクローンしプロジェクトルートへ移動
   - プロジェクトルートは .git または pyproject.toml の存在で自動判定されます。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存パッケージをインストール
   - 必要な主要パッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml からインストールしてください）

4. 環境変数を設定
   - .env / .env.local をプロジェクトルートに配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — （Slack 通知を使う場合）
     - SLACK_CHANNEL_ID — （Slack 通知を使う場合）
     - KABU_API_PASSWORD — kabu ステーション API を使う場合
     - OPENAI_API_KEY — OpenAI を使う場合（score_news / score_regime で使用）
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デプロイ環境
     - LOG_LEVEL (DEBUG | INFO | ...)
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

5. DB ディレクトリを作成（必要なら）
   - mkdir -p data

---

## 簡単な使い方（コード例）

以下は各主要 API の使用例です。実行前に環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- 共通: settings / DuckDB 接続取得
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー取得 → 株価/財務 ETL → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（指定日分のニュースを集約して ai_scores に書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import os

score_news(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
```

- 市場レジーム判定（1321 の MA200 + マクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import os

score_regime(conn, target_date=date(2026, 3, 20), api_key=os.environ.get("OPENAI_API_KEY"))
```

- 監査ログ用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して発注関連の INSERT を行えるようになります
```

- リサーチ用ファクタ計算例
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
# list[dict] 形式で各銘柄のファクターを返す
```

- calendar ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_trade = is_trading_day(conn, date(2026, 3, 20))
next_day = next_trading_day(conn, date(2026, 3, 20))
```

注意:
- score_news / score_regime は OpenAI API を呼び出します。APIキーの設定と使用料に注意してください。
- run_daily_etl 等は DuckDB 上のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）が前提です。スキーマ初期化は別途スクリプト／DDL を用意してください（本コードには各保存処理の ON CONFLICT を前提とした実装が含まれます）。

---

## 環境変数と設定（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（動作モード）
- LOG_LEVEL — ログレベル
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" をセットすると .env 自動ロードを無効化

自動読み込み:
- config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env を自動で読み込みます。
- 読み込み順序: OS 環境 > .env.local > .env（.env.local は既存環境を上書き）
- テスト等で自動読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル / モジュール）

リポジトリ内の主なモジュール構成（src/kabusys 以下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント（score_news）
  - regime_detector.py  — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py    — J-Quants API クライアント & DuckDB 保存関数
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）、ETLResult
  - etl.py              — ETLResult の再エクスポート
  - news_collector.py   — RSS 収集・正規化
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - quality.py          — データ品質チェック（check_missing_data / check_spike / ...）
  - stats.py            — zscore_normalize 等の統計ユーティリティ
  - audit.py            — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py  — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

（上記は本 README 作成時点の抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 運用上の注意

- OpenAI や J-Quants の API 呼び出しは課金対象・レート制限あり。API キー/利用量に注意してください。
- LLM 依存機能は外部 API の可用性に依存するため、失敗時はフェイルセーフ（スコア 0.0 など）にフォールバックする実装になっていますが、運用時は監視を強化してください。
- DuckDB に保存するスキーマ（テーブル定義）は想定されており、事前にスキーマを作成しておく/初期化処理を行う必要があります。
- 監査ログは削除しない前提設計です。保存先 DB のサイズ・バックアップ計画を検討してください。

---

## 参考 / 次のステップ

- 各モジュールの docstring（ソースコード内）に詳細な設計・前提条件・例が記載されています。実装の挙動を確認するには該当ファイルを参照してください。
- 本 README は概要と利用開始のための最小情報をまとめたものです。CI / 実運用用の設定（ログ集約、監視、ジョブスケジューリング、シークレット管理）は別途整備してください。

---

README に記載の不明点や、特定機能（例: ETL スキーマ初期化スクリプト、Slack 通知の統合、kabu ステーション連携）の追加ドキュメントが必要であれば教えてください。必要に応じてサンプルスクリプトや初期スキーマ DDL を作成します。