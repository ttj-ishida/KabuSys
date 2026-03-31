# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集とAIを使ったニュースセンチメント評価、ファクター計算、監査ログ（注文トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築に役立つコンポーネント群を提供します。主な目的は次の通りです。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いたデータ永続化（ETL の冪等保存）
- ニュース収集（RSS）と自然言語処理による銘柄別センチメント評価（OpenAI を利用）
- 市場レジーム判定（価格指標＋マクロニュースセンチメント）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェックモジュール
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマと初期化ユーティリティ

設計上、バックテストや運用でのルックアヘッドバイアスを避ける実装指針（target_date を明示、現在時刻参照の回避など）を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・ページネーション・レート制御）
  - 市場カレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS の安全取得、前処理、raw_news への保存補助）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマと DB 初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI により算出し ai_scores に書き込む
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュースセンチメントを合成して市場レジームを判定
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）
2. リポジトリをチェックアウト
3. 仮想環境を作成して有効化（例）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate
4. 依存パッケージのインストール
   - requirements.txt があれば:
     - pip install -r requirements.txt
   - 無ければ主要なランタイム依存をインストール:
     - pip install duckdb openai defusedxml
     - （プロジェクトに応じて requests などを追加してください）
5. パッケージを開発モードでインストール（任意）
   - pip install -e .
6. 環境変数設定
   - プロジェクトルートの .env / .env.local に設定を置くことで自動読み込みされます（優先順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 送信先チャンネルID
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 呼び出し時に引数で渡すことも可）
   - その他（デフォルトあり）:
     - KABUSYS_ENV (development|paper_trading|live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

例 .env（最低限のイメージ）:
```
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
```

---

## 使い方（簡単な例）

以下はライブラリ API の典型的な使い方例です。実行前に必ず環境変数を設定してください。

- DuckDB 接続の作成（デフォルトファイルパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（株価・財務・カレンダーの差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（OpenAI が必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を渡すか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使って監査テーブルへアクセス
```

- ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
```

注意点:
- OpenAI 呼び出し部はネットワークや API レート・エラーを考慮した実装になっています。API キー未設定時は例外が発生します。
- ETL やニューススコアリングは対象データ（raw_* テーブル）の存在／前提を必要とします。初回ロードには J-Quants データの一括取得等が必要です。

---

## 主要な環境変数（まとめ）

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
  - KABU_API_PASSWORD — kabu ステーション API のパスワード
  - SLACK_BOT_TOKEN — Slack 通知用
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル
  - OPENAI_API_KEY — OpenAI 利用時に必要（関数引数で渡すことも可能）

- 任意（デフォルトあり）:
  - KABUSYS_ENV=development|paper_trading|live（default: development）
  - LOG_LEVEL=DEBUG|INFO|...（default: INFO）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロードを無効化）

設定管理の挙動:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml が見つかる場所）を探索し、.env/.env.local を読み込みます（OS 環境変数が優先）。
- .env.local は .env を上書きします（OS 環境変数はどちらも保護される）。

---

## ディレクトリ構成

以下は主要モジュールの概観（src/kabusys 配下）です。実装ファイルと役割を簡潔に記載します。

- src/kabusys/
  - __init__.py — パッケージ初期化、公開サブパッケージ指定
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント生成（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の公開（エイリアス）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - news_collector.py — RSS ニュース収集・前処理
    - quality.py — データ品質チェック群（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログ（DDL / 初期化ユーティリティ）
    - stats.py — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py — モメンタム／バリュー／ボラティリティ等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー等
  - ai/, research/, data/ に関連する他ユーティリティ群

（実際のファイル数やサブモジュールはコードベースに依存します。README は主要モジュールを抜粋しています。）

---

## 開発・貢献

- ローカルでの試験やユニットテストを行う際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを抑制できます。
- OpenAI や J-Quants との外部 API 呼び出しはモック化しやすいように設計されています（内部呼び出し関数を patch して差し替え可能）。
- 機能追加・バグ修正は PR を歓迎します。ドキュメント・型注釈・ログを重視したコードスタイルを維持してください。

---

## 参考

- 各モジュールの docstring に設計指針・処理フロー・フェイルセーフの方針が記載されています。実装詳細やパラメータの理由付けなどはソース内のコメントを参照してください。

---

必要であれば README にサンプル .env.example、より詳細な起動コマンド（systemd / supervisor の PID 管理や監視連携、Slack 通知の実装例）や典型的な ETL スケジュール例（cron / Airflow）を追記します。どの情報を追加しますか？