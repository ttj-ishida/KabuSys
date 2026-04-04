KabuSys — 日本株自動売買・データ基盤ライブラリ
====================================

概要
----
KabuSys は日本株向けのデータパイプライン、NLP/LLM を使ったニュース解析、ファクター計算、監査（オーディット）などを提供する Python パッケージです。  
主に以下用途を想定しています。

- J-Quants API からのデータ ETL（株価、財務、マーケットカレンダー）
- RSS ベースのニュース収集と LLM を用いた銘柄ごとのセンチメント算出
- 市場レジーム判定（ETF MA とマクロニュースを組合せ）
- ファクター計算や特徴量探索（リサーチ用途）
- 発注フローを追跡する監査ログ（DuckDB ベース）の初期化・管理
- データ品質チェック（欠損、スパイク、重複、日付整合性）

主な機能
--------
- ETL パイプライン（kabusys.data.pipeline.run_daily_etl 等）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 差分取得、ページネーション、リトライ、トークン自動リフレッシュ
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、SSRF/サイズ対策、トラッキングパラメータ除去、冪等保存
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを JSON で取得、DuckDB へ保存
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを合成して daily レジームを判定
- 研究用モジュール（kabusys.research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算、IC・前方リターン計算、統計ユーティリティ
- データ品質チェック（kabusys.data.quality）
- 監査ログスキーマ初期化・専用 DB 作成（kabusys.data.audit）

要件
----
- Python 3.10+
- 必須パッケージ例（代表）:
  - duckdb
  - openai
  - defusedxml
- （ネットワークアクセスを伴う機能）J-Quants と OpenAI の API キーが必要

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ... （プロジェクトルートに移動）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があれば pip install -e . や pip install -r requirements.txt を使用）

4. 環境変数の設定
   - プロジェクトルートの .env または .env.local に設定を置くと自動で読み込まれます（kabusys.config が自動ロード）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

推奨の .env（例）
----------------
以下は最低限よく使われるキー例です。実運用では .env.example を参照して必要な値を設定してください。

- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- OPENAI_API_KEY=sk-...
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development         # development / paper_trading / live
- LOG_LEVEL=INFO

設定管理の挙動
--------------
- 優先順: OS 環境変数 > .env.local > .env
- 自動ロードはパッケージ起点で .git または pyproject.toml を探してプロジェクトルートを決定します。
- 必須値が不足すると Settings プロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。

基本的な使い方（サンプル）
-------------------------

1) DuckDB に接続して日次 ETL を実行（J-Quants トークンは settings で参照されます）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのスコア付け（OpenAI API キーは OPENAI_API_KEY または api_key 引数で指定可能）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数からキー取得
print(f"scored {n_written} codes")
```

3) 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DB 初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/monitoring.audit.duckdb")
# conn を使って監査テーブルが作成されていることを確認できます
```

注意点 / 実装上の考慮
-------------------
- Look-ahead バイアス対策:
  - 多くの関数は内部で datetime.today() を直接参照せず、呼び出し側が target_date を渡す設計です（バックテスト対応）。
- OpenAI 呼び出し:
  - news_nlp と regime_detector は OpenAI の JSON mode を利用します。API 呼び出しのため OPENAI_API_KEY が必要です。関数は api_key 引数で上書きできます。
  - リトライとフェイルセーフ: API エラー時は適切にリトライまたはスコアを中立化（0.0）して継続する実装です。
- J-Quants クライアント:
  - レートリミット（120 req/min）やトークン自動リフレッシュ、ページネーション、リトライ等を内包しています。

ディレクトリ構成（抜粋）
---------------------
- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュース NLP / スコア付け
    - regime_detector.py         -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント + 保存ロジック
    - pipeline.py                -- ETL パイプライン
    - etl.py                     -- ETL インターフェース (ETLResult 再エクスポート)
    - news_collector.py          -- RSS 収集
    - calendar_management.py     -- 市場カレンダー管理
    - quality.py                 -- データ品質チェック
    - stats.py                   -- 統計ユーティリティ（zscore_normalize 等）
    - audit.py                   -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         -- ファクター計算（momentum, value, volatility）
    - feature_exploration.py     -- 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ 等それぞれのユーティリティとスキーマ定義

ライセンス・貢献
----------------
- ライセンス情報や開発フロー（PR / Issue）についてはリポジトリのトップレベルを参照してください（ここには含まれていません）。

補足情報
-------
- ログレベル: 環境変数 LOG_LEVEL で調整可能（DEBUG/INFO/...）。
- 環境切替: KABUSYS_ENV により development / paper_trading / live を選択可能。is_live / is_paper / is_dev が Settings から参照可能。
- テスト時: config の自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

問題の報告や使い方の相談があれば、リポジトリの Issue に詳細を記載して提出してください。