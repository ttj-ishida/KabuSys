# KabuSys

日本株向けの自動売買・データ基盤ライブラリセットです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（オーディット）など、取引システムと研究ワークフローに必要な機能群を提供します。

---

## プロジェクト概要

KabuSys は以下を主眼に設計されています。

- Look‑ahead bias を避ける（日時の扱いに注意）
- ETL／データ品質チェックによる堅牢なデータ基盤
- OpenAI（LLM）を用いたニュースセンチメント評価（JSON Mode を利用）
- J-Quants API を用いた株価・財務・カレンダー取得（レート制御・リトライ有り）
- DuckDB を用いたローカル分析・運用ストレージ
- 発注・約定までを辿れる監査ログ（監査用スキーマ）

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants からの株価（daily quotes）・財務（statements）・市場カレンダー取得（jquants_client）
  - 差分取得 / バックフィル / 品質チェックを含む日次 ETL（data.pipeline.run_daily_etl）
- データ品質管理
  - 欠損・スパイク・重複・日付不整合チェック（data.quality）
- マーケットカレンダー管理
  - 営業日判定 / 前後営業日取得 / カレンダーの夜間更新ジョブ（data.calendar_management）
- ニュース収集・NLP
  - RSS 取得・前処理（news_collector.fetch_rss / preprocess_text）
  - LLM を用いた銘柄ごとのニュースセンチメント評価（ai.news_nlp.score_news）
- レジーム判定（AI + テクニカル合成）
  - ETF (1321) の 200 日 MA とマクロニュースセンチメントを合成して日次レジーム判定（ai.regime_detector.score_regime）
- リサーチ・ファクター計算
  - モメンタム / ボラティリティ / バリュー等（research.factor_research）
  - 将来リターン計算・IC・統計サマリー（research.feature_exploration）
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用テーブル初期化・DB（data.audit.init_audit_db / init_audit_schema）
- その他ユーティリティ
  - 簡易統計（data.stats.zscore_normalize）
  - 環境設定管理（config.Settings）

---

## セットアップ手順

前提
- Python 3.10+（型記法や union 型（X | Y）を使用しているため）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに pyproject.toml / requirements.txt がある想定です。なければ下記を手動で）
   ```
   pip install duckdb openai defusedxml
   ```

   開発時は便利なパッケージを追加してください（例: pytest 等）。

4. パッケージを editable インストール（開発向け）
   ```
   pip install -e .
   ```
   （pyproject.toml / setup.cfg がある場合）

5. 環境変数の準備
   プロジェクトルート（.git または pyproject.toml の親ディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（ただし、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。

   必須となる主な環境変数:
   - JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン
   - SLACK_BOT_TOKEN        … Slack 通知に使用する Bot トークン（必要な場合）
   - SLACK_CHANNEL_ID       … Slack チャンネル ID
   - KABU_API_PASSWORD      … kabu ステーション API 用パスワード（発注連携を行う場合）
   - OPENAI_API_KEY         … OpenAI API キー（score_news / score_regime 等で使用）
   任意・デフォルトあり:
   - KABUSYS_ENV            … development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL              … DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH            … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            … sqlite（監視用）パス（デフォルト: data/monitoring.db）

   例 .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   ```

---

## 使い方（代表的な例）

※ ここでは DuckDB を直接使ったコマンドラインもしくは Python スクリプトでの利用例を示します。

1) 設定と DuckDB 接続
```python
from kabusys.config import settings
import duckdb

db_path = str(settings.duckdb_path)  # 設定から取得
conn = duckdb.connect(db_path)
```

2) 日次 ETL 実行（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのセンチメントスコア（LLM を使用）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されていることが前提
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} ai_scores")
```

4) 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を利用
```

5) 監査ログ用 DuckDB 初期化（監査 DB を分ける場合）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_db_path = Path("data/audit.duckdb")
audit_conn = init_audit_db(audit_db_path)
# これで signal_events, order_requests, executions 等のテーブルが作成されます
```

6) RSS フィード取得（ニュースコレクターの一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```
（fetch_rss は記事取得と前処理を行います。DB 保存処理はプロジェクト上の別処理で冪等に保存する想定です）

---

## 環境変数の自動読み込みについて

- config モジュールはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動読み込みします。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 必須環境変数が読み込まれていない状態でアクセスすると ValueError が発生します（例: settings.jquants_refresh_token）。

---

## ログ・実行モード

- 許容される実行環境（KABUSYS_ENV）:
  - development
  - paper_trading
  - live
- ログレベルは LOG_LEVEL 環境変数で設定（DEBUG, INFO, WARNING, ERROR, CRITICAL）

---

## ディレクトリ構成（主要ファイル）

（コードベースの src/kabusys 下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py       — マーケットカレンダー管理
    - etl.py                       — ETL インターフェース再エクスポート
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログスキーマ初期化
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - news_collector.py            — RSS ニュース収集・前処理
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — 将来リターン/IC/統計サマリー
  - ai/、research/ などで OpenAI / DuckDB を利用する箇所があります。

---

## 開発時の注意点 / 補足

- DuckDB の executemany に空リストを渡すと動作が不安定なバージョンがあります（pipeline / ai.news_nlp 内で対策済み）。
- OpenAI 呼び出しは JSON Mode（response_format）を使う設計のため、レスポンスパースの堅牢化処理が入っています。API 失敗時はフェイルセーフとして 0.0 を返す設計箇所が多くあります。
- ニュース取得では SSRF 対策（ホストのプライベート判定、リダイレクト検査）、XML の安全パーシング（defusedxml）などセキュリティ対策を行っています。
- J-Quants クライアントはレート制御・リトライ・401 リフレッシュを備えています。

---

必要であれば、README に含める具体的な .env.example のテンプレートや、docker-compose / systemd を用いた運用例、CI 用の設定例も作成します。どの情報を優先で追加しましょうか？