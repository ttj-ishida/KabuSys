# KabuSys

バージョン: 0.1.0

日本株向けの自動売買 / データプラットフォームのコアライブラリです。  
データ ETL、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログなどのモジュールを提供します。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 使い方 (主要な API / サンプル)
- 環境変数
- ディレクトリ構成
- 注意事項

---

## プロジェクト概要

KabuSys は日本株向けに設計されたデータプラットフォーム兼リサーチ / 自動売買の基盤ライブラリです。  
主に以下を目的とします。

- J-Quants API からの株価・財務・カレンダー等の ETL（差分取得・冪等保存）
- RSS ニュース収集と LLM によるニュースセンチメント評価（銘柄別 ai_score）
- マーケットレジーム（bull / neutral / bear）の判定（ETF とマクロニュースの融合）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ
- 取引監査ログの初期化・管理（監査テーブル、インデックス、監査 DB 初期化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴:
- Look-ahead バイアスを避ける設計（date.now などを直接参照しない箇所がある）
- DuckDB を採用したローカル分析向けの高速 DB 操作
- OpenAI（gpt-4o-mini）を利用した JSON Mode による安定的な LLM 呼び出し（フォールバック／リトライ実装あり）
- API キーや .env 自動ロード機能を備えた設定管理

---

## 機能一覧

- data:
  - jquants_client: J-Quants との通信（取得＋DuckDB 保存用ユーティリティ）
  - pipeline: 日次 ETL パイプライン（run_daily_etl）と個別ジョブ
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - news_collector: RSS 取得と raw_news への安全保存
  - quality: 品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 監査ログテーブル定義と初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（Zスコア正規化）
- ai:
  - news_nlp.score_news: ニュースから銘柄別センチメント（ai_scores）を生成
  - regime_detector.score_regime: ETF とニュースを合成して市場レジームを判定
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - 環境変数管理（.env / .env.local の自動読み込み、Settings オブジェクト）

---

## 前提条件

- Python 3.10 以上（ソースは型記法（|）を使っています）
- 推奨パッケージ（最小限）:
  - duckdb
  - openai
  - defusedxml

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

（プロジェクトをパッケージ化している場合は pip install -e . / requirements.txt を利用してください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. 環境変数を設定（.env または OS 環境変数）
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（config モジュール）  
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
4. DuckDB 用のディレクトリを用意（デフォルト: data/kabusys.duckdb）

初期化例（監査 DB の初期化）:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: を使うことも可能
# conn を他処理に渡して利用
```

---

## 環境変数

主な必須環境変数（Settings クラスで参照されます）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 関連機能で必須）

任意（デフォルト値あり）:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化
- DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH — 監視 DB などで使用する場合のデフォルト "data/monitoring.db"
- KABU_API_BASE_URL — kabuapi のベース URL（デフォルト http://localhost:18080/kabusapi）

.env に保存する例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-xxxx...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=your_kabu_password
```

.env のパースはシェル形式（export 対応、クォート、コメント等）をサポートします。

---

## 使い方（主要 API、サンプル）

ここでは典型的な利用例を示します。実行は Python スクリプト / REPL／ジョブとして行います。

1) 日次 ETL を実行する（DuckDB 接続を渡す）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（ai_scores）を作成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
print("書き込み銘柄数:", n_written)
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
```

4) ファクター計算 / 研究ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

5) 監査ログスキーマの初期化（既存の DuckDB に監査テーブルを作成）
```python
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

6) カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## ディレクトリ構成

（抜粋。実際のリポジトリで整合を確認してください）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (再エクスポート)
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - (その他 ETL・クライアント周り)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/* utilities (zscore_normalize など)
  - (その他 strategy/execution/monitoring のパッケージ名が __all__ に記載されていますが、ここでは主に data/ ai/ research を中心に実装)

主要ファイルの目的:
- config.py: .env 自動読み込み・Settings の提供
- data/jquants_client.py: J-Quants API の取得、DuckDB への保存
- data/pipeline.py: 日次 ETL パイプライン（run_daily_etl）
- data/news_collector.py: RSS 収集と raw_news 保存
- ai/news_nlp.py: ニュース -> 銘柄別スコア (score_news)
- ai/regime_detector.py: 市場レジーム判定 (score_regime)
- research/*: 研究用のファクター計算と解析ユーティリティ

---

## 注意事項 / 運用上のポイント

- LLM（OpenAI）呼び出しには API キーが必要です。キーは環境変数 `OPENAI_API_KEY` または各関数の api_key 引数で渡してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に行います。配布後やパッケージ化後に動作させる場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化し、環境変数を外部で管理することを推奨します。
- DuckDB executemany の互換性に依存する実装があるため、DuckDB のバージョンに注意してください（メッセージやコード内で互換性に配慮した処理あり）。
- ニュース収集では SSRF 対策・レスポンスサイズ上限・XML の安全パース（defusedxml）等の安全設計が施されていますが、運用時は RSS ソースの監視・ホワイトリスト化を推奨します。
- ETL・API 呼び出しでのエラーハンドリングはフォールバックしつつ継続する設計です（部分失敗時に全体停止しない）。重大な品質問題は quality モジュールで検出できます。

---

必要であれば、README に含める具体的な CLI 実行例や、.env.example のテンプレート、CI 用のセットアップ手順も作成できます。追加要望があれば教えてください。