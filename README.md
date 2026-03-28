# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群 (KabuSys)

このリポジトリは、日本株のデータ収集（J-Quants）、ニュース収集・NLP（OpenAI）、特徴量計算、ETL、監査ログ、マーケットカレンダー管理などを提供するモジュール群です。DuckDB をデータ層に用い、バックテストや実運用向けの前処理・品質管理を目的に設計されています。

主な設計方針
- Look‑ahead バイアスを避ける（内部処理で date.today() 等の参照を限定）
- DuckDB ベースで冪等的なデータ保存（ON CONFLICT 系）
- 外部 API 呼び出しはリトライ・レートリミット・フェイルセーフを実装
- モジュール毎にテストしやすく分離（DB 接続注入、API キー注入可能）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートを探索）
  - 必須変数の取得（Settings オブジェクト経由）
- データ取得 (J-Quants)
  - 日足（OHLCV）取得・保存（ページネーション、トークン自動リフレッシュ）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 保存時に冪等性を保つ save_* 関数
- ETL パイプライン
  - 差分取得（最終取得日からの再取得 / backfill）
  - run_daily_etl による一括処理（カレンダー→日足→財務→品質チェック）
  - ETL 結果を ETLResult で集約
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複・日付不整合検出
  - QualityIssue で結果を返却
- ニュース収集 / NLP
  - RSS 収集（SSRF 対策、トラッキング除去、gzip 対応）
  - raw_news → 銘柄紐付け → ai_scores へ LLM によるセンチメント書き込み
  - OpenAI（gpt-4o-mini）を用いたバッチ評価（JSON Mode）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA とマクロニュース LLM スコアを合成してレジーム判定（bull/neutral/bear）
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - init_audit_db による監査 DB 初期化（UTC タイムスタンプ管理）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、Z-score 正規化 等

---

## セットアップ手順

前提
- Python 3.10+（コードが型 hint の `|` を使用）
- DuckDB が使える環境（pip install duckdb）
- OpenAI ライブラリ（OpenAI SDK）を使用するため API キーが必要
- ネットワークアクセス（J-Quants / RSS / OpenAI）

推奨パッケージ（最低限）
- duckdb
- openai
- defusedxml

例: 仮想環境作成とインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# （プロジェクトに requirements.txt がある場合はそれを使う）
# pip install -r requirements.txt
```

環境変数 / .env
プロジェクトルートに `.env`（および必要に応じて `.env.local`）を置くと、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot Token（必須）
- SLACK_CHANNEL_ID: Slack Channel ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（検証用フラグ）
- LOG_LEVEL: DEBUG|INFO|...（ログレベル）

注意: .env の読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います。

---

## 使い方（簡易例）

以下は主要なユースケースのサンプルコードです。実行は Python スクリプト内で行います。

DuckDB 接続の作成
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイルがなければ作成されます
```

ETL（日次パイプライン）の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニューススコアリング（OpenAI が必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"scored {count} codes")
```

市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

監査DBの初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn をアプリケーションの監査ログ書き込みに使用
```

J-Quants データ取得（直接呼び出し例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
print(len(records))
```

設定値の取得（コード内で）
```python
from kabusys.config import settings
print(settings.duckdb_path)        # Path オブジェクト
print(settings.is_live)            # boolean
```

ログ設定やエラーハンドリングは実運用時に適切に設定してください（LOG_LEVEL 環境変数参照）。

---

## ディレクトリ構成（主要ファイル / モジュール一覧）

src/kabusys/
- __init__.py
  - パッケージのバージョン/公開モジュール定義
- config.py
  - 環境変数・.env 自動読み込み・Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM 評価（score_news）
  - regime_detector.py — ETF 200日MA とマクロニュースを合成して市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 / 保存 / トークン管理 / レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理・raw_news への保存
  - calendar_management.py — 市場カレンダーの管理・営業日判定・更新ジョブ
  - audit.py — 監査ログスキーマ定義と初期化ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 共通統計ユーティリティ（zscore_normalize など）
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン・IC・rank・summary 等
- ai/__init__.py, research/__init__.py などで主要関数をエクスポート

その他
- data/ 以下に DuckDB ファイルや SQLite ファイルを保存することが想定されています（デフォルトは data/kabusys.duckdb, data/monitoring.db）。

---

## 注意事項 / 運用上のポイント

- OpenAI の呼び出しにはコストとレート制限があるため、バッチ単位の呼び出しやリトライ制御が実装されています。APIキーは環境変数か引数で安全に注入してください。
- J-Quants API はレート制限（120 req/min）を守るため内部でスロットリングを行います。長時間の全銘柄取得は時間がかかる点に注意してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。CIやテストで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany や SQL の互換性はバージョン差で振る舞いが変わる場合があります（コード内に互換性対策あり）。
- 監査スキーマは削除しない前提で設計されています。初期化時は transactional オプションの扱いに注意してください（DuckDB はネストトランザクションに制約あり）。

---

必要であれば README に利用例のより詳細なスクリプトや .env.example のサンプル、CI の設定手順（テスト・フォーマット）などを追加します。どの情報を優先的に追加したいか教えてください。