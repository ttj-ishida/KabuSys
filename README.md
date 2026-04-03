# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → ニュースNLP（OpenAI） → 市場レジーム判定 → 監査ログ といったワークフローを想定したユーティリティ群を提供します。

---

## 主な特徴
- データ取得（J-Quants API）と DuckDB への冪等保存（ON CONFLICT）
- 日次 ETL パイプライン（価格データ / 財務データ / 市場カレンダー）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・前処理（RSS）とニュースセンチメントの LLM スコアリング（OpenAI）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）
- 研究用ユーティリティ（ファクター計算 / 将来リターン / IC / 統計）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）を格納するスキーマ初期化関数
- 設定は環境変数 / .env から読み込み（自動ロードあり。テスト時に無効化可能）

---

## 機能一覧（概観）
- kabusys.config
  - .env の自動読み込み、必須値チェック、各種パス／閾値の設定
- kabusys.data
  - jquants_client：J-Quants API クライアント（ページネーション・リトライ・レート制御・保存関数）
  - pipeline / etl：差分 ETL と日次 ETL（run_daily_etl）
  - quality：データ品質チェック（run_all_checks）
  - news_collector：RSS 収集・前処理・SSRF 対策
  - calendar_management：JPX カレンダー管理 / 営業日判定
  - stats：Zスコア正規化ユーティリティ
  - audit：監査ログスキーマの初期化 / audit DB 初期化
- kabusys.ai
  - news_nlp.score_news：銘柄別ニュースセンチメントを ai_scores テーブルへ書込
  - regime_detector.score_regime：市場レジーム（日次）を market_regime テーブルへ書込
- kabusys.research
  - factor_research：モメンタム／バリュー／ボラティリティ等のファクター計算
  - feature_exploration：将来リターン、IC、統計サマリー、ランク関数 等

---

## 動作環境 / 要件
- Python >= 3.10
- 主なパッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- （実運用時）J-Quants API アクセス用のリフレッシュトークン、OpenAI API キー等が必要

依存パッケージは pyproject.toml / requirements.txt がある場合はそちらを参照してください。ローカルで試す場合は最低限次をインストールします:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発 editable 推奨）
   - git clone ...
   - pip install -e .

2. Python バージョンを満たしていることを確認（>=3.10）。

3. 環境変数を設定（.env をプロジェクトルートに置くと自動読み込みされます）。
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。
   - テストなどで自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須設定（例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - OPENAI_API_KEY=sk-xxxx (AI 機能を使う場合必須)
   - KABU_API_PASSWORD=（kabuステーション API を使う場合）
   - （任意）KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH=data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH=data/monitoring.db（デフォルト）
   - その他監視・ログ設定は kabusys.config.Settings のプロパティ参照

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 主要環境変数（抜粋・説明）
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルトあり）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（動作モード）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

.env 例（実際の値は秘密にしてください）:
JQUANTS_REFRESH_TOKEN=eyJhbGci...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単な例）

※ 以下コードは Python REPL やスクリプトで実行します。

1) ETL（日次パイプライン）の実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントのスコアリング（OpenAI API キー必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026,3,20))
print(f"written scores: {written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

4) 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄のモメンタム辞書リスト
```

---

## 実装上の注意 / 設計方針（抜粋）
- Look-ahead バイアス回避: 関数は内部で date.today() を直接参照しないことが設計方針になっています（target_date を引数で受け取る）。
- ETL / AI 呼び出しは外部 API に依存するため、テスト時はネットワーク呼び出しをモックすることを推奨します（モジュール内の _call_openai_api や _urlopen 等を patch）。
- ニュース収集は SSRF 対策・受信サイズ制限・XML セキュリティを組み込んでいます。
- J-Quants クライアントはレートリミッターとリトライ・401 リフレッシュを実装しています。
- DuckDB に対する INSERT は冪等化（ON CONFLICT DO UPDATE / DO NOTHING）を基本としています。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下を抜粋）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (re-export)
  - quality.py
  - stats.py
  - calendar_management.py
  - news_collector.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

各モジュールの責務はそれぞれのファイル冒頭の docstring にまとめられています。詳しい挙動やパラメータは該当ソースを参照してください。

---

## テストとデバッグのヒント
- OpenAI 呼び出しは _call_openai_api をモックして挙動をシミュレートできます（kabusys.ai.news_nlp._call_openai_api、kabusys.ai.regime_detector._call_openai_api）。
- J-Quants クライアントの HTTP 呼び出しは urllib を使用しているため、ネットワークエラーや HTTPError のシナリオをユニットテストで模擬可能です。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に推奨）。

---

必要な追加情報（例：requirements.txt、実運用の deployment 手順、CI 設定、詳細な設計ドキュメント等）があれば、それに基づいて README を拡張します。どの部分を詳しく書きたいか教えてください。