# KabuSys — 日本株自動売買システム

KabuSys は日本株のデータ収集・ETL・特徴量生成・ニュースNLP・市場レジーム判定・監査ログなどを含む自動売買／リサーチ基盤のコアライブラリです。DuckDB を中心にデータプラットフォームを構築し、J-Quants / OpenAI / kabu ステーション等と連携する処理を提供します。

主な用途：
- 日次 ETL（株価・財務・市場カレンダー）の差分取得と品質チェック
- ニュースを用いた銘柄ごとの NLP スコアリング（OpenAI）
- 市場レジーム判定（ETF 指標 + マクロニュース）
- ファクター計算・特徴量探索（リサーチ用ユーティリティ）
- 取引フローの監査ログ（監査テーブル初期化・管理）

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得 / 保存 / ページネーション / リトライ / レート制御）
  - 市場カレンダー管理（営業日判定・次営業日/前営業日取得・夜間更新ジョブ）
  - ニュース収集（RSS 取得・前処理・SSRF 対策・冪等保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログテーブル初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：銘柄ごとのセンチメントスコアを ai_scores に保存）
  - 市場レジーム判定（score_regime：ETF MA とマクロニュースを合成）
  - OpenAI 呼び出しはリトライ・例外ハンドリング・JSON 検証付き
- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリー

主な設計方針：
- ルックアヘッドバイアス回避（内部で date.today() を直接参照しない設計、ターゲット日指定方式）
- DuckDB による SQL + Python のハイブリッド実装
- 冪等保存（ON CONFLICT / UPSERT）と堅牢なエラーハンドリング
- OpenAI / J-Quants / ネットワーク呼び出しに対するリトライ・バックオフ実装
- セキュリティ配慮（RSS の SSRF 対策、XML パースの安全化など）

---

## セットアップ手順

前提：
- Python 3.10+（typings の union 型等を使用）
- Git（開発時）
- ネットワーク接続（J-Quants / OpenAI など）

1. リポジトリをクローン（開発中であれば）
   - git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject がある場合はそちらを使ってください）

   主要依存（例）：
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外の軽量なユーティリティは上記の通り）

4. パッケージをインストール（編集可能な開発インストール）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

重要な環境変数（一例）：
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視関連設定
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（ライブラリ利用例）

以下は Python REPL / スクリプトからの利用例です。

- DuckDB 接続を開いて日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアを生成する（OpenAI API キーが環境にあること）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("書き込んだ銘柄数:", written)
```

- 市場レジームスコアを計算して保存する
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # :memory: も指定可
# conn は監査テーブルが作成された DuckDB 接続
```

- J-Quants の生データを手動でフェッチして保存する
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

# 例: 日足取得
records = jq.fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
jq.save_daily_quotes(conn, records)
```

注意点：
- OpenAI 呼び出し（score_news / score_regime）は API キーが必要。api_key 引数で直接渡すか、環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl 等は内部でトランザクション管理や品質チェックを行います。エラーはロギングされ、ETLResult に集約されます。
- ルックアヘッドバイアス対策として target_date を明示的に渡す設計です。自動で現在日を参照するケースは最小限に留めています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なモジュール構成は以下の通りです（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLU / スコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      — RSS ニュース収集・前処理
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログ（テーブル定義・初期化）
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

付帯ファイル（プロジェクトルート想定）
- .env, .env.local（環境変数）
- pyproject.toml / setup.cfg / requirements.txt（依存管理、存在する場合）

---

## 運用上の注意 / トラブルシューティング

- 環境変数が不足している場合、settings の該当プロパティは ValueError を投げます（必須項目: JQUANTS_REFRESH_TOKEN など）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト等で無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB への大量インサートは executemany を使用していますが、DuckDB のバージョン差異に起因する制約（空リストを渡せない等）をコード側で考慮しています。
- OpenAI や J-Quants の API 呼び出しはリトライやバックオフを備えていますが、API キーのレート制限や課金ポリシーには注意してください。
- RSS 取得では SSRF / XML 脆弱性対策（ホスト検査・defusedxml・リダイレクト検査等）を実施していますが、追加の信頼性／監視を推奨します。

---

## 貢献 / 開発

- コードスタイル・型注釈を整え、ユニットテストを追加することで品質を向上できます。
- OpenAI 呼び出し部分はテスト時にモック可能な設計になっています（内部の _call_openai_api を patch）。
- ETL のジョブスケジューリング（cron / airflow / Kubernetes CronJob 等）による運用を想定しています。

---

必要であれば、README に含めるサンプル .env.example、より詳細な API 使用例、あるいは簡単な CLI 起動スクリプトのテンプレートも作成できます。どの追加情報が欲しいか教えてください。