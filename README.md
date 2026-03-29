# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群。  
ETL（J-Quants からのデータ取得）、ニュース収集と LLM による記事センチメント評価、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定のトレース）など、アルゴリズムトレード向けのコア機能を含みます。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 主な機能一覧
- 動作要件 / 推奨パッケージ
- セットアップ手順
- 環境変数（.env）の例
- 使い方（主要 API の例）
- ディレクトリ構成
- 注意点 / 設計方針のハイライト

---

## プロジェクト概要

KabuSys は、日本株自動売買やリサーチ用途に必要なデータ基盤・分析・監査機能をまとめた Python パッケージです。主に以下を提供します。

- J-Quants API からの差分 ETL（株価日足 / 財務 / 市場カレンダー）
- RSS ベースのニュース収集と前処理（SSRF / gzip / トラッキング除去対策を含む）
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント評価（銘柄単位）
- マーケットレジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- ファクター計算（Momentum / Value / Volatility 等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレース）
- DuckDB を用いたローカルデータ格納と処理

設計上、ルックアヘッドバイアスを避けるために日付参照の扱いに注意が払われています（内部で datetime.today()/date.today() を不用意に参照しない等）。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（レートリミット / リトライ / トークン自動更新 / DuckDB 保存）
  - fetch_* / save_* 系関数
- data.pipeline
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェックの一連処理
- data.news_collector
  - RSS 取得・前処理・raw_news への冪等保存支援
- data.calendar_management
  - 営業日判定・next/prev_trading_day / calendar_update_job
- data.quality
  - 品質チェック群（欠損・スパイク・重複・日付整合性）
- data.audit
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
- ai.news_nlp
  - calc_news_window / score_news: ニュースを銘柄別に集約し LLM でセンチメント付与
- ai.regime_detector
  - ETF(1321)のMA200乖離とマクロ記事の LLM センチメントを組み合わせて日次レジーム判定
- research
  - calc_momentum, calc_value, calc_volatility 等、ファクター計算と feature_exploration（forward returns、IC、summary）
- data.stats
  - zscore_normalize などの統計ユーティリティ

---

## 動作要件 / 推奨パッケージ

- Python 3.10 以上（型アノテーションの union `X | Y` を使用）
- 必要となる主要パッケージ（使用する機能により異なる）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

インストール例（最低限）:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

プロジェクト側で requirements.txt を用意している場合はそれを使用してください。

---

## セットアップ手順

1. リポジトリをクローンしてソースを配置
2. Python 環境の準備（推奨: venv / pyenv）
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定（.env または OS 環境変数）
5. DuckDB ファイル（デフォルト: data/kabusys.duckdb）を使う場合は、親ディレクトリを作成しておく（多くの関数は自動で作成する場合あり）
6. OpenAI / J-Quants の API キー等を設定

自動的な .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動で読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。

---

## 環境変数（.env の例）

主に以下の変数が使用されます（必須はモジュール内で _require によって検査されます）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注連携時）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI を使う場合に使用（score_news / score_regime 呼び出し時にも引数で指定可）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring など）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると自動 .env ロードを無効化

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要 API のサンプル）

以下は簡単な利用例です。実行前に必要な環境変数を用意してください。

- DuckDB 接続の準備:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査スキーマの初期化:
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn, transactional=True)
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（AI）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で明示してもよい
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

- レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- ファクター計算（リサーチ用）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- データ品質チェック:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意:
- score_news/score_regime は OpenAI API 呼び出しを行います。api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants の操作では JQUANTS_REFRESH_TOKEN が必要です（settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要なファイル構造（`src/kabusys` 以下）です。実装済みモジュールを一覧します。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数/設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースの LLM によるスコアリング
    - regime_detector.py             — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 他）
    - etl.py                         — ETL 結果クラスのエクスポート
    - news_collector.py              — RSS 取得・前処理
    - calendar_management.py         — マーケットカレンダー管理
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore_normalize等）
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Value / Volatility 等
    - feature_exploration.py         — forward returns / IC / summary / rank
  - monitoring/ (エクスポートのみを __all__ に含めている可能性あり)
  - strategy/, execution/, monitoring/ (パッケージ概要に含まれるがここでは実装の有無に依存)

（実際のリポジトリではさらに tests、scripts、docs などが存在することが想定されます）

---

## 注意点・設計方針のハイライト

- ルックアヘッドバイアス対策:
  - 多くのモジュールは内部で date.today() を不用意に参照せず、呼び出し元から target_date を与える設計です。
  - DB クエリでは date < target_date の排他条件や、取得日時（fetched_at）を保存する等の配慮があります。
- 冪等性:
  - 保存処理（save_*）は ON CONFLICT DO UPDATE による冪等操作を行います。
  - ETL は差分取得・backfill をサポートし、部分失敗時に既存データを不要に壊さない設計です。
- フェイルセーフ:
  - LLM 呼び出しやネットワークエラーは多くの箇所でフォールバック（例: macro_sentiment = 0.0）を行い、致命的な停止を避ける工夫があります。
- セキュリティ / 安全性:
  - news_collector は SSRF 防止（リダイレクト検査 / private IP 検査）、XML パースに defusedxml を使う、レスポンスサイズ制限等を実装しています。
- ロギング:
  - 各モジュールは logging を使用しており、LOG_LEVEL 環境変数で制御できます。

---

## 最後に

この README はコード内コメント・ドキュメントストリングに基づいてまとめた概要です。各モジュールの詳細な使い方（API の引数・戻り値・エラー挙動）については、対象モジュールの docstring を参照してください。実運用環境では、API キーの管理、バックアップ、監査ログの保存ポリシー、実際の発注フローの冪等性検証などを十分に行ってください。

必要であれば、README にサンプル .env.example、詳細なデプロイ手順、CI 用のコマンド例、よくあるトラブルシュート項目などを追加で作成します。どの項目が要るか教えてください。