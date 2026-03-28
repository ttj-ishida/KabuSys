# KabuSys — 日本株自動売買プラットフォーム（ライブラリ）

このリポジトリは日本株向けのデータパイプライン、研究（リサーチ）ツール、AI ベースのニュースセンチメント処理、監査（オーディット）・監視・発注周りの基盤機能を提供する Python パッケージ群です。バックテスト・研究・本番運用それぞれのフェーズで再利用できるモジュール群を想定しています。

主な設計方針：
- ルックアヘッドバイアス対策（日付参照は明示的な target_date を使用）
- DuckDB を中心としたローカルデータ保存（冪等的な保存ロジック）
- 外部 API（J-Quants / OpenAI / kabuステーション / Slack 等）への堅牢なアクセス機能（レート制御・リトライ・フォールバック）
- 品質チェック・監査ログ・トレーサビリティを重視

---

## 機能一覧（概要）

- data
  - ETL パイプライン（J-Quants からの株価/財務/カレンダー取得、差分更新）
  - market calendar 管理・営業日判定ユーティリティ
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - RSS ベースのニュース収集（SSRF 対策・前処理・冪等保存）
  - J-Quants API クライアント（レート制御・リトライ・トークンリフレッシュ）
  - 監査ログ用スキーマ初期化（signal/order/execution の監査テーブル）
  - 汎用統計ユーティリティ（Zスコア正規化 等）
- ai
  - news_nlp: ニュース記事を LLM（OpenAI）でセンチメント化し ai_scores テーブルへ保存
  - regime_detector: ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して市場レジーム判定
- research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）、統計サマリー 等
- config
  - 環境変数自動読み込み（`.env`, `.env.local`）と Settings オブジェクトの提供

---

## 必要環境・依存

- Python 3.10+
  - 理由: 複数箇所で X | Y の型ヒントを使用しているため
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （必要に応じて）requests 等

インストール例（仮の requirements.txt がある場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# あるいは最低限
pip install duckdb openai defusedxml
pip install -e .
```

---

## 環境変数（主な必須設定）

以下は本パッケージで参照される主な環境変数です。`.env` または OS 環境で設定してください。`kabusys.config` はプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動ロードします。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（data.jquants_client）
- KABU_API_PASSWORD — kabuステーション API パスワード（execution 関連）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知・モニタリング）
- SLACK_CHANNEL_ID — Slack の送信先チャンネル ID
- OPENAI_API_KEY — OpenAI を使う AI 機能（news_nlp, regime_detector）で使用

任意:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

設定はコードから次のように参照できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

---

## セットアップ手順（ローカルで動かす場合の最小手順）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（duckdb, openai, defusedxml など）
4. プロジェクトルートに `.env` を作成（`.env.example` を参照。存在しない場合は必要な環境変数を設定）
5. DuckDB データベースファイルの作成ディレクトリ（例: data/）を作成
6. 必要に応じて監査 DB を初期化

例:
```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 環境変数を .env に記載
mkdir -p data
```

監査 DB の初期化（Python REPL 例）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
# conn を使ってさらに操作可能
```

---

## 使い方（主要機能の簡単な例）

以下は代表的な使い方例です。実行時は必要な環境変数（J-Quants トークンや OpenAI キーなど）をセットしてください。

- DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- news_nlp によるニューススコア付け（ai_scores テーブルへ保存）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（regime_detector）:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 研究用のファクター計算:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)

# 例: mom の mom_1m を zscore 正規化
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- カレンダー関連（営業日判定等）:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- ニュース収集（RSS フィード取得）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI を呼ぶ関数は API キーが必須です（引数で渡すか環境変数 OPENAI_API_KEY を設定）。
- J-Quants 系は JQUANTS_REFRESH_TOKEN（リフレッシュトークン）が必要です。
- ETL / 保存処理は DuckDB のスキーマ（raw_prices, raw_financials, raw_news 等）が事前に存在することを前提にしています。スキーマ初期化ロジックは別途用意するか、サンプルスクリプトで作成してください。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（Settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM ベースセンチメント（ai_scores への書き込み）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 関数）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETLResult のエクスポート
    - calendar_management.py — 市場カレンダー管理・営業日関数
    - news_collector.py — RSS 収集・前処理・保存ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

（上記は主要なファイル群の抜粋です）

---

## 開発・テスト時のヒント

- config._find_project_root() は .git または pyproject.toml を探索して `.env` を自動ロードします。テスト時に自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは個別関数（ai.news_nlp._call_openai_api / ai.regime_detector._call_openai_api）でラップされているため、単体テスト時にモックしやすく設計されています（unittest.mock.patch 等）。
- DuckDB を用いる関数は直接 SQL を実行するため、テストセットアップ時にメモリ上の DuckDB（":memory:"）を使うと容易です。
- ニュース収集は SSRF 対策・受信サイズ上限・XML パースの安全化（defusedxml）を実装しているため、実運用でも比較的安全に動作します。

---

もし README の別途追加項目（例: CLI コマンド、サンプルスキーマ定義、デプロイ手順、CI 設定ファイル）を追加したい場合は、用途に合わせて追記しますので要件を教えてください。