KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けのデータプラットフォームおよび自動売買リサーチ基盤です。  
J-Quants API を用いた時系列データの ETL、ニュースの収集と LLM を用いたニュースセンチメント解析、マーケットレジーム判定、ファクター計算、データ品質チェック、監査（トレーサビリティ）などの機能を備えています。  
パッケージは src/kabusys 配下にモジュールとして実装されています。

主な特徴
--------
- J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御、保存）
- 日次 ETL パイプライン（価格 / 財務 / カレンダー取得、品質チェック）
- ニュース収集（RSS）・前処理・raw_news 保存・銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュース NLP（銘柄ごとのセンチメント）とマクロセンチメントを用いた市場レジーム判定
- Research 向けファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン、IC 計算、Z スコア正規化
- データ品質チェック機能（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order_request → execution のトレース可能なスキーマと初期化ユーティリティ）
- DuckDB を主要なローカル DB として利用

セットアップ
----------
前提
- Python 3.10 以上（型注釈に | が使用されているため）
- ネットワーク接続（J-Quants / OpenAI / RSS）

1) 仮想環境作成（推奨）
```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
```

2) 必要パッケージのインストール（プロジェクトに requirements.txt がない場合の最低限）
```bash
pip install duckdb openai defusedxml
```
- 実際の運用では logging / requests 等の追加依存や slack 用ライブラリ等を使う可能性があります。プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

3) 環境変数 / .env の用意
- 必須（動作に応じて設定してください）
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector の呼び出し時に引数で上書きも可能）
  - KABU_API_PASSWORD: kabu ステーション API パスワード（発注系を使う場合）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知系（必要に応じて）
- 任意 / デフォルトあり
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env の自動ロードを無効化
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
- 自動読み込み
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を親方向に探索）から .env → .env.local の順で自動読み込みします。テスト時などで無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要な API 例）
--------------------

下記例は最小限の呼び出し方のサンプルです。各関数は DuckDB 接続オブジェクトを受け取ります。

1) DuckDB 接続の準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（価格 / 財務 / カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（銘柄ごとの ai_scores 書き込み）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されている場合は api_key 引数は省略可
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

4) 市場レジーム判定（ma200 とマクロニュースを統合）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

5) ファクター計算 / リサーチユーティリティ
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

t = date(2026, 3, 20)
mom = calc_momentum(conn, t)
val = calc_value(conn, t)
vol = calc_volatility(conn, t)
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

6) 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db

# audit 専用の DB ファイルを用意して初期化
audit_conn = init_audit_db("data/audit.duckdb")
# 必要な監査テーブル(signal_events / order_requests / executions) が作成されます
```

設定と注意点
-------------
- OpenAI 呼び出しはタイムアウト / レートリミットに対応したリトライ実装が各モジュールに組み込まれています。API キーは env 変数 OPENAI_API_KEY か関数引数で与えます。
- J-Quants クライアントは ID トークンの自動取得／キャッシュとリフレッシュをサポートします。JQUANTS_REFRESH_TOKEN を環境変数に設定してください。
- ルックアヘッドバイアス回避のため、各モジュールは date / target_date を明示的に受け取り、datetime.today() の乱用を避ける設計です。
- DuckDB のバージョンによっては executemany に空リストを渡せない制約等があるため、空チェックが各所に入っています。
- テスト実行時などで .env の自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソース配下の主要なファイル・モジュールの一覧と簡単な説明（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 読み込み、settings オブジェクトを公開
  - ai/
    - __init__.py
    - news_nlp.py        : 銘柄別ニュースセンチメントスコア生成（OpenAI）
    - regime_detector.py : マクロセンチメントと ETF ma200 を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  : J-Quants API クライアント（fetch / save）
    - pipeline.py        : ETL パイプライン（run_daily_etl 等）
    - etl.py             : ETLResult の再エクスポート
    - news_collector.py  : RSS 取得・正規化・raw_news 保存
    - quality.py         : データ品質チェック群
    - stats.py           : zscore_normalize 等の統計ユーティリティ
    - calendar_management.py : マーケットカレンダー管理（営業日判定等）
    - audit.py           : 監査ログスキーマの初期化 / audit DB ユーティリティ
  - research/
    - __init__.py
    - factor_research.py : Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py : 将来リターン計算、IC, ランク関数、統計サマリー
  - ai/__init__.py
  - research/__init__.py

（上記は抜粋です。実際のツリーはプロジェクトルートの src/kabusys を参照してください）

開発・貢献
----------
- コードはモジュール単位でユニットテスト可能な設計を意識しています（外部 API 呼び出しは注入やモックで差し替えられる）。
- .env.example を用意して、必要な環境変数をドキュメント化することを推奨します（本リポジトリには含まれていないため作成してください）。
- テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使い、環境を明示的にセットアップしてください。

付録：よく使う環境変数一覧
-------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY        — OpenAI API キー（必須 for news/regime）
- KABU_API_PASSWORD     — kabu ステーション API パスワード（注文機能を使う場合）
- KABU_API_BASE_URL     — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       — Slack Bot Token（通知がある場合）
- SLACK_CHANNEL_ID      — Slack チャンネル ID
- DUCKDB_PATH           — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           — SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV           — development / paper_trading / live（デフォルト development）
- LOG_LEVEL             — ログレベル（DEBUG/INFO/...）

お問い合わせ・ライセンス
-----------------------
この README はソースコードのドキュメント化目的で自動生成されました。ライセンス・コントリビューション指針はプロジェクトルートに別途用意してください。必要があれば README に追記します。