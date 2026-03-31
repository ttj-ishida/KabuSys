# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP による銘柄センチメント推定、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（発注トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・前処理・研究・運用を支援するモジュール群です。主な責務は次のとおりです。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（duckdb 保存、冪等）
- RSS ニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別・マクロ）
- マーケットレジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- ファクター計算（モメンタム／ボラティリティ／バリュー）と研究系ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を格納する監査 DB 初期化ユーティリティ

設計上の重要点:
- ルックアヘッドバイアスを避けるため、内部実装は `date`/`datetime` を外部から渡す形（内部で date.today() を直接参照しない箇所が多い）。
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを備える（失敗時はスコアを 0 とする等）。
- DuckDB を主要なオンディスク DB として扱い、冪等保存（ON CONFLICT）を重視。

---

## 機能一覧

主な公開 API / 機能（モジュール別）

- kabusys.config
  - 環境変数の自動ロード（.env, .env.local）と Settings オブジェクト（J-Quants / kabu / Slack / DB パスなど）

- kabusys.data
  - jquants_client: J-Quants API 取得・保存（fetch_* / save_*）
  - pipeline: 日次 ETL 実行 run_daily_etl（差分取得・保存・品質チェック）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - news_collector: RSS 取得・正規化・raw_news への保存
  - quality: 各種データ品質チェック
  - audit: 監査テーブルの初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の共通統計ユーティリティ
  - ETLResult: ETL 実行結果データクラス

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロセンチメントを合成して market_regime に書き込む

- kabusys.research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提（依存関係）

最低限必要な Python バージョン: 3.10+（PEP604 の `X | Y` 型ヒントを使用しているため）  
主な依存パッケージ（例）:
- duckdb
- openai
- defusedxml

pip を使ったインストール例（適宜 requirements を用意してください）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発インストール（プロジェクトをパッケージ化している場合）
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／取得
2. Python 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 環境変数を設定（`.env` ファイルをプロジェクトルートに置くと自動読み込みされます）
   - 自動ロードは既定で有効。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
   - 読み込み優先順位: OS 環境変数 > .env.local > .env
4. 必須環境変数（Settings で参照）:
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
   - OPENAI_API_KEY — OpenAI API キー（news/regime スコア実行時に必要）
   - その他（任意、デフォルトあり）:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development/paper_trading/live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...）

例 .env:

```
JQUANTS_REFRESH_TOKEN=あなたの_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（コード例）

以下は主要ユースケースの簡単な使い方です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を想定します。

1) DuckDB 接続と日次 ETL の実行

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# ファイル DB に接続（なければ作成）
conn = duckdb.connect("data/kabusys.duckdb")

# ETL を実行（target_date を指定しなければ今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュース NLP スコアリング（score_news）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")

# OPENAI_API_KEY は環境変数にセットするか api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) マーケットレジーム判定（score_regime）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査 DB 初期化（監査テーブルを作る）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn 経由で signal_events / order_requests / executions テーブルが使用可能
```

5) ファクター計算・研究ユーティリティ

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# factors は [{'date': ..., 'code': '1301', 'mom_1m': ..., ...}, ...]
```

---

## 注意点・運用上のヒント

- OpenAI 呼び出しや J-Quants API 呼び出しはレート制限・エラーに備えた実装がされていますが、API キーの管理や課金に注意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から行われます。テストや一時的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ETL は差分取得とバックフィル（デフォルト 3 日）を行い、API 側の後出し修正に対応します。
- DuckDB の executemany の仕様に依存する箇所があるため、空のパラメータでの executemany は避ける実装になっています（空チェックが入っています）。
- ニュース収集は SSRF 対策・レスポンスサイズ制限・XML の安全パース（defusedxml）を行っていますが、運用環境ではソースの信頼性も考慮してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイルと役割（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py            — 銘柄ニュース NLP スコアリング
    - regime_detector.py     — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定）
    - news_collector.py      — RSS ニュース収集
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログテーブル定義・初期化
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — モメンタム／バリュー／ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・サマリー等

その他:
- pyproject.toml / setup.cfg 等（プロジェクトルートに置く想定）
- .env.example（環境変数サンプルを用意すると良い）

---

## テスト・開発

- OpenAI やネットワーク呼び出しを含む関数は、呼び出し箇所（_call_openai_api / _urlopen / _request など）をモックしてユニットテストを容易にしています。
- 自動ロードされる .env をテストで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要に応じて README に追記します（例: 実際の .env.example、CI/CD 設定、詳しい ETL スケジュール例、Slack 通知の利用方法、kabu ステーション連携の詳細など）。どの項目を詳しく追加しましょうか？