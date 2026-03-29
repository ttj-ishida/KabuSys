# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）のリポジトリ内 README です。  
この README はコードベース（src/kabusys）に基づく簡易ドキュメントで、導入・利用方法と各モジュールの概要を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株を対象とした以下の機能を提供する Python ライブラリです。

- J-Quants API からの株価・財務・カレンダー等の ETL（差分取得・保存・品質チェック）
- RSS ベースのニュース収集とニュースの前処理（SSRF 等の安全対策込み）
- OpenAI（gpt-4o-mini）を用いたニュースの NLP スコアリング（銘柄別 ai_score）、およびマクロセンチメントとETF指標を合成した市場レジーム判定
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量探索（将来リターン、IC 等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用 DB 初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）

設計方針としては「ルックアヘッドバイアスの排除」「冪等性」「外部依存の最小化（DuckDB・標準ライブラリ中心）」「フェイルセーフ（API失敗時のデフォルト動作）」を重視しています。

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数の読み込み（.env/.env.local の自動ロード。無効化可）、必須設定の取得（settings）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得/保存/認証/レート制御・リトライ）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 収集・正規化・保存
  - calendar_management: 市場カレンダー管理・営業日判定
  - quality: データ品質チェック
  - audit: 監査テーブルのDDL/初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM で銘柄ごとにスコアリングし ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF(1321) の MA200 乖離と LLM マクロセンチメントを合成して market_regime に書き込み
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈や "X | Y" 構文を使用）
- DuckDB を利用するためネイティブモジュールがインストールされます

1. リポジトリをクローン（例）
   - git clone <repo-url>

2. 仮想環境作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - 必須（例）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml がある場合）pip install -e . または poetry install

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、kabusys.config が自動読み込みします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みは無効化されます）。
   - 最低限必要な環境変数（利用する機能によって必須項目は異なります）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client.get_id_token に使用）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（注文系で使用）
     - SLACK_BOT_TOKEN — Slack 通知に使用
     - SLACK_CHANNEL_ID — Slack チャンネルID
     - OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / score_regime など）。関数呼び出し時に api_key を引き渡すことも可能
   - その他:
     - KABUSYS_ENV: "development" / "paper_trading" / "live"（既定: development）
     - LOG_LEVEL: "DEBUG"/"INFO"/...（既定: INFO）
     - DUCKDB_PATH / SQLITE_PATH: データベースファイルパス（既定値あり）

   例 `.env`（参考）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

以下はライブラリを直接インポートして使う際の簡易例です。実行前に環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等）を設定してください。

1) DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 今日の ETL を実行（内部で market_calendar / prices / financials を差分取得して保存）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの NLP スコアリング（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} scores")
```

3) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査 DB 初期化（監査専用 DuckDB を作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブルとインデックスが作成されます
```

5) RSS フィード取得（news_collector）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- OpenAI 呼び出しには `openai`（または OpenAI の Python SDK）が必要です。score_news / regime_detector は API 失敗時にフェイルセーフ（スコア 0.0 を採用する等）で動作する設計ですが、API キーは必須です（引数で渡すことも可）。
- jquants_client は ID トークンの自動リフレッシュ・レート制御・ページネーション対策を持ちます。J-Quants のトークンは JQUANTS_REFRESH_TOKEN から取得されます。
- テスト時には内部の API 呼び出し関数（例: kabusys.ai.news_nlp._call_openai_api）をモックするように設計されています。

---

## 実装上の挙動・設定の補足

- .env の自動ロード
  - package 初期化時にプロジェクトルート（.git または pyproject.toml の位置）を起点に `.env` と `.env.local` を自動読み込みします。
  - OS 環境変数 > .env.local > .env の順に優先されます。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- KABUSYS_ENV の有効値
  - "development", "paper_trading", "live" のいずれか。settings.is_live / is_paper / is_dev で判定できます。

- ログレベル
  - LOG_LEVEL 環境変数で "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" を指定できます。

- DuckDB の注意点
  - DuckDB に対する executemany の空リストバインドに留意した実装になっています（空リスト時に呼ばれると失敗するバージョン対応）。
  - 日付やタイムスタンプは明確に UTC を扱うよう記述している箇所があります（監査ログ等）。

---

## ディレクトリ構成（抜粋）

（src/kabusys 配下の主要ファイルを示します）

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP（score_news）
    - regime_detector.py                — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（fetch/保存）
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - etl.py                            — ETL の公開型（ETLResult）
    - news_collector.py                 — RSS 収集（fetch_rss 等）
    - calendar_management.py            — 市場カレンダー管理（is_trading_day 等）
    - quality.py                        — データ品質チェック
    - audit.py                          — 監査ログ DDL / 初期化
    - stats.py                          — 汎用統計ユーティリティ（zscore_normalize）
    - pipeline.py (及び ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py                — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py            — 将来リターン/IC/統計サマリー/etc
  - research/...（その他ユーティリティ）
  - その他、execution / monitoring / strategy などのエクスポートプレースホルダ（__all__ に含まれる）

（各ファイルにはモジュールレベルで詳細な docstring が付与されています。実装の意図やフェイルセーフ動作、ルックアヘッドバイアス回避方法なども記載されています）

---

## テスト・開発時のヒント

- OpenAI / HTTP 呼び出し部分はモックしやすいよう関数を分離しています（例: _call_openai_api を patch）。
- news_collector は内部で DNS 解決や socket/getaddrinfo を行うため、ユニットテストでは fetch_rss 内の _urlopen をモックすると扱いやすいです。
- 環境変数の自動ロードを無効にすることでテスト実行時の環境影響を抑えられます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

もし README に追記してほしいサンプルコード（パイプラインの cron 実行例、Dockerfile、CI 設定例、.env.example の具体テンプレ等）があれば、用途に合わせて追加で作成します。