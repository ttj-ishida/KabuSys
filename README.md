# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの市場データ取得）やニュース収集・NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）、および市場レジーム判定など、運用に必要な基盤機能を備えます。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API障害時の緩和）」「DuckDB を中核としたオンプレ／クラウド両対応」です。

---

## 主な機能一覧

- データ取得（J-Quants）と ETL パイプライン
  - 日次株価（OHLCV）・財務データ・上場銘柄情報・マーケットカレンダーの差分取得・保存
  - レートリミッター、リトライ、トークン自動リフレッシュ、ページネーション対応
- ニュース収集
  - RSS フィード取得（SSRF 対策、圧縮対応、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄別ニュース統合評価（gpt-4o-mini を想定） → ai_scores に書き込み
  - レート制限・再試行・レスポンス検証・スコアクリップ
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成し
    日次で 'bull' / 'neutral' / 'bear' を判定し market_regime に記録
- 研究（Research）用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- マーケットカレンダー管理
  - JPX カレンダーの差分取得・保存、営業日判定・次/前営業日の検索など
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（QualityIssue を返す）
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査スキーマ定義と初期化（DuckDB）
  - 発注フローのトレーサビリティ確保（UUID による冪等性）
- 設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（プロジェクトルート検出）
  - 必須環境変数の明示とアクセス API（kabusys.config.settings）

---

## 要求環境

- Python 3.10+
  - （コードは代替型注釈 (|) を使用しているため Python 3.10 以上を想定）
- ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （ネットワークや RSS を扱うため標準ライブラリ以外も必要）
- DuckDB をファイルまたはインメモリで使用

注: 実際の requirements.txt / pyproject.toml はプロジェクトに合わせて作成してください。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンしてプロジェクトルートへ移動
   - 本 README はパッケージルート（.git または pyproject.toml があるディレクトリ）を探して .env を自動読み込みします。

2. 仮想環境の作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -e .    # 開発インストール（pyproject.toml/setup.py がある前提）
   - または最低限: pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を作成して必要なキーを設定します。
   - 自動ロードはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   代表的な環境変数（.env 例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...        # news_nlp / regime_detector で使用
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development   # development | paper_trading | live
   - LOG_LEVEL=INFO

   注意: kabusys.config.Settings は必須キーが未設定の場合 ValueError を送出します（JQUANTS_REFRESH_TOKEN など）。

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（サンプル）

以下は代表的な利用例です。実行は Python REPL またはスクリプト中で行います。

- DuckDB へ接続して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアを生成（ai.news_nlp.score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で渡す
print(f"scored {count} symbols")
```

- 市場レジーム判定（ai.regime_detector.score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログスキーマ初期化

```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: も可
```

- 設定の読み取り

```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- OpenAI API 呼び出しを行う機能は api_key 引数を受け付けます。None の場合は環境変数 OPENAI_API_KEY を参照します。
- 日付関連関数はルックアヘッドバイアスを防ぐため内部で date.today() を不用意に参照しない設計です。テスト時には明示的な target_date を渡してください。
- ETL / 保存処理は冪等（ON CONFLICT / DO UPDATE）になっています。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知に使用する Slack 設定（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector で使用）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV — 環境 ('development' | 'paper_trading' | 'live')
- LOG_LEVEL — ログレベル ('DEBUG','INFO','WARNING','ERROR','CRITICAL')
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化する場合に 1 を設定

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml の存在する親ディレクトリ）にある .env を自動で読み込みます。
- 読み込み順序: OS 環境 > .env > .env.local（.env.local は .env を上書き可能）
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## テスト・開発時のヒント

- OpenAI 呼び出しやネットワークを伴う箇所はモックしやすいように内部呼び出しを分離しています（例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で置き換え可能）。
- 自動 .env 読み込みはテストで影響する場合があるため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。
- DuckDB は簡単にインメモリで起動できるためテストは ":memory:" を用いると高速です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

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
  - etl.py
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - pipeline.py (ETLResult 再エクスポート在り)
  - etl.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*.py（ファクター計算・統計）
- その他（strategy, execution, monitoring などはパッケージ公開対象として __all__ に含まれますが、実装はプロジェクト内に応じて追加してください）

---

## 参考・補足

- 各モジュールの関数やクラスはドキュメンテーション文字列（docstring）で詳細が記載されています。実装の挙動（例: リトライ方針、フェイルセーフ時の戻り値、DB トランザクション扱い等）を確認してください。
- 本 README はコードベースに含まれる実装を元に作成しています。運用や本番環境で使用する際は、テスト、監査、アクセス権管理（シークレット管理）を十分に行ってください。

---

もし README に追加したい「実行スクリプト例」「CI / デプロイ手順」「詳細な .env.example」などがあれば、その内容を教えてください。必要に応じて追記します。