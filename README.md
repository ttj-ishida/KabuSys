# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群（読み取り専用のリサーチ・ETL・NLP・監査ロジックを含む）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、ETL、ニュースの自然言語処理（OpenAI を利用した銘柄センチメント）、市場レジーム判定、監査ログ（発注→約定のトレース）などを提供する内部ライブラリです。バックテストや運用の基盤として、DuckDB ベースのデータレイク・監査 DB、J-Quants クライアント、ニュース収集器、LLM を使った NLP モジュール、ファクター/リサーチ用ユーティリティ等を含みます。

設計上の特徴（抜粋）:
- Look-ahead bias を排除する設計（日時参照の取り扱いに注意）
- DuckDB をデータ保存の中心に使用
- J-Quants API 呼び出しはレート制御・自動リフレッシュ・リトライ実装済み
- OpenAI（gpt-4o-mini 等）を JSON mode で利用し、レスポンス検証・リトライ制御あり
- ETL/保存処理は冪等（ON CONFLICT / idempotent）に設計

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants からの株価（日次 OHLCV）、財務データ、マーケットカレンダー取得（jquants_client）
  - 差分取得 / バックフィル / 品質チェック（data.pipeline、data.quality）
- ニュース収集・NLP
  - RSS フィードの収集と前処理（news_collector）
  - OpenAI を用いた銘柄別ニュースセンチメント算出（ai.news_nlp）
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定（ai.regime_detector）
- 研究用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算（research.factor_research）
  - 将来リターン、IC、統計サマリー等（research.feature_exploration、data.stats）
- 監査・トレーサビリティ
  - signal → order_request → executions を辿れる監査テーブル定義・初期化（data.audit）
- 環境設定
  - .env/.env.local と OS 環境変数から設定を自動読み込み（config）

---

## 必要条件 / 依存パッケージ（例）

- Python 3.10+
- duckdb
- openai
- defusedxml

（実際のプロジェクトでは requirements.txt を用意してください。上記は主要依存です。）

例 requirements.txt（参考）
```
duckdb>=0.6
openai>=1.0
defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / 作業ディレクトリへ配置
2. 仮想環境を作成し有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install -r requirements.txt
   - （編集開発用）pip install -e .
4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（および必要なら `.env.local`）を配置すると自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（LLM 機能を使う場合は必須）
   - （任意）LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
   - （任意）DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH など（デフォルトあり）

例 `.env`（参考）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な API / 実行例）

※ すべての操作は Python から DuckDB 接続（duckdb.connect(...)）を渡して実行します。

1) DuckDB 接続の作成（例）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

2) 日次 ETL（データ取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントのスコア付与（ai.news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で渡せます
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

4) 市場レジーム判定（ai.regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

r = score_regime(conn, target_date=date(2026, 3, 20))
print("regime scored:", r)
```

5) 監査 DB 初期化（監査テーブル作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して監査ログを記録できるようになる
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from datetime import date
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

補足:
- OpenAI 呼び出しは内部でリトライ・JSON 検証を行いますが、API キーやレート制限の管理は運用側で行ってください。
- ETL / 保存処理は基本的に冪等（ON CONFLICT）です。スケジューラ（cron / systemd timer / Airflow）等で日次実行を想定しています。

---

## 設定（config）について

- `.env` / `.env.local` をプロジェクトルートから自動読み込みします。優先順位は OS 環境変数 > .env.local > .env。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 主要な Settings プロパティ（settings オブジェクト経由で取得可能）
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
  - settings.line_channel_access_token
  - settings.duckdb_path, settings.sqlite_path
  - settings.env (development | paper_trading | live)
  - settings.log_level

環境変数が未設定の必須項目アクセス時は ValueError が発生します（実行前に .env を用意してください）。

---

## 注意点 / 実運用のヒント

- Look-ahead bias を回避するため、モジュールは date や window を明示的に受け取る設計です。内部で `date.today()` などを不用意に参照しないことを心がけていますが、バッチ実行時は `target_date` を明示して呼ぶことを推奨します。
- J-Quants API のレート制限（120 req/min）に対応するレートリミッタと再試行ロジックがありますが、複数ジョブを並列で叩く場合はシステム全体でのレート設計に注意してください。
- OpenAI 呼び出しは JSON mode を利用し、厳密なレスポンス検証を行っていますが、LLM の挙動は変動するため追加の監視を推奨します。
- DuckDB の executemany に関するバージョン差（空リスト渡せない等）に注意してコードは保護済みです。
- news_collector は SSRF 対策（リダイレクト検査、プライベートIP 検査）、XML 安全パッケージ（defusedxml）を使用しています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                          — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py                       — ニュースセンチメント算出
  - regime_detector.py                — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                 — J-Quants API クライアント（取得/保存）
  - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
  - etl.py                            — ETL 結果クラス再エクスポート
  - quality.py                        — データ品質チェック
  - stats.py                          — 統計ユーティリティ（zscore_normalize）
  - news_collector.py                 — RSS ニュース収集
  - calendar_management.py            — 市場カレンダー管理 / 営業日判定
  - audit.py                          — 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py                — モメンタム/ボラティリティ/バリュー
  - feature_exploration.py            — 将来リターン/IC/統計サマリー

テストや CLI スクリプトは含まれていません（必要に応じて追加してください）。

---

## 追加情報 / 貢献

- バグ報告、改善提案は Issue を立ててください。
- 新しい外部依存を追加する場合は requirements.txt を更新し README に追記してください。
- セキュリティ関連（API キー漏洩、SSRF 等）は優先度高で扱ってください。

---

以上。必要であれば README にサンプル .env.example、CLI 実行例（cron / systemd）や開発用ユニットテストの書き方を追記します。どの部分を詳しく書き足しましょうか？