# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）  
このリポジトリは「KabuSys」と呼ばれる日本株の自動売買／データ基盤コンポーネント群を提供します。ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants / kabu ステーション連携など、運用に必要なユーティリティとアルゴリズムを含みます。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 動作要件（依存関係）
- セットアップ手順
- 環境変数（設定）
- 使い方（簡易サンプル）
- ディレクトリ構成
- 注意事項

---

## プロジェクト概要
KabuSys は次の目的を持つ Python モジュール群です。

- J-Quants API から株価・財務・カレンダー等を取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と OpenAI を利用した記事/銘柄単位のセンチメント分析（ai.news_nlp）
- マクロセンチメントと MA 乖離を組み合わせた市場レジーム判定（ai.regime_detector）
- 研究用途のファクター計算・特徴量探索（research.*）
- データ品質チェック・監査ログ用スキーマ管理（data.quality / data.audit）
- J-Quants クライアント、ニュース収集、カレンダー管理など運用用ユーティリティ群

設計方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」を重視しています。

---

## 主な機能一覧
- data.jquants_client: J-Quants API からの差分取得・保存（レートリミット・リトライ・トークン自動リフレッシュ対応）
- data.pipeline: 日次 ETL（カレンダー・株価・財務）と品質チェックの一括実行
- data.news_collector: RSS フィード取得および前処理（SSRF 対策、トラッキング除去、冪等保存を想定）
- ai.news_nlp: OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント取得（チャンク・リトライ付き）
- ai.regime_detector: ETF（1321）の MA とマクロニュースセンチメントを合成して市場レジームを判定し保存
- research.*: モメンタム / バリュー / ボラティリティ等のファクター計算、および IC / 統計サマリ
- data.quality: 欠損・スパイク・重複・日付不整合などのデータ品質チェック
- data.audit: シグナル → 発注 → 約定までの監査ログスキーマと初期化ユーティリティ

---

## 動作要件（依存関係）
少なくとも以下パッケージが必要です（バージョンはプロジェクト方針に従って調整してください）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

（本コードは urllib を標準ライブラリで使用しているため requests は必須ではありませんが、運用上必要なら追加してください）

例（pip）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   git clone <このリポジトリURL>
   cd <repo>

2. 仮想環境を作成・有効化（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （パッケージ一覧を requirements.txt にまとめている場合は pip install -r requirements.txt を使用）

4. パッケージを開発モードでインストール（プロジェクト内で import する場合）
   pip install -e .

5. 環境変数を設定
   - .env または .env.local をプロジェクトルートに置くと自動的に読み込まれます（既定では OS 環境変数 > .env.local > .env の順）。
   - 自動読み込みを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 環境変数（主な設定）
Settings クラスが参照する主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL で使用）

必要に応じて:
- KABU_API_PASSWORD : kabu ステーション API のパスワード
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY : OpenAI API キー（ai モジュールを直接使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知用（任意）

データベース / ファイルパス（デフォルト値は下記）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)

システム設定:
- KABUSYS_ENV : development | paper_trading | live（デフォルト development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

注意: Settings のプロパティはいくつか必須値を _require() によって検査します。未設定でアクセスすると ValueError が発生します。

---

## 使い方（簡易サンプル）

下記は典型的な Python API 呼び出し例です。各関数は DuckDB 接続を受け取るので、ローカルの DuckDB ファイルを指定します。

- DuckDB 接続を作る:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行（カレンダー・株価・財務・品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースに対する AI スコア生成:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026,3,20))
print("scored:", count)
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

# OpenAI API key は env OPENAI_API_KEY を使うか api_key 引数で指定
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログスキーマ初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # データベースを作成してスキーマを初期化
```

- J-Quants トークンの取得:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # JQUANTS_REFRESH_TOKEN が環境変数に必要
```

---

## 主要モジュールの説明（抜粋）
- kabusys.config
  - .env の自動読み込み（プロジェクトルート検出）と Settings クラスを提供
  - 自動読み込み順: OS 環境変数 > .env.local > .env

- kabusys.data.jquants_client
  - J-Quants API 呼び出し、ページネーション、ID トークン管理、DuckDB への保存ユーティリティ
  - save_* 系関数は ON CONFLICT DO UPDATE による冪等保存

- kabusys.data.pipeline
  - run_daily_etl を中心とした ETL ワークフロー実装。品質チェックもここで呼び出す。

- kabusys.ai.news_nlp / kabusys.ai.regime_detector
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメントと市場レジーム判定ロジック。API 呼び出しは堅牢なリトライ設計。

- kabusys.research
  - ファクター計算（momentum/value/volatility）と探索用ユーティリティ（forward returns, IC, summary）

---

## ディレクトリ構成
（主要ファイルを抜粋）

- src/kabusys/
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
    - (その他 utility モジュール)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

データファイル（デフォルト想定場所）
- data/kabusys.duckdb        (DuckDB メイン DB)
- data/monitoring.db         (SQLite など監視用 DB)

---

## 注意事項 / 運用メモ
- OpenAI や J-Quants API は課金・レート制限があるため、実運用では API キー管理とコスト監視を行ってください。
- ai モジュールは API 呼び出しで外部通信を行います。テスト時は _call_openai_api をモックするなどして外部依存を切ってください（コード中にモック想定のコメントあり）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から検出されます。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンがあるため、コード中で空チェックが入っています。DuckDB のバージョン差異に注意してください。
- news_collector は SSRF 対策・最大受信サイズ制限・トラッキング除去等のセキュリティ配慮を実装しています。

---

この README はコードベースの主要機能と利用方法のサマリです。より詳しい設計方針や仕様は各モジュール内の docstring（コメント）を参照してください。必要であれば利用例や運用手順（CI/デプロイ、ジョブスケジューラ連携、監視/アラート設定など）を追加で作成できます。