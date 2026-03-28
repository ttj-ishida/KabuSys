# KabuSys

日本株の自動売買 / データプラットフォーム用ライブラリ。  
ETL、データ品質チェック、ニュースのNLPスコアリング、マーケットレジーム判定、監査ログ（監査DB）などを含むモジュール群を提供します。

主な設計方針：
- DuckDB を中心としたローカルデータプラットフォーム
- Look‑ahead bias を防ぐ設計（内部で datetime.today()/date.today() を不用意に参照しない）
- 外部API呼び出しはリトライ・レート制御・フェイルセーフを備える
- 冪等性（ETL/保存処理で ON CONFLICT を使用）と監査ログによるトレーサビリティ

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 取得、SSRF対策、トラッキングパラメータ除去）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログスキーマ初期化・監査DBユーティリティ（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースのセンチメントスコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime） — ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成
  - OpenAI（gpt-4o-mini）を使った JSON Mode 応答パーシング、リトライやフォールバック処理を組み込み
- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 特徴量探索・IC 計算・統計サマリー

その他：
- 環境設定ローダ（.env/.env.local をプロジェクトルートから自動読み込み）
- ログレベル・実行環境（development / paper_trading / live）管理

---

## 要求環境（例）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （ネットワークアクセス：J-Quants API、OpenAI、RSS フィード等）

※ 実際の依存関係はプロジェクトの requirements.txt / pyproject.toml を参照してください。

---

## 環境変数

主に以下の環境変数を使用します（必須は README の該当欄を参照）：

必須（Settings._require により未設定時はエラー）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...。デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化
- OPENAI_API_KEY — OpenAI API キー（ai.score_* 関数に渡す api_key を省略する場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト data/monitoring.db）

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（例）

1. リポジトリをクローン / チェックアウトしてプロジェクトルートへ移動

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -r requirements.txt
   または
   - pip install -e .

4. 環境変数を用意（プロジェクトルートに .env を作成）
   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   SLACK_BOT_TOKEN=xoxb-....
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリを作成（必要なら）
   - mkdir -p data

6. 監査DBスキーマを初期化（任意）
   Python スクリプト例:
   ```python
   import kabusys.data.audit as audit
   conn = audit.init_audit_db("data/audit.duckdb")  # ":memory:" も可
   # すでに接続を持っている場合:
   # import duckdb
   # conn = duckdb.connect("data/kabusys.duckdb")
   # audit.init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（簡単な例）

以下はライブラリの代表的な呼び出し例です。すべて Python から呼び出します。

1) DuckDB 接続を作る（settings.duckdb_path を利用）
```python
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)
```

2) 日次 ETL を実行（J-Quants からデータ取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を指定可
print(result.to_dict())
```

3) ニュースの NLP スコアリング（OpenAI を使用）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は DuckDB 接続
written = score_news(conn=conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

4) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn=conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査テーブル初期化済みで、監査DBを作る
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

6) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 注意事項 / 設計上のポイント

- AI（OpenAI）を呼び出す箇所は JSON Mode を使い、レスポンスを厳密に検証します。不正なレスポンスや API 例外時はフォールバック（0.0 等）して処理を継続するよう設計されています。
- ETL・保存処理は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を前提としています。
- DuckDB の executemany に空リストを与えない等の実装上の互換性考慮があります（コード内にコメントあり）。
- カレンダー情報が無い場合は曜日ベース（週末は非営業日）でフォールバックします。
- 内部で datetime.today()/date.today() を不用意に参照しないよう設計されており、バックテスト等での look‑ahead bias を防止します。

---

## ディレクトリ構成（主なファイル）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得/保存/認証/レート制御）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL 公開型（ETLResult 再エクスポート）
    - calendar_management.py       — マーケットカレンダー管理
    - news_collector.py            — RSS ニュース収集（SSRF 対策・正規化）
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py       — 将来リターン計算 / IC / 統計サマリー

各モジュールの docstring に詳細な処理フロー・設計方針が記載されています。実装はコメントとログメッセージによって安全な動作を補助します。

---

もし README に追記したい利用シナリオ（CI 用スクリプト例、Dockerfile、systemd ユニット、Slack 通知例など）があれば教えてください。必要に応じてサンプル .env.example や簡易デプロイ手順も追加します。