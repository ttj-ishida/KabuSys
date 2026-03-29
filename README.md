# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。データ取り込み（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（注文 → 約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株投資のためのバックエンド基盤ライブラリで、主に以下の領域をカバーします。

- データ取得 / ETL（J-Quants API 経由）
- DuckDB を使った永続化と品質チェック
- RSS ベースのニュース収集と前処理（SSRF・Gzip・トラッキング除去対策あり）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別）およびマクロセンチメントを組み合わせた市場レジーム判定
- 研究用ユーティリティ（ファクター計算、フォワードリターン、IC 計算、Z スコア正規化 等）
- 監査ログ（signal → order_request → execution）スキーマの初期化ユーティリティ
- 設定管理（.env/環境変数自動ロード、必須値チェック）

設計上の重要ポイント:
- ルックアヘッドバイアス回避（内部で datetime.today() を不用意に参照しない）
- フェイルセーフ：外部 API 失敗時も可能な範囲で処理継続
- 冪等性：DB 保存は ON CONFLICT を活用
- テストしやすさ：API 呼び出し等は差し替え可能に実装

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数、トークン自動リフレッシュ、レートリミット管理）
  - market calendar 管理（営業日判定、next/prev/get_trading_days）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - news_collector: RSS 収集と前処理、SSRF 対策
  - audit: 監査ログスキーマ作成（signal_events / order_requests / executions）
  - stats: zscore 正規化などの統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF 1321 の MA 乖離とマクロニュースを合成して market_regime を書き込む
- research/
  - factor 計算（momentum / volatility / value）
  - feature_exploration（forward returns / IC / rank / summary）
- config
  - 環境変数自動ロード（プロジェクトルートの .env / .env.local）と Settings API
- monitoring / execution / strategy（パッケージ公開用のためエクスポートあり）

---

## 必要条件（推奨）

- Python 3.9+（typing 記述や型注釈に準拠）
- DuckDB
- OpenAI Python SDK（openai）
- defusedxml
- その他標準ライブラリ（urllib 等）

最低限インストール例（pip）:
```
pip install duckdb openai defusedxml
```
（プロジェクトに setup.py / pyproject.toml があれば `pip install -e .` を推奨）

---

## 環境変数 / .env

config.Settings から参照される主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（使用箇所がある場合）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

OpenAI:
- OPENAI_API_KEY — ai.score_news / regime_detector の既定 API キー（関数呼び出し時に api_key 引数で上書き可能）

オプション / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動ロードを無効化
- KABUSYS_DISABLE_AUTO_ENV_LOAD をテストで利用可能

データベースパス:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）

.env の自動ロード:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。

---

## セットアップ手順（例）

1. リポジトリをクローン / 配布パッケージを展開
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   # または最低限
   pip install duckdb openai defusedxml
   ```
4. 環境変数を設定
   - プロジェクトルートに .env を作成（.env.example を参照）
   - 必須キー（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY など）を設定
5. データベース格納先ディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```
6. （任意）監査 DB を初期化
   Python REPL / スクリプトで:
   ```python
   import kabusys.data.audit as audit
   conn = audit.init_audit_db("data/audit.duckdb")
   # これで signal_events, order_requests, executions テーブル等が作成されます
   ```

---

## 使い方（主要な例）

以下は最小限の実行例です。各関数は duckdb 接続を受け取るので、既存の DB を使うか新規に接続してください。

1) 日次 ETL（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- J-Quants API へのアクセスには settings.jquants_refresh_token が必要です。
- run_daily_etl はカレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック の順で実行します。

2) ニュースセンチメントを計算して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print("written", n_written)
```

3) 市場レジーム判定（market_regime に書き込む）
```python
from kabusys.ai.regime_detector import score_regime
# conn: DuckDB 接続, target_date: date オブジェクト
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
```

4) 監査スキーマ初期化（別 DB に監査専用を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # transactional=True による安全な初期化も可能
```

5) 研究用ユーティリティ（例: モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
# records は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

注意:
- OpenAI 呼び出しは API 制限・料金が発生します。テスト時は該当 API 呼び出し関数をモックできます（コード内で差し替え可能に設計されています）。
- 日付やウィンドウ計算はルックアヘッドバイアス対策で厳格に実装されています。target_date の扱いに注意してください。

---

## ディレクトリ構成

主要なファイル / モジュール（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — 銘柄別ニュースセンチメント
    - regime_detector.py            — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save 等）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL の公開インタフェース
    - news_collector.py             — RSS 収集・前処理
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - quality.py                    — データ品質チェック
    - stats.py                      — 共通統計ユーティリティ（zscore）
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value
    - feature_exploration.py        — forward returns / IC / rank / summary
  - research/ (他ファイル)
  - (その他) strategy/, execution/, monitoring/（パッケージ参照用あり）

この README に記載の機能はコードコメント・ドキュメント文字列に基づいており、より詳細な設計ドキュメント（DataPlatform.md / StrategyModel.md 等）が別途存在することを想定しています。

---

## 開発・テスト時のヒント

- 自動 .env ロードを無効にする:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
  テスト時に外部環境変数の影響を避けたい場合に有用です。

- OpenAI / ネットワーク呼び出しは差し替え可能:
  - テスト時は kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api をモックして deterministic な挙動を得られます。
  - J-Quants 呼び出しは kabusys.data.jquants_client._request をモックすることで API を模擬できます。

- DuckDB: executemany に空リストを渡すとエラーになるバージョンがあるため、コードでは空チェックが入っています。テストでも同様の注意を。

---

## ライセンス / 貢献

（ここにライセンスや貢献方法を追記してください）

---

もし README に追加したい具体的な利用シナリオ（CI パイプラインでの ETL スケジューリング例、Slack 通知フロー、kabu ステーション連携方法など）があれば教えてください。必要に応じてサンプル .env.example や CLI ラッパーの README を追記します。