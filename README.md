# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（モジュール群）。
ETL（J-Quants からのデータ取得）・ニュース収集・AI ベースのニュース/市場判定・ファクター計算・監査ログなどを提供します。

---

## 概要

KabuSys は以下の目的を持つ Python モジュール群です。

- J-Quants API からの株価/財務/カレンダーの差分取得と DuckDB への冪等保存（ETL）
- RSS ニュース収集と前処理、銘柄紐付け
- OpenAI を用いたニュースのセンチメント（ai_score）算出と市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ）および研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定の監査ログ用スキーマ生成（DuckDB）

設計上の特徴：
- Look-ahead bias 対策（現在時刻を安易に参照しない等）
- API リトライ・バックオフ・レートリミット対応
- 冪等保存（ON CONFLICT を利用）
- DuckDB を中心とした軽量かつ高速なローカルデータ保存

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save 各種関数, トークン自動リフレッシュ、レート制御）
  - ニュース収集（RSS の取得・正規化・SSRF 保護）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（missing, spike, duplicates, date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 共通統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で取得して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 とマクロニュースの LLMセンチメントで市場レジーム判定
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン / IC 計算 / ファクターサマリなど
- config
  - 環境変数読み込み (.env / .env.local 優先度) と settings オブジェクトでアクセス可能

---

## 動作環境 / 前提

- Python 3.10 以上（型表記に | を使用）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants API、OpenAI API の利用には各サービスの API キー/トークンが必要

（実際の requirements.txt / setup.py はプロジェクトに依存します。上記パッケージは主要な依存です。）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュールを使う際に必要）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視等に使う SQLite パス（デフォルト: data/monitoring.db）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
   - PID_FILE_PATH, KILL_FLAG_PATH 等：監視・実行制御用

   .env の書式はシェル風（export 対応、クォート対応、コメント行許容）です。

---

## 使い方（簡単なコード例）

- settings による設定取得

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

- DuckDB 接続して日次 ETL を走らせる

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None なら環境変数 OPENAI_API_KEY を使用
print(f"written: {n_written}")
```

- 市場レジームスコア生成

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB の初期化（監査用に専用 DB を作成）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルへアクセス
```

---

## .env の例（参考）

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

※ .env.example がプロジェクトに含まれている想定のメッセージがコード中にあります（未作成の場合はリポジトリに合わせて作成してください）。

---

## よく使う API（抜粋）

- kabusys.config.settings — 環境設定オブジェクト
- kabusys.data.pipeline.run_daily_etl — 一括 ETL 実行（カレンダー → 株価 → 財務 → 品質チェック）
- kabusys.data.jquants_client.* — fetch_ / save_ 系関数（J-Quants 連携）
- kabusys.data.news_collector.fetch_rss — RSS 取得処理（SSRF 対策・前処理あり）
- kabusys.ai.news_nlp.score_news — ニュースセンチメント解析 & ai_scores への保存
- kabusys.ai.regime_detector.score_regime — 市場レジーム（bull/neutral/bear）判定
- kabusys.research.* — ファクター計算・IC・統計解析ユーティリティ
- kabusys.data.audit.init_audit_schema / init_audit_db — 監査ログテーブル初期化

---

## ディレクトリ構成（主要ファイル）

下記は src/kabusys 配下の主要モジュール構成（抜粋）です。

- src/
  - kabusys/
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
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - audit.py
      - etl.py
      - etc...
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/    (監視・実行管理モジュール等: パッケージ化されている想定)
    - strategy/      (戦略・シグナル生成モジュール: 別途実装)
    - execution/     (発注実行・ブローカー連携: 別途実装)

（リポジトリによっては追加ファイルやサブパッケージがあります。ここに挙がっていないユーティリティはプロジェクト内を参照してください。）

---

## 運用上の注意 / 設計上のポイント

- OpenAI / J-Quants の API キーは適切に管理し、不要な公開を避けること。
- AI 呼び出しはレートやコストを伴うためバッチ化やキャッシュを検討してください。
- run_daily_etl は各ステップで独立してエラーハンドリングされ、可能な限り続行します。結果は ETLResult で確認してください。
- DuckDB のバージョン差により executemany の挙動や配列バインドに差が出るため、コード内で回避されています（互換性に配慮済み）。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時に自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## サポート / 貢献

- バグ報告や改善提案は Issue を立ててください。
- コントリビュートの際はテスト / 型チェック / ドキュメントの更新をお願いします。

---

README はここまでです。必要なら、使用例（スクリプト / CLI）の追加、より詳細な環境変数リスト、推奨インストール方法（pip packaging）などを追記します。どの部分を詳しく書きたいか教えてください。