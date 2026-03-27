# KabuSys

日本株向けのデータプラットフォーム & 自動売買（バックテスト・リサーチ・監査ログ含む）ライブラリです。  
DuckDB をデータレイクとして使い、J-Quants からのデータ取得、RSS ニュース収集、LLM によるニュースセンチメント評価、ファクター計算、ETL パイプライン、監査ログ（注文・約定トレーサビリティ）などの機能を提供します。

---

## 主な機能（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務データ、JPX 市場カレンダーを差分取得・保存
  - 差分取得・バックフィル・品質チェックを行う日次 ETL（run_daily_etl）
- データ品質チェック
  - 欠損（OHLC）、スパイク（前日比閾値）、重複、日付不整合の検出
- ニュース収集 & 前処理
  - RSS フィード収集（SSRF 対策、URL 正規化、トラッキング除去）、raw_news 保存
- ニュース NLP（LLM）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - マクロニュース + ETF（1321）200 日 MA 乖離から市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON Mode で呼び出す実装（リトライ・フェイルセーフ）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Spearman）や統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを保証する監査テーブル作成・初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local / 環境変数からの設定読み込み（自動ロード、上書きルール、無効化フラグあり）

---

## セットアップ手順

前提: Python 3.9+ を推奨（型ヒントで union 型や generic が使用されています）。  

1. リポジトリをクローン（またはパッケージを配置）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate
3. 必要パッケージをインストール（最低限の例）
   - pip install duckdb openai defusedxml
   - プロジェクトを編集可能インストールする場合:
     - pip install -e .

注: 実運用では `requirements.txt` / `pyproject.toml` に依存を明記してください。

---

## 環境変数（主要設定）

自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（名前・用途・デフォルト）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime が必要な場合）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例 .env（最小）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

設定は `kabusys.config.settings` からアクセス可能です。

---

## 使い方（主要 API と実行例）

下記はライブラリを利用する際の典型的な例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

- DuckDB 接続の生成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日
print(result.to_dict())
```

- ニュースセンチメントスコア（銘柄ごと）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} symbols")
```
score_news は OpenAI API キーを環境変数 `OPENAI_API_KEY` から取得します。関数引数で `api_key` を渡すことも可能です。

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```
同様に OpenAI API キーを必要とします。

- 監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または init_audit_schema(conn) で既存接続へスキーマを追加
```

- カレンダー / 営業日判定ユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- LLM 呼び出し時のフェイルセーフ: API エラーやパース失敗時には無理に例外を投げずにデフォルト値（例: macro_sentiment=0）で継続する設計です。ログで警告が出ます。
- Look-ahead バイアス対策: 各モジュールは明示的な target_date を受け取り、内部で datetime.today() を安易に参照しない設計になっています。

---

## 実運用上のヒント

- テストや CI で自動的に .env を読み込ませたくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しはコストとレート制限があるため、バッチサイズやモデル（_MODEL）を調整してください。
- J-Quants API はレート制限（120 req/min）に合わせて RateLimiter が組み込まれていますが、長時間のバックフィルでは注意してください。
- DuckDB の executemany に関しては一部バージョンで空リストを受け付けない制約に対応した実装になっています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py        — 銘柄単位ニュースセンチメント（score_news）
    - regime_detector.py — マクロ + ETF MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理、営業日判定
    - etl.py                 — ETL の公開型/再エクスポート
    - pipeline.py            — 日次 ETL パイプライン（run_daily_etl 等）
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - quality.py             — データ品質チェック（check_missing_data 等）
    - audit.py               — 監査ログテーブル定義 / 初期化
    - jquants_client.py      — J-Quants API クライアントと保存処理
    - news_collector.py      — RSS ニュースの収集 / 前処理
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — forward returns, calc_ic, factor_summary, rank
  - ai / data / research パッケージはそれぞれの機能群を提供します。

---

## 開発・テスト

- ユニットテストの実行方針:
  - OpenAI や外部 API 呼び出しはモック化してテストしてください。
  - news_nlp / regime_detector 内の _call_openai_api 等はテスト時に patch しやすい設計になっています。
- lint / type-check: 推奨（flake8 / mypy 等）

---

## ライセンス・貢献

この README はコードベースから生成された概要です。実際のリポジトリに合わせて LICENSE ファイルや貢献ガイド（CONTRIBUTING.md）を追加してください。

---

問題点や追加で README に載せたい内容（例: 実行スクリプト、CI 設定、より詳しい環境変数の例、運用時の注意事項など）があれば教えてください。README を拡張して反映します。