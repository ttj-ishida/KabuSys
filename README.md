# KabuSys

日本株のデータ取得・ETL・リサーチ・AI支援・監査ログを備えた自動売買基盤ライブラリです。  
このリポジトリは、J-Quants / JPX / RSS / OpenAI を利用してデータを集約し、DuckDB に永続化、AI によるニュースセンチメント / 市場レジーム判定、ファクター計算や品質チェック、監査ログ（トレーサビリティ）の仕組みを提供します。

---

## 主要な特徴（ハイライト）

- データ収集（J-Quants）
  - 株価日足（OHLCV）、財務データ（四半期）、
  - JPX マーケットカレンダー（祝日・半日・SQ）
  - レート制限、リトライ、トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）
  - 日次 ETL の統合実行（run_daily_etl）
- ニュース収集 & NLP
  - RSS から記事収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
  - API 失敗時は安全側（スコア 0.0）にフォールバックする設計
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events, order_requests, executions 等の監査テーブルを DuckDB に初期化
  - UUID によるトレーサビリティ確保
- 設定管理
  - .env / .env.local / OS 環境変数読み込み（プロジェクトルート検出）
  - 必須環境変数の明示的検査

---

## 機能一覧（モジュール単位）

- kabusys.config
  - .env 自動読み込み（.git または pyproject.toml を基準にプロジェクトルートを探索）
  - settings オブジェクトで環境変数アクセス
- kabusys.data
  - jquants_client: J-Quants API クライアント（fetch / save / pagination / auth）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl、ETLResult
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得 & 前処理、raw_news への保存補助
  - calendar_management: JPX カレンダー管理・営業日判定
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出と ai_scores へ保存
  - regime_detector.score_regime: ETF（1321）MA とマクロセンチメントから市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要環境 / 依存パッケージ

- Python 3.10+
- 必須（実行する機能に応じて）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, json, datetime, logging 等を使用

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ化されていれば: pip install -e .
```

---

## 環境変数（主要）

以下はコード中で参照される主要な環境変数です（.env.example を作成して利用してください）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client 用）
- SLACK_BOT_TOKEN — （通知等で使用する場合）
- SLACK_CHANNEL_ID — Slack 通知用チャンネルID
- KABU_API_PASSWORD — kabuステーション API パスワード（実行機能により必要）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時）

オプション（デフォルト値あり）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を検出）から .env を自動読み込みします。
- 読み込み順: OS 環境変数 > .env.local > .env
- テストなどで自動ロードを無効にしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

注意:
- Settings クラスは必須変数がない場合に ValueError を投げます（利用前に環境変数を整えてください）。
- KABUSYS_ENV の有効値は {development, paper_trading, live} のみです。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして作業ディレクトリへ
2. 仮想環境作成・有効化
3. 依存パッケージをインストール
4. プロジェクトルートに .env を作成（下記サンプルを参照）
5. DuckDB データベースを作成（初回は ETL 等でテーブルが自動作成されますが、audit 用に初期化することが可能）

サンプル .env（必要なキーだけ置く例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_slack_channel
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（コード例）

下記はライブラリの代表的な使い方例です。DuckDB の接続は duckdb.connect(path) を利用します。

1) 日次 ETL を実行する
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュースセンチメントを算出して ai_scores に保存する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を参照
print(f"written scores: {written}")
```

3) 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB を初期化する（独立した監査 DB を作成する場合）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # :memory: も可
```

5) 研究用ファクター計算の呼び出し例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
# mom は [{"date": ..., "code": "1332", "mom_1m": 0.05, ...}, ...] のようなリスト
```

注意点:
- OpenAI API 呼び出し部はモデル（gpt-4o-mini）を利用します。API 利用制限・コストに注意してください。
- score_news / score_regime は API 失敗時にフェイルセーフ（0.0）で継続するよう実装されていますが、API キー自体が未設定の場合は ValueError が投げられます。

---

## ディレクトリ構成（要約）

以下は主要なファイル・モジュール構成の抜粋（src/kabusys 以下）:

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
    - etl.py
    - quality.py
    - news_collector.py
    - calendar_management.py
    - stats.py
    - audit.py
    - etl.py (再エクスポート用)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research パッケージ内で zscore_normalize 等を利用
  - その他: strategy/, execution/, monitoring/ など（パッケージ公開名には含まれるが今回の抜粋には実装がありません）

（上記は本リポジトリのコード抜粋に基づく要約です。実際のリポジトリではさらにファイルが存在する可能性があります。）

---

## 実運用での注意（運用メモ）

- J-Quants の API レート制限（120 req/min）を守るために RateLimiter が実装されていますが、運用で大量に並列呼び出しを行わないよう注意してください。
- OpenAI のコスト、レイテンシ、レート制限を考慮した運用設計が必要です。大規模バッチは分割して実行することを推奨します（news_nlp はバッチ処理を行う設計）。
- 本ライブラリは Look-ahead Bias 防止を設計方針としており、内部で date.today()/datetime.today() を参照しない（または引数で日付を明示する）箇所が多くあります。バックテスト用途では target_date を明示して利用してください。
- .env の自動読み込みはプロジェクトルート検出に依存します。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して明示的に環境を注入することが可能です。
- DuckDB のバージョンや API 互換性（executemany の空リスト扱いなど）に注意のこと。

---

## ライセンス・貢献

この README では具体的なライセンス表記・貢献フローは記載していません。プロジェクトのルートに LICENSE / CONTRIBUTING.md があればそちらを参照してください。

---

何か追加で README に含めたい内容（例: CI 手順、より詳しい .env.example、サンプルデータでの動作確認手順、Docker イメージ等）があれば教えてください。README を追記・拡張して整備します。