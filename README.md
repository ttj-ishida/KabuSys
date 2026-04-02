# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants）・ニュース収集・LLMによるニュースセンチメント・ファクター算出・監査ログ等、運用／リサーチ／戦略実装に必要な機能群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群から構成される Python パッケージです。

- データ取得・保存・品質チェック（J-Quants API → DuckDB）  
- RSS ニュース収集と前処理、銘柄紐付け  
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄・マクロ）  
- 市場レジーム判定（ETF MA と LLM を合成）  
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ  
- 監査ログ（signal → order → execution のトレーサビリティ）初期化ユーティリティ

設計原則として、バックテストでのルックアヘッドバイアスを防ぐために「現在時刻を直接参照しない」実装方針が各モジュールで守られています。また、外部 API 呼び出しには適切なリトライ／レート制御が実装されています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得 + DuckDB へ冪等保存）
  - カレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュースコレクタ（RSS の正規化・SSRF対策・前処理・保存）
  - 品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ（init_audit_db / init_audit_schema）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA 乖離とマクロニュースを合成して market_regime を更新
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（スピアマン）や統計サマリー

その他、設定管理モジュール `kabusys.config.Settings` により環境変数の読み込みや検証を行います。

---

## 必要条件

- Python 3.10 以上（| 型注釈等を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

プロジェクトに requirements.txt / pyproject.toml がある想定ですが、手動でインストールする場合は:

pip install duckdb openai defusedxml

※ Slack 通知等を使う場合は slack-sdk などを追加インストールしてください。

---

## セットアップ手順

1. リポジトリをクローン

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール

   pip install -e .            # パッケージ化されている場合
   # または最低限:
   pip install duckdb openai defusedxml

4. 環境変数の設定

   プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN    ← J-Quants の refresh token
   - OPENAI_API_KEY           ← OpenAI API キー（score_news/score_regime で参照）
   - KABU_API_PASSWORD        ← kabuステーション API を使う場合
   - SLACK_BOT_TOKEN          ← Slack 通知を使用する場合
   - SLACK_CHANNEL_ID         ← Slack 通知先

   その他設定（任意、デフォルトあり）:
   - KABUSYS_ENV (development | paper_trading | live) 既定: development
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) 既定: INFO
   - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, などは Settings 参照

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-...
   KABUS_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データディレクトリを作成（必要に応じて）

   mkdir -p data

---

## 使い方（簡易例）

以下はいくつかの代表的なユースケース例です。実運用ではログ・例外処理・リトライ等を適切に組み合わせてください。

共通: DuckDB 接続の作成

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

1) 日次 ETL を実行する

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略すると today）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュースセンチメント（銘柄単位）を計算して ai_scores に書き込む

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written_count = score_news(conn, target_date=date(2026,3,20))
print("書き込み銘柄数:", written_count)
```

3) 市場レジームを判定して market_regime テーブルへ書き込む

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

4) 監査ログ用 DuckDB を初期化する（監査スキーマの作成）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/monitoring.db")
# init_audit_db は必要なテーブル・インデックスを作成します
```

5) 設定値参照（コードから環境設定を参照する）

```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- OpenAI API 呼び出しは `OPENAI_API_KEY` を参照します。明示的に引数 `api_key` を渡すことも可能です。
- 各 API 呼び出しはネットワークエラーや API 制限に対して内部でリトライ処理を実装していますが、運用ではレートやコストに注意してください。
- 本ライブラリはルックアヘッドバイアス防止のため、target_date の扱いが厳しく設計されています。バックテスト用途でも日付管理に注意してください。

---

## 主要モジュール・ディレクトリ構成

リポジトリの主要なファイル/ディレクトリ（抜粋）:

src/kabusys/
- __init__.py                  - パッケージ初期化（バージョン等）
- config.py                    - 環境変数 / 設定管理（Settings）
- ai/
  - __init__.py
  - news_nlp.py                - ニュースセンチメント（銘柄）
  - regime_detector.py         - 市場レジーム判定（1321 MA + マクロ）
- data/
  - __init__.py
  - jquants_client.py          - J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py                - ETL パイプライン（run_daily_etl など）
  - etl.py                     - ETLResult 再エクスポート
  - calendar_management.py     - 市場カレンダー管理（営業日判定等）
  - news_collector.py          - RSS 収集と前処理
  - quality.py                 - データ品質チェック
  - audit.py                   - 監査ログ（テーブル定義・初期化）
  - stats.py                   - 汎用統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py         - ファクター計算（momentum, value, volatility）
  - feature_exploration.py     - 将来リターン、IC、統計サマリー

各モジュールはドキュメント文字列で処理フローや設計方針・制約を明記しており、ETLやAI呼び出しの fail-safe 挙動やリトライ挙動が注記されています。

---

## 設定項目（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (必須: score_news/score_regime を使う場合)
- KABU_API_PASSWORD (kabuステーション連携)
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live) — 実行モード

設定は .env(.local) または環境変数から読み込まれます。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ロギング / モニタリング

- 各モジュールは logging を利用して情報・警告・エラーを出力します。`LOG_LEVEL` 環境変数で制御可能です。
- 実運用ではバックアップ・監視（pid ファイル、CPU/メモリ/ディスク閾値）・Slack 通知などを組み合わせて監視運用を行ってください（Settings に閾値等のプロパティがあります）。

---

## 開発・テスト時の注意

- DuckDB を使うため、テスト時は `:memory:` を使ってインメモリ DB を立てることが可能です（例: duckdb.connect(":memory:")）。
- AI/API 呼び出し部分は内部で分離されたラッパー関数を持つため、ユニットテストでは該当関数をモックして副作用を抑制できます（コード内にモックの想定箇所がコメントで示されています）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定して制御できます。

---

必要があれば、README を具体的な実行スクリプト例（systemd ユニット、cron、Dockerfile、docker-compose 等）、CI 設定例、より詳細な API 使用例（関数の引数・戻り値のスキーマ）で拡張できます。どの部分を拡張したいか教えてください。