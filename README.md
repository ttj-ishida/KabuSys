# KabuSys

バージョン: 0.1.0

日本株向けのデータ基盤・リサーチ・AI支援・監査ログを備えた自動売買（研究）ライブラリです。DuckDB をデータ層に用い、J-Quants / OpenAI / RSS 等を連携してデータ取得・品質チェック・ファクター計算・ニュースセンチメント評価・市場レジーム判定・監査ログ初期化などの機能を提供します。

---

## 主要コンセプト / プロジェクト概要

- データ取得（J-Quants）→ ETL → 品質チェック → 研究・特徴量計算 → 戦略（別途実装）という分離されたレイヤー設計。
- DuckDB を主要な永続ストアに利用（インメモリも可）。監査ログ用 DB の初期化ユーティリティあり。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別 & マクロ）や、市場レジーム判定を提供。
- セキュリティ面に配慮（RSS の SSRF/リダイレクト検査、J-Quants のレート制御・トークンリフレッシュ、API リトライ等）。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local からの自動ロード（OS 環境変数優先）。自動ロード無効化フラグあり。
  - Settings クラス経由で設定値（J-Quants トークン、kabu API、DB パスなど）を取得。

- Data（kabusys.data）
  - jquants_client：J-Quants API の取得＋DuckDB への冪等保存（株価・財務・カレンダー・上場情報）。
  - pipeline / etl：差分 ETL（prices / financials / calendar）と日次パイプライン run_daily_etl。
  - quality：欠損・スパイク・重複・日付不整合などのデータ品質チェック。
  - news_collector：RSS からのニュース収集（SSRF 対策、前処理、冪等保存）。
  - calendar_management：JPX カレンダー管理と営業日判定ユーティリティ。
  - audit：監査ログ（signal / order_request / executions）用テーブルの初期化ユーティリティ。
  - stats：共通統計ユーティリティ（zscore 正規化 など）。

- Research（kabusys.research）
  - factor_research：モメンタム / ボラティリティ / バリュー等のファクター計算。
  - feature_exploration：将来リターン計算、IC（スピアマン）計算、統計サマリー、ランク変換など。

- AI（kabusys.ai）
  - news_nlp.score_news：銘柄別ニュースセンチメントを計算し ai_scores に格納。
  - regime_detector.score_regime：ETF（1321）MA200 乖離とマクロニュースセンチメントを合成して市場レジーム判定。

---

## セットアップ手順

推奨: Python 3.9+（ソースは型注釈でモダン機能を利用）

1. リポジトリをクローン / コピー

2. 仮想環境を作成・有効化（任意）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

3. 必要パッケージをインストール（代表例）
   - pip install duckdb openai defusedxml

   実環境では logging 設定や追加の HTTP / DB ドライバが必要になる場合があります。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的にロードされます（既定の優先順位: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主な環境変数（Settings により参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で未指定時に使用）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - DUCKDB_PATH: DuckDB のパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（monitoring 用）のパス（デフォルト data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH など（監視用）

   サンプル .env（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=your_openai_api_key
   - KABU_API_PASSWORD=your_kabu_password
   - DUCKDB_PATH=data/kabusys.duckdb
   - KABUSYS_ENV=development

---

## 使い方（代表的な API）

以下は Python スクリプト / REPL からの利用例です。

- DuckDB 接続の作成例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # または ":memory:"
```

- ETL（日次パイプライン）を実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）を計算して ai_scores に保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を直接渡すことも可能（None の場合は環境変数 OPENAI_API_KEY を参照）
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n} codes")
```

- 市場レジームを評価して market_regime テーブルへ書き込み
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB の初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は自動的に実行され、必要なテーブル/インデックスを作成します
```

- 研究用ファクター計算の例
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code": "...", "mom_1m": ..., ...}, ...]
```

---

## 設定と挙動に関する注意点

- 環境ロード:
  - 自動読み込みの挙動: OS env > .env.local (override) > .env (only set if unset)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化できます。
- KABUSYS_ENV の許容値: development, paper_trading, live。その他は ValueError。
- OpenAI 呼び出し:
  - 内部でリトライ・例外ハンドリングがあるが、API キーが未指定の場合は ValueError。
  - news_nlp / regime_detector は gpt-4o-mini を使用し、JSON モードで厳密な JSON を期待します。
- J-Quants クライアント:
  - rate limit（120 req/min）を守る実装。401 を検知した場合はリフレッシュトークンで自動再取得。
  - save_* 関数は DuckDB へ冪等保存（ON CONFLICT DO UPDATE）する。
- RSS ニュース収集:
  - SSRF 対策・受信サイズ制限・XML の安全パーサ（defusedxml）を使用。
- DuckDB のバージョン差異に関して:
  - 一部 executemany の仕様や配列バインドに対する互換性を考慮した実装になっています（空リストを渡さない等）。

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義
  - ai/
    - __init__.py
    - news_nlp.py         - 銘柄別ニュースセンチメント評価（score_news）
    - regime_detector.py  - マクロ + ETF MA200 を用いた市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   - J-Quants API クライアント & DuckDB 保存ユーティリティ
    - pipeline.py         - ETL パイプライン（run_daily_etl など）、ETLResult
    - etl.py              - ETLResult の再エクスポート
    - quality.py          - 品質チェック
    - news_collector.py   - RSS 収集・前処理
    - calendar_management.py - JPX カレンダー管理・営業日判定
    - stats.py            - zscore_normalize 等の統計ユーティリティ
    - audit.py            - 監査ログテーブルの DDL・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  - momentum/value/volatility 等
    - feature_exploration.py - 将来リターン・IC・統計サマリー等
  - ai/ (上に記載)
  - research/ (上に記載)

---

## 開発・運用上のヒント

- ロギングレベルは Settings.log_level を参照。デバッグ時は LOG_LEVEL=DEBUG を推奨。
- テスト時:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化してください。
  - OpenAI / J-Quants 呼び出し部分はモジュール内の _call_openai_api / _urlopen 等をモックする設計になっています。
- バックテストや研究用途では Look-ahead bias に注意。多くの関数が date 引数を外から注入することで未来情報利用を排除する設計です。

---

## ライセンス / コントリビュート

（この README はコードベースの概要を示すためのものです。実際の配布リポジトリには LICENSE / CONTRIBUTING ガイドを追加してください。）

---

README についての補足や、特定モジュールの詳細なドキュメント（関数引数の説明、SQL スキーマ、例データの導入手順 など）が必要であれば、どの部分を詳しく書くかを指定してください。