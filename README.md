# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants／kabuステーション／RSS／OpenAI（LLM）等を組み合わせて、データ収集（ETL）、品質チェック、ニュースセンチメント、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ管理などを提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）例
- 使い方（主要 API の例）
- ディレクトリ構成

---

プロジェクト概要
----------------
KabuSys は日本株のデータパイプライン／研究／自動売買に必要な基盤機能をモジュール化した Python パッケージです。主な目的は以下です。

- J-Quants からの株価・財務・カレンダーなどの差分 ETL（DuckDB 保存、冪等性あり）
- RSS ニュースの収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON モード）
- ETF とマクロニュースを合成した市場レジーム（bull/neutral/bear）判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 発注/約定までの監査ログ（監査テーブル・DB 初期化ユーティリティ）
- 設定管理（.env 自動ロード、保護オプション）

設計上の留意点
- ルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を内部的に安易に参照しない）
- API 呼び出しはリトライ/バックオフ・レートリミット制御あり
- DuckDB に対する保存は冪等（ON CONFLICT DO UPDATE 等）
- 外部ネットワーク処理（RSS）に対する安全対策（SSRF、サイズ制限、XML 攻撃対策）

主な機能
--------
- data: ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）、J-Quants クライアント、news_collector、calendar 管理、品質チェック、監査ログ初期化
- ai: ニュース NLP（score_news）と市場レジーム判定（score_regime）
- research: ファクター計算（calc_momentum / calc_value / calc_volatility）、特徴量探索（forward returns / IC / summary）
- config: .env 自動ロード、環境変数ラッパー（Settings）
- data.stats: 汎用統計ユーティリティ（zscore_normalize）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 表記、型ヒントに依存）
- DuckDB を利用可能な環境
- OpenAI API キー、J-Quants リフレッシュトークン等の外部キー

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必要な主なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）
   - 開発中なら編集可能インストール:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env を作成（下記の例参照）
   - パッケージ起動時に自動で .env/.env.local がプロジェクトルートから読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

環境変数（.env）例
------------------
以下は最低限必要になる代表的な環境変数の例（実運用では適宜追記してください）:

# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id

# 任意/デフォルトが使えるもの
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development   # development / paper_trading / live
LOG_LEVEL=INFO
KABU_API_BASE_URL=http://localhost:18080/kabusapi

注意:
- パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env を自動読み込みします。
- 自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要 API の例）
------------------------

以下は代表的な使い方例です。各関数は duckdb.DuckDBPyConnection を受け取る設計になっています。

1) 日次 ETL を実行（J-Quants からの差分取得 → 保存 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（AI）で銘柄ごとのスコアを算出
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="your_openai_key")
print(f"scored {count} codes")
```

3) 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="your_openai_key")
```

4) ファクター計算（モメンタム / ボラティリティ / バリュー）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

5) 監査ログ（audit）テーブルの初期化
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

6) カレンダー・営業日取得ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

注意点（運用上の留意）
- OpenAI 呼び出しは JSON mode を使い厳密にパースしています。API レスポンス失敗時はフェイルセーフ（0.0 等）で継続する設計ですが、運用ではログと再試行を検討してください。
- ETL は冪等を意識して設計されていますが、バックテストや再現性のためには DuckDB データの管理に注意してください（fetched_at 等のメタ情報あり）。
- news_collector は RSS フィード取得において SSRF 対策やサイズ制限、XML の安全パーシングを組み込んでいます。RSS ソースは DEFAULT_RSS_SOURCES に追加できます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                 - 環境変数/.env 管理（自動ロード）
- ai/
  - __init__.py
  - news_nlp.py             - ニュースセンチメント（score_news）
  - regime_detector.py      - マーケットレジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py       - J-Quants API クライアント & DuckDB 保存関数
  - pipeline.py             - ETL パイプライン（run_daily_etl 等）
  - etl.py                  - ETLResult 再エクスポート
  - news_collector.py       - RSS 収集（fetch_rss 等）
  - calendar_management.py  - マーケットカレンダーと営業日ロジック
  - quality.py              - データ品質チェック
  - stats.py                - zscore_normalize 等統計ユーティリティ
  - audit.py                - 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py      - calc_momentum / calc_value / calc_volatility
  - feature_exploration.py  - calc_forward_returns / calc_ic / factor_summary / rank
- monitoring/                - （監視系・SQLite 連携など、将来的に監視モジュール）
- strategy/                  - （戦略層：シグナル生成等、別途実装を想定）
- execution/                 - （ブローカー連携・発注ラッパー等、別途実装を想定）

ライセンス・貢献
---------------
（この README にはライセンス情報は含めていません。リポジトリの LICENSE を確認してください）
貢献は Pull Request / Issue を通じて受け付けます。外部 API を扱うコードのため、テスト時は外部呼び出しをモックすることを推奨します。

---

問題・質問・拡張案があれば教えてください。README の追加項目（例: CI、より詳しい .env.example、設定テンプレート、運用チェックリスト等）も作成できます。