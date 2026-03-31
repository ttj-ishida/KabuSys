# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ向けファクター計算、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買プラットフォームおよび研究用途のための共通ライブラリ集です。主な設計方針は以下です。

- Look-ahead バイアスを避ける（内部で date.today() を安易に参照しない）
- DuckDB を中心としたローカルデータベース運用（ETL / 監査ログ / 解析）
- J-Quants API 経由のデータ取得（差分取得、ページネーション、トークン自動リフレッシュ、レート制御）
- OpenAI（gpt-4o-mini など）を用いたニュースセンチメント評価（JSON Mode を利用）
- 冪等性を保った DB 保存（ON CONFLICT / UPDATE 等）
- ニュース収集における SSRF 対策・サイズ制限・XML 防御

---

## 主な機能一覧

- 環境設定管理（.env の自動読み込み / Settings）
- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）
  - 財務データ（四半期）
  - JPX カレンダー
- ETL パイプライン（差分取得、保存、品質チェック）
- ニュース収集（RSS → raw_news）
- ニュース NLP（OpenAI を用いた銘柄別センチメント scoring）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
- リサーチ用モジュール（モメンタム・バリュー・ボラティリティなどのファクター計算）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions テーブル、監査 DB 初期化ユーティリティ）
- 各種ユーティリティ（統計正規化、カレンダー管理等）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `X | Y` 表記を使用）
- Git（任意）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 代表的な依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは requirements.txt や pyproject.toml に依存が記載されている想定です。

4. パッケージを開発モードでインストール（任意）
   - プロジェクトルートに pyproject.toml / setup.cfg 等がある場合:
     - pip install -e .

5. 環境変数 / .env を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると無効化可能）。
   - 必須となる環境変数例（用途とともに）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注等）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知用
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
     - DUCKDB_PATH / SQLITE_PATH — データベースパス（オプション）
     - KABUSYS_ENV — development / paper_trading / live
     - LOG_LEVEL — DEBUG/INFO/...

   例 `.env`（実運用では機密情報は Git に含めないでください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

---

## 使い方（主要な例）

以下はライブラリの主要機能を使う際の最小例です。詳細なパラメータは各関数の docstring を参照してください。

1) DuckDB 接続を用意する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する（カレンダー/株価/財務/品質チェックを順に実行）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（銘柄別）をスコアリングする
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI の API キーは環境変数 OPENAI_API_KEY で指定するか、api_key 引数で渡す
n_written = score_news(conn, date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

4) 市場レジーム判定を行う
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, date(2026, 3, 20))  # OpenAI API キーは env または api_key 引数
```

5) 監査ログデータベースを初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/monitoring_audit.duckdb")
# これで signal_events, order_requests, executions テーブル等が作成されます
```

6) カレンダー関連ユーティリティ（営業日判定等）
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print("is_trading_day:", is_trading_day(conn, d))
print("next_trading_day:", next_trading_day(conn, d))
```

---

## 環境変数 / 設定（summary）

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml を検出）から `.env`、続けて `.env.local` を読み込みます。
  - OS 環境変数が優先され、.env.local は override=True で上書き可能。ただし既に OS にあるキーは protected されます。
  - 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 主な必須環境変数（実行する機能により変わります）
  - JQUANTS_REFRESH_TOKEN
  - OPENAI_API_KEY（news_nlp / regime_detector）
  - KABU_API_PASSWORD（kabuステーション連携）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB 等、デフォルト: data/monitoring.db）
  - KABUSYS_ENV（development / paper_trading / live）
  - LOG_LEVEL（DEBUG/INFO/...）

---

## セキュリティ / 運用上の注意

- 秘密情報（トークン / パスワード）は .env に置いても Git にコミットしないこと。運用ではシークレット管理（Vault 等）を推奨します。
- OpenAI の呼び出しは課金が発生します。大量バッチ処理時のレートやコストに注意してください。
- J-Quants API にはレート制限があるため、ETL は RateLimiter で制御しています。API の利用規約を遵守してください。
- ニュース収集では SSRF や XML 攻撃対策を実装していますが、追加の想定外入力に対する監視を行ってください。

---

## ディレクトリ構成（主要ファイル）

（パスは `src/kabusys/` 以下）

- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / Settings 管理（.env 自動ロード含む）

- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（OpenAI）: score_news, calc_news_window など
  - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save 系）
  - pipeline.py — ETL パイプラインと run_daily_etl 等
  - etl.py — ETLResult の再エクスポート
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management.py — 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - news_collector.py — RSS ニュース収集と前処理
  - audit.py — 監査ログ（テーブル定義、init_audit_db 等）

- research/
  - __init__.py
  - factor_research.py — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

---

## 開発・テスト

- モジュール内の多くの外部呼び出し（OpenAI, J-Quants, ネットワーク）についてはユニットテスト時にモック可能に設計されています（例: _call_openai_api や _urlopen の差し替え）。
- CI では外部 API を直接叩かないようにモックを使用してください。

---

もし README に追記したい具体的な実行コマンド、Docker / systemd ユニット、CI 設定、あるいはより詳細な API 使用例（kabuステーション連携、Slack 通知の実装など）があれば教えてください。その内容に合わせて README を拡張します。