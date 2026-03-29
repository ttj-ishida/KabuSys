# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants API を用いたデータ ETL、DuckDB ベースのデータ管理、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター計算・リサーチ、監査ログ（注文→約定のトレーサビリティ）などを含むモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ収集 / ETL
  - J-Quants API クライアント（株価日足 / 財務 / JPX カレンダー）
  - 差分取得（バックフィル対応）、ページネーション、トークン自動リフレッシュ、レート制御、リトライ
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集 / 前処理
  - RSS フィードの取得と安全対策（SSRF 防止、gzip 上限、XML 危険対策）
  - 記事正規化・重複防止（URL 正規化 → SHA256 による記事 ID）

- ニュース NLP / AI
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュースと ETF（1321）の MA より市場レジーム判定（score_regime）
  - API 呼び出しに対するリトライ / フォールバック設計

- データ品質チェック
  - 欠損、重複、スパイク（急騰/急落）、日付不整合の検出
  - QualityIssue を集めて ETL 後に検査可能

- 研究（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ

- カレンダー管理
  - JPX マーケットカレンダー管理、営業日判定、next/prev trading day 等

- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブル初期化ユーティリティ
  - 監査用 DuckDB データベース初期化（UTC タイムゾーン固定）

- 設定管理
  - 環境変数（.env / .env.local の自動読み込み、無効化フラグあり）
  - 必須設定を Settings オブジェクト経由で取得

---

## セットアップ手順

※ 以下は一般的な手順例です。実行環境や要件に合わせて調整してください。

1. リポジトリをクローン
   - git clone <your-repo-url>
   - cd <repo>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必須パッケージをインストール
   - 必要パッケージ（コードベースから推定）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml

   - （プロジェクト配布用に setup.cfg / pyproject.toml があれば）：
     pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（注文実行などを行う場合）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（通知機能利用時）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）

   その他（デフォルト値あり）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用等）パス（デフォルト: data/monitoring.db）

---

## 使い方（簡単なコード例）

- 共通: Settings を使って設定を取得できます。

例: DuckDB 接続を作って日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（ファイルは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメントのスコア付け（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み件数: {n_written}")
```

市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("成功" if res == 1 else "失敗")
```

監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
```

注意事項・設計方針（要点）
- すべてのバックテスト用関数は「ルックアヘッドバイアス」を避ける設計（date.today() 等に依存しない）。
- OpenAI 呼び出しはリトライやフォールバック（失敗時 0.0）を行うため、API エラーでプロセスが一気に停止しにくい設計。
- DuckDB での executemany に対する互換性処理（空リスト回避等）が組み込まれている。

---

## ディレクトリ構成（概要）

プロジェクトの主要ファイル/モジュール（src/kabusys 内）

- __init__.py
  - パッケージのバージョンと公開 API 指定

- config.py
  - 環境変数・設定読み込みロジック（.env 自動読み込み、Settings）

- ai/
  - news_nlp.py         — ニュースを銘柄別に集約して OpenAI でセンチメント解析（score_news）
  - regime_detector.py  — ETF MA とマクロニュースを合成して市場レジーム判定（score_regime）

- data/
  - jquants_client.py       — J-Quants API クライアント（取得 + DuckDB 保存関数）
  - pipeline.py             — 日次 ETL のオーケストレーション（run_daily_etl 等）
  - etl.py                  — ETLResult のエクスポート
  - news_collector.py       — RSS 取得・前処理・raw_news への保存ロジック
  - calendar_management.py  — 市場カレンダー管理・営業日判定
  - quality.py              — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py                — Zスコア正規化等の統計ユーティリティ
  - audit.py                — 監査ログスキーマ初期化（signal_events / order_requests / executions）

- research/
  - factor_research.py      — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py  — 将来リターン計算、IC、統計サマリ、ランク関数
  - __init__.py             — research API の再エクスポート

- monitoring / execution / strategy 等（パッケージ全体のエントリや実行系は将来追加）

（上記は主要ファイルの抜粋です。詳細はソースコードを参照してください。）

---

## テストやモックに関するメモ

- OpenAI への実呼び出しをテストで差し替えるため、news_nlp と regime_detector の内部で _call_openai_api を patch/mocking することが想定されています（unittest.mock.patch を使用）。
- 自動環境変数読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストや CI で .env の読み込みを抑制するときに有用）。

---

## 参考・運用上の注意

- 本リポジトリは実売買を想定した設計要素（kabu API パスワードや監査ログ等）を含みます。実際に「live」環境で稼働させる場合は十分なテストとリスク管理を行ってください。
- OpenAI / J-Quants の API 利用料金や利用制限にご注意ください。
- DuckDB のファイルパスは Settings.duckdb_path で管理されます。バックアップや運用フローを設計してください。

---

README に書いてほしい追加項目（例、運用手順・SQL スキーマ・CI 設定など）があれば教えてください。必要に応じてサンプル .env.example の雛形や、よく使う CLI ラッパー（スクリプト例）も作成します。