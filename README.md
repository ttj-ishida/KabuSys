# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュースセンチメント（LLM）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどのモジュールを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・AIベースのニュースセンチメント評価・市場レジーム判定・監査ログ等を包括的に扱う Python ライブラリ群です。J-Quants API などを用いてデータを定期的に ETL して DuckDB に保存し、研究・バックテスト・自動売買実行ロジックの基盤を提供します。

設計上のポイント:
- DuckDB を中心にステートレスで再現可能な ETL を実装
- Look-ahead bias を避ける設計（内部で date.today() を不用意に読まない等）
- OpenAI（gpt-4o-mini）を用いたニュース NLP の JSON Mode を利用
- 冪等性（ON CONFLICT / upsert）を重視した保存処理
- API レート制御・リトライ・フェイルセーフの実装

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants から株価日足、財務データ、JPX カレンダーを差分取得・保存（duckdb）
  - pipeline.run_daily_etl による日次一括 ETL
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出（quality.run_all_checks）
- ニュース収集 / 前処理
  - RSS フィード取得（SSRF 対策、トラッキング除去、XML の安全パース）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを統合して LLM に送信し ai_scores を保存（ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して日次レジームを決定（ai.regime_detector.score_regime）
- 研究支援
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン、IC、統計サマリー（research パッケージ）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル群の初期化・データ永続化ヘルパー（data.audit）

---

## 動作要件

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース等）

（実際の requirements.txt はプロジェクトに合わせて準備してください）

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を利用）

3. パッケージをインストール / 開発モードで編集可能に
   - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると、自動的に読み込まれます（ただしテスト等で自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須の環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（自動注文を使う場合）
     - OPENAI_API_KEY: OpenAI APIキー（score_news / score_regime を使う場合）
   - 省略時のデフォルトは config.Settings のプロパティを参照してください（例: KABU_API_BASE_URL のデフォルトは http://localhost:18080/kabusapi）。

例 `.env`（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（代表的な API と実行例）

以下は簡単な使用例です。date は datetime.date 型を渡します。

共通準備:
```python
from kabusys.config import settings
import duckdb
from datetime import date

# DuckDB 接続（settings.duckdb_path は Path を返す）
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュース NLP による銘柄別スコア算出（score_news）
```python
from kabusys.ai.news_nlp import score_news
# OPENAI_API_KEY を環境変数に設定している場合は api_key を省略可
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

4) 監査ログ用 DuckDB の初期化
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# 必要に応じて audit_conn を使って監査テーブルへアクセス
```

5) 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄のファクター辞書のリスト
```

6) データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

---

## 主要な環境変数（抜粋・デフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY (LLM 機能を使う場合は必須)
- KABU_API_PASSWORD (kabuステーション連携)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で `.env` 読み込みを行いません（テスト用途等）

---

## ディレクトリ構成

（パッケージ内の主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            - ニュースセンチメント（OpenAI）
    - regime_detector.py     - 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（取得 + 保存）
    - pipeline.py            - ETL パイプライン（run_daily_etl 等）
    - etl.py                 - ETLResult の再エクスポート
    - calendar_management.py - 市場カレンダー管理・営業日判定
    - news_collector.py      - RSS 収集・前処理
    - stats.py               - 統計ユーティリティ（zscore_normalize）
    - quality.py             - データ品質チェック
    - audit.py               - 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py     - モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py - 将来リターン・IC・統計サマリー

---

## 開発・運用上の注意

- LLM / API 呼び出し
  - OpenAI 呼び出しはリトライやフェイルセーフを備えていますが、API キーや料金に注意してください。production 環境ではレート制御・ロギングを適切に設定してください。
- Look-ahead bias
  - モジュールはバックテストでのルックアヘッドを避ける設計になっています。target_date を必ず明示的に渡すなどの運用ルールを守ってください。
- DuckDB の executemany に関する注意
  - 一部の DuckDB バージョンでは executemany に空リストを渡せない箇所があるため、コード内で空チェックを行っています。DuckDB のバージョン互換性には留意してください。
- .env の自動読み込み
  - config モジュールはプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込みします。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- セキュリティ
  - RSS 取得は SSRF 対策・XML 安全パーサを使用していますが、運用ではネットワークアクセス制御や秘密情報の取り扱いに注意してください。

---

## 参考・拡張ポイント

- 追加データソースの統合（ニュース / マクロ指標等）
- 戦略層（signal 生成、リスク管理、発注エンジン）との接続
- Web UI / モニタリング・アラート機能の実装（LINE 通知等は設定済みのアクセストークンを利用）

---

この README は現行のコード構成（src/kabusys 以下）に基づいて作成しています。実運用時は各 API キー・DB パス・ログ設定を環境ごとに適切に管理してください。質問や追加で載せて欲しい説明があれば教えてください。