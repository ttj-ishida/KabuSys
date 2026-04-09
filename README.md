# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
DuckDB を用いたデータプラットフォーム、J-Quants からの ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注 / 約定トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針は「バックテストや運用におけるルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗時の安全な挙動）」「外部副作用を極力分離」です。

バージョン: 0.1.0

---

## 主要機能一覧

- データ収集 / ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル・ページネーション・レートリミット・トークン自動リフレッシュ対応
- データ品質チェック
  - 欠損、重複、将来日付、株価スパイク検出などのチェックを収集して報告
- ニュース収集・前処理
  - RSS 取得（SSRF防止・URL正規化・トラッキングパラメータ除去）
  - raw_news / news_symbols との紐付けと冪等保存
- ニュース NLP（OpenAI）
  - gpt-4o-mini を使った銘柄単位のセンチメントスコア算出（ai_scores へ保存）
  - チャンク化、リトライ、レスポンス検証、結果クリッピング
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離 + マクロニュースの LLM センチメントを合成して日次レジーム（bull/neutral/bear）を出力
- リサーチ用ユーティリティ
  - モメンタム / バリュー / ボラティリティなどファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルを提供し、発注から約定までを UUID で追跡可能にする初期化ユーティリティ
- 設定管理
  - .env（プロジェクトルート）および環境変数から設定を自動読み込み（オプトアウト可能）

---

## 必要条件（概略）

- Python 3.10 以上（typing における `|` を使用）
- 外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）
- J-Quants リフレッシュトークン、OpenAI API キー 等の環境変数（下記参照）

実際のプロジェクトでは requirements.txt / pyproject.toml を用意して依存管理してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
   - パッケージは src/ 配下に配置されていることを想定しています。

2. 仮想環境の作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトで pyproject.toml / requirements.txt があればそれを使う）

4. 開発用に editable インストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（読み込みは config.py のロジックに従う）。
   - 自動読み込みを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

例: .env（必要なキーと説明）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション（運用時）
KABU_API_PASSWORD=...

# OpenAI（news scoring / regime detector）
OPENAI_API_KEY=sk-...

# 環境設定
KABUSYS_ENV=development           # development | paper_trading | live
LOG_LEVEL=INFO

# DB パス（デフォルト）
DUCKDB_PATH=data/kabusys.duckdb
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
SQLITE_PATH=data/monitoring.db

# Paper trading の挙動（instant/partial/never/reject）
PAPER_FILL_MODE=instant
```

---

## 使い方（主要な例）

下記はライブラリをプログラムから呼び出す基本例です。必要に応じてログ設定や例外処理を行ってください。

- DuckDB 接続を作って日次 ETL を実行する例
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# デフォルトの duckdb ファイルは settings.duckdb_path
conn = duckdb.connect("data/kabusys.duckdb")

# 今日の ETL（target_date を指定して任意の日の ETL を走らせることも可能）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが env にあるか api_key を渡す）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db

# file path: ":memory:" も可
conn_audit = init_audit_db("data/audit.duckdb")
```

- カレンダー更新バッチ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("保存レコード数:", saved)
```

注意:
- OpenAI 呼び出しは API 料金が発生します。テスト時はモック（unittest.mock.patch）で _call_openai_api を差し替え可能です（各モジュールがその使い方を想定）。
- DuckDB に対する executemany やトランザクションはコード内に互換性対応が含まれています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用のリフレッシュトークン。config.Settings.jquants_refresh_token が参照します。
- KABU_API_PASSWORD (必須 in 実運用)
  - kabuステーション API のパスワード。
- OPENAI_API_KEY（news / regime 用）
  - OpenAI API キー。score_news / score_regime は引数で渡すこともできます。
- KABUSYS_ENV
  - 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL
  - ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 SQLite、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper trading DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper trading の約定挙動: instant|partial|never|reject)

自動読み込みの順序: OS 環境 > .env.local > .env。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下にモジュールが配置されています。主要構成:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py       — 市場カレンダー管理
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL 型の再エクスポート
    - jquants_client.py            — J-Quants API クライアント（取得 & 保存）
    - news_collector.py            — RSS ベースのニュース収集（SSRF 対策等）
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore 等）
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Value/Volatility 等の計算
    - feature_exploration.py       — forward returns / IC / summary / rank
  - ai/, data/, research/ などのテストや補助モジュールは各ディレクトリに配置

上記以外に実運用用のスクリプト（起動スクリプト等）や設定ファイルをプロジェクトルートに置くことを推奨します。

---

## 注意点 / 運用上のヒント

- ルックアヘッドバイアス対策:
  - 多くの関数は内部で date.today() 等を直接参照せず、target_date 引数に基づいて動作します。バックテスト時は必ず target_date を明示してください。
- 冪等性:
  - ETL・保存関数は可能な限り ON CONFLICT を使って冪等に保存します。
- フェイルセーフ:
  - OpenAI 等 API 呼び出しが失敗した場合はスコアを 0 にフォールバックする等の安全策が入っています（例外を上位に伝えない実装箇所あり）。ただしログや結果を監視して異常を検知してください。
- テスト:
  - OpenAI 呼び出しやネットワーク周りはモック可能（モジュール内の _call_openai_api や _urlopen 等を patch して差し替え可能）。
- セキュリティ:
  - news_collector は SSRF 対策や XML パーサの安全実装（defusedxml）を行っていますが、RSS ソースの管理やネットワーク制御は運用側で行ってください。

---

## ライセンス / 貢献

（ここにライセンス情報やコントリビューションポリシーを記載してください）

---

この README はコードベースに含まれるモジュールの意図・主要な使い方・セットアップを簡潔にまとめたものです。詳細な API 仕様や運用手順、pyproject.toml / requirements.txt、CI 構成等はプロジェクトに合わせて補完してください。必要であれば各モジュールの関数一覧と引数説明を別ドキュメントとして展開できます。