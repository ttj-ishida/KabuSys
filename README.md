# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター / リサーチ関数、監査ログ（トレーサビリティ）、市場カレンダー管理、監視用設定などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的に沿って設計されたモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（DuckDB 保存・冪等処理）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント分析と市場レジーム判定
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → executions）用のスキーマ作成ユーティリティ
- 環境設定の自動読み込み（`.env` / `.env.local`）と設定ラッパー

設計方針として、Look-ahead バイアスを避ける実装、冪等性、外部 API の再試行・バックオフ、セキュリティ対策（SSRF、XML パース安全化）を重視しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants からのデータ取得（株価 / 財務 / 市場カレンダー）
  - DuckDB への保存（save_* 関数、ON CONFLICT ベースの冪等）
  - rate limit + retry + token refresh を備えた HTTP クライアント
- data.pipeline
  - 日次 ETL 実行エントリ（run_daily_etl）と個別 ETL ジョブ
  - ETL 結果を表す ETLResult
- data.news_collector
  - RSS フィード収集、前処理、raw_news への保存用ユーティリティ
  - SSRF 対策・受信サイズ制限・XML 安全パーサ
- ai.news_nlp / ai.regime_detector
  - ニュースの銘柄別センチメント推定（OpenAI）
  - マクロニュース + ETF (1321) MA200乖離に基づく市場レジーム判定
  - JSON Mode / 再試行・フォールバックを考慮した実装
- research.*
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- data.quality
  - 欠損、スパイク、重複、日付不整合のチェック。QualityIssue を返す
- data.audit
  - 監査ログ用テーブル定義 & 初期化（init_audit_schema / init_audit_db）
- config
  - .env 自動読み込み（プロジェクトルート検出）
  - Settings クラスからアプリ設定を参照可能

---

## 前提 / 必要条件

- Python 3.10+
  - 型注釈に Python 3.10 の union 型 (A | B) を利用しています
- 推奨パッケージ（開発環境に応じてインストールしてください）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の他パッケージがあれば requirements.txt を用意してください）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーに配置

2. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt がある場合）
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数の設定（.env をプロジェクトルートに配置すると自動で読み込まれます）
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須 / 推奨環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN=...   （必須: J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD=...      （kabu API パスワード）
     - SLACK_BOT_TOKEN=...        （監視通知で使用）
     - SLACK_CHANNEL_ID=...       （監視通知で使用）
     - OPENAI_API_KEY=...         （AI スコアリングで必須）
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト development）
     - LOG_LEVEL=INFO|DEBUG|...   （デフォルト INFO）
     - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト保存先）
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid

   サンプル .env（プロジェクトルートに .env として保存）:
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

5. （任意）DuckDB ファイルやデータフォルダを作成
   - デフォルトでは data/ 以下にファイルを作成します。必要なら予めディレクトリ作成を行ってください。
   - mkdir -p data

---

## 使い方（簡易例）

以下はライブラリ API を直接呼び出す簡単な例です。実運用ではエラーハンドリングやログ設定、プロセス制御を適切に行ってください。

- DuckDB に接続して日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を None にすると今日が対象
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（銘柄別）を実行する

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジームをスコアリングして保存する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログデータベースを初期化する

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブルが作成されます
```

- 研究用ファクター計算の例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# 返り値は dict のリスト（各銘柄ごとのファクター）
```

注意:
- OpenAI 呼び出しは OPENAI_API_KEY を参照します（関数引数でキー注入も可能）。
- 実際の ETL / 発注システムと組み合わせる場合は、KABU（kabuステーション）やブローカー API への接続処理、監視（monitoring）等を別途実装してください（本コードベースでは方向を示すモジュールが含まれています）。

---

## 環境変数 / 設定の詳細

config.Settings で参照される主な変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 BOT トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（SQLite）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH — 実行 PID 保存先
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視しきい値
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

また、OpenAI の API キーはモジュールが直接 os.environ["OPENAI_API_KEY"] を参照しています（score_news / score_regime 等）。必要に応じて関数引数で api_key を渡せます。

自動 .env のロード:
- プロジェクトルート (.git または pyproject.toml を起点) に .env / .env.local があれば起動時に自動読み込み（.env.local が優先して上書き）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      stats.py
      quality.py
      calendar_management.py
      news_collector.py
      audit.py
      etl.py (ETLResult re-export)
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/__init__.py
    (その他: strategy, execution, monitoring パッケージが __all__ に記載されていますが、今回の提供コード断片には含まれていないファイルがある可能性があります)

各モジュールの役割:
- ai: OpenAI を用いた NLP / レジーム判定
- data: ETL、J-Quants クライアント、ニュース収集、品質チェック、監査ログ
- research: ファクター計算と統計ユーティリティ
- config: 環境変数・設定の読み込み・検証

---

## 運用上の注意 / ベストプラクティス

- Look-ahead バイアス回避:
  - すべてのスコアリング/ETL関数は内部で date 引数を受け取り、date.today() を直接参照しないよう設計されています。バックテストや再現性のため、必ず明示的な target_date を渡すことを推奨します。
- OpenAI 呼び出し:
  - API 呼び出しには再試行・フォールバックが組み込まれていますが、API 利用料やレート制限に注意してください。テスト時は _call_openai_api をモックする設計です。
- DB トランザクション:
  - 主要な書き込みは BEGIN/COMMIT を使うなど冪等性・整合性を確保する実装がされていますが、運用コード側でも例外・ROLLBACK を適切に扱ってください。
- セキュリティ:
  - news_collector は SSRF / XML Bomb 等に対処していますが、外部 URL を扱う場合は実行環境のネットワーク制限・プロキシ設定等を検討してください。

---

## 貢献 / 開発

- 新機能やバグ修正を行う際は、まず既存のテスト（もしあれば）を追加・通過させてください。
- OpenAI / J-Quants の外部 API はモック可能な設計になっています（テストでの差し替えポイントを備えています）。

---

必要であれば README に実際の requirements.txt、起動スクリプト（例: 日次 cron / systemd ユニット）やより詳細な設定例、運用フロー（ETL → 品質チェック → モデル更新 → 発注）を追加します。どの情報を優先して追記するか教えてください。