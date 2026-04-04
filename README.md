KabuSys
=======

KabuSys は日本株を対象としたデータプラットフォーム／リサーチ／自動売買支援ライブラリです。  
DuckDB をデータレイヤに使い、J-Quants API からの ETL、ニュース収集・NLP（OpenAI）、ファクター計算、品質チェック、監査ログ用スキーマなどを提供します。

主な特徴
--------
- J-Quants API を使った差分 ETL（株価・財務・市場カレンダー）の取得と DuckDB への冪等保存
- ニュース収集（RSS）と前処理、news → 銘柄紐付けのためのユーティリティ
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（ai_scores）解析（バッチ・リトライ・レスポンス検証）
- マクロセンチメントと ETF（1321）200 日移動平均乖離を組み合わせた市場レジーム判定
- ファクター計算（モメンタム / バリュー / ボラティリティ等）および特徴量探索（将来リターン・IC・統計サマリ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- 環境変数 / .env 自動読み込み（プロジェクトルート検知、.env.local 優先）

セットアップ（開発用／実行環境）
-----------------
前提：
- Python 3.10+（型ヒントで | 記法を利用）
- DuckDB、OpenAI SDK、defusedxml などが必要

例（venv を使う）:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# その他必要なパッケージがあれば追加でインストールしてください
```

プロジェクトでは .env / .env.local をプロジェクトルート（.git または pyproject.toml がある場所）から自動読み込みします。自動読み込みを無効にするには環境変数を設定します:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

必須（または推奨）環境変数の例（.env）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxx

# OpenAI
OPENAI_API_KEY=sk-xxxxxxx

# kabuステーション API
KABU_API_PASSWORD=...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

# DB/モニタリング
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development      # development | paper_trading | live
LOG_LEVEL=INFO
```

設定は kabusys.config.settings 経由でアクセスできます（例: settings.duckdb_path）。

使い方（主要 API）
-----------------

1) DuckDB 接続を得る（例: ファイル DB）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのスコアリング（OpenAI を使用）
- raw_news / news_symbols が DuckDB に入っていることが前提です。
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数に渡すか、OPENAI_API_KEY 環境変数を設定してください
written_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書込銘柄数:", written_count)
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```
- OpenAI API の呼び出しに失敗した場合はマクロセンチメントを 0.0 としてフェイルセーフで継続します。
- api_key を None にすると環境変数 OPENAI_API_KEY を参照します。

5) ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```
- 返却は各銘柄について (date, code, ...) の辞書リストです。データ不足時は None を返すフィールドがあります。

6) データ品質チェック
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

7) 監査ログ（スキーマ初期化）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

環境変数の注意点
----------------
- 自動的に .env / .env.local をロードします（優先順: OS 環境 > .env.local > .env）。プロジェクトルート検出に失敗した場合は自動ロードをスキップします。
- 自動ロードを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings で定義されている値（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）は必須チェックを行うプロパティがあります。不足時は ValueError が発生します。

主な設計方針（抜粋）
------------------
- ルックアヘッドバイアスの排除: 実行時に datetime.today()/date.today() を不用意に参照しない。target_date を明示して処理を行う設計が徹底されています。
- 冪等性: DuckDB への保存は原則 ON CONFLICT DO UPDATE / DO NOTHING を使い冪等性を担保。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）障害時には部分的にフォールバックして処理継続する実装が多く取り入れられています。
- テスト容易性: API 呼び出しや時間依存を差し替え可能にしてユニットテストを想定した実装になっています（内部関数のモック等）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールです（抜粋）。

- kabusys/
  - __init__.py
  - config.py                         - 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                      - ニュース NLP / スコアリング（OpenAI 経由）
    - regime_detector.py               - 市場レジーム判定（ETF + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py                - J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py                      - ETL パイプライン（run_daily_etl 等）
    - etl.py                           - ETLResult 再エクスポート
    - news_collector.py                - RSS フィード収集・前処理
    - calendar_management.py           - 市場カレンダー管理・営業日判定
    - quality.py                       - データ品質チェック
    - stats.py                         - 汎用統計（zscore 正規化）
    - audit.py                         - 監査ログスキーマ作成ユーティリティ
  - research/
    - __init__.py
    - factor_research.py               - モメンタム/バリュー/ボラティリティ等の計算
    - feature_exploration.py           - 将来リターン / IC / 統計サマリー 等
  - ai、data、research のほか、strategy / execution / monitoring 等の名前空間を公開する設計があります（実装はモジュールにより分かれます）。

補足 / 運用メモ
---------------
- OpenAI 呼び出しはモデル gpt-4o-mini を利用し、レスポンスは JSON mode を期待しています。API レスポンスのバリデーションやリトライ（429 / ネットワーク / 5xx）ロジックが組み込まれています。
- J-Quants API はレート制限を守るため固定間隔スロットリング（120 req/min）と指数バックオフのリトライを行います。401 はリフレッシュトークンによる自動更新を試みます。
- news_collector は SSRF 対策（スキーム検証 / プライベートアドレス検査 / リダイレクト検査）や XML パースで defusedxml を利用しています。
- DuckDB はローカルファイル（例: data/kabusys.duckdb）または ":memory:" が利用可能です。

貢献
----
- バグ報告や機能提案は issue を立ててください。ユニットテストやドキュメント PR を歓迎します。
- 外部 API の鍵や機密情報は .env に置き、リポジトリに含めないでください。

ライセンス
----------
- 本リポジトリにライセンスファイルがある場合はそちらを参照してください（README にはライセンスを含めていません）。

以上が KabuSys の概要と基本的な使い方です。必要なら具体的なユースケース（ETL の cron 設定例、CI/CD、監視設定、戦略→発注フロー等）についても追記します。どの部分を詳しく知りたいか教えてください。