# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買支援ライブラリです。J-Quants API や RSS などからデータを収集・保存し、データ品質チェック、ファクター計算、ニュースの LLM ベーススコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）などを提供します。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ」です。バックテストやライブ運用の両方を想定したモジュラ設計になっています。

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants から株価（日足）、財務データ、JPX カレンダーを差分取得・保存（ページネーション・レート制御・トークン自動リフレッシュ対応）
  - ETL パイプライン（差分取得 / 保存 / 品質チェック / カレンダー先読み / バックフィル）
- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付整合性チェック
- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、正規化）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコアリング（ai_scores）
- マーケットレジーム判定
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次で 'bull'/'neutral'/'bear' を判定
- 研究（Research）ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（情報係数）、統計サマリー、Z スコア正規化
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までのトレーサビリティを保持する監査テーブルの初期化・管理
- カレンダー管理
  - market_calendar の更新、営業日判定、next/prev_trading_day 等のユーティリティ

---

## 要件 (概略)

- Python 3.10+
- ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants API アクセス用のリフレッシュトークン
- OpenAI API キー（ニュース NLP / レジーム判定を使用する場合）

（プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -e .          # パッケージが組み込み済みの場合
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements があれば `pip install -r requirements.txt` を使用）

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - `.env` のサンプル（必要最小限の例）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - 優先順位: OS 環境変数 > .env.local > .env（.env.local は .env を上書き）

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから利用する際の例です。いずれも DuckDB 接続を渡して操作します。

1) 設定の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

2) DuckDB 接続を用意して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニューススコアリング（OpenAI キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は duckdb connection
count = score_news(conn, target_date=date(2026, 3, 19))
print(f"scored {count} codes")
```

4) マーケットレジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 19))
```

5) 監査ログ DB の初期化（専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# audit_conn を使って監査テーブルへ書き込み・参照が可能
```

6) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 19))
val = calc_value(conn, date(2026, 3, 19))
vol = calc_volatility(conn, date(2026, 3, 19))
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須で ETL 実行時に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携などで使用）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: 通知先のチャンネル ID
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment。許可値: development, paper_trading, live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

注意: Settings オブジェクトは環境変数未設定時に ValueError を投げるプロパティがあります（必須変数）。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールの階層と役割の概要（src/kabusys 以下）。

- kabusys/
  - __init__.py              -- パッケージ初期化（バージョン等）
  - config.py                -- 環境変数 / 設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュースの LLM スコアリング（ai_scores への書き込み）
    - regime_detector.py     -- 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch / save）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - etl.py                 -- ETLResult の再エクスポート
    - calendar_management.py -- 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      -- RSS 収集と前処理
    - quality.py             -- データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py               -- 汎用統計ユーティリティ（zscore_normalize）
    - audit.py               -- 監査ログ（監査スキーマの初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py     -- Momentum/Value/Volatility のファクター計算
    - feature_exploration.py -- 将来リターン・IC・統計サマリー

（上記以外にも strategy / execution / monitoring 等の名前空間が __all__ に宣言されていますが、ここでは主要な data/ai/research 部分を抜粋しています）

---

## 開発・運用上の注意点

- ルックアヘッドバイアス防止:
  - 多くのモジュールは date を明示的に引数として受け取り、内部で datetime.today()/date.today() を直接参照しない設計です。バックテスト時は必ず過去の date を渡してください。
- 冪等性:
  - ETL / 保存関数は可能な限り冪等性（ON CONFLICT DO UPDATE / INSERT … DO NOTHING）を考慮しています。
- フェイルセーフ:
  - OpenAI / 外部 API の失敗時はスコアを 0 にフォールバックするなど、例外で全処理を止めない設計が多く採用されています（ただし重大エラーはログに出力されます）。
- セキュリティ:
  - RSS 収集は SSRF 対策、defusedxml を使った XML パース等を行っています。
- テスト:
  - モジュール内に外部呼び出しを差し替えるためのフック（例: _call_openai_api の差し替え）があります。unit テスト時はモックして利用してください。

---

## 貢献・ライセンス

この README はコードベースの概要を示すためのドキュメントです。実際の運用・導入時はプロジェクトの LICENSE / CONTRIBUTING ガイドラインに従ってください。

---

必要であれば、特定のユースケース（例: ローカルでの ETL 実行手順、OpenAI のコスト見積もり、監査 DB 設計の詳細）について追記します。どの部分を詳しく書いて欲しいか教えてください。