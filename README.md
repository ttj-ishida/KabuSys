KabuSys — 日本株自動売買 / データ基盤ライブラリ
========================================

概要
---
KabuSys は日本株向けのデータ収集・品質管理・ファクター研究・AI（LLM）を用いたニュース解析・市場レジーム判定・監査ログ管理を含む内部ライブラリ群です。ETL パイプライン（J-Quants からのデータ取得）、DuckDB を使ったデータ保存・集計、OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析と市場レジーム判定、監査テーブル（発注→約定のトレース）などを提供します。バックテストや研究（Research）用のユーティリティも含まれます。

主な機能
---
- データ取得 / ETL
  - J-Quants API から株価（日足）、財務データ、JPX カレンダーの差分取得（ページネーション対応、レート制御、リトライ、トークン自動リフレッシュ）
  - ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを一括実行
- データ品質チェック
  - 欠損、重複、日付不整合、スパイク（急変）検出（品質レポートを返す）
- ニュース収集 / NLP
  - RSS 取得（SSRF 対策、URL 正規化、トラッキング除去）
  - OpenAI によるニュースセンチメント解析（score_news）、銘柄ごとに ai_scores に保存
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュース LLM スコアを合成して日次で 'bull'/'neutral'/'bear' を判定（score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルを含む監査スキーマの初期化（冪等）
  - 監査 DB の初期化ユーティリティ（init_audit_db）
- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で各種設定にアクセス

セットアップ手順
---
前提
- Python 3.9+（typing 機能に依存）
- DuckDB
- OpenAI SDK（openai）
- defusedxml（RSS の安全パース）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

推奨インストール（プロジェクトルートで実行）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）
   - pip install -e .   （パッケージを開発モードでインストールできる場合）

環境変数 / .env
- プロジェクトルートに .env/.env.local を置くと自動的に読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを検出）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（.env の例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  (デフォルト)
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
- SQLITE_PATH=data/monitoring.db
- OPENAI_API_KEY=...  （score_news / score_regime の実行に必要）
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

使い方（代表例）
---

1) 設定オブジェクトにアクセスする
```python
from kabusys.config import settings

# 必須トークンは settings.jquants_refresh_token などで取得
print(settings.duckdb_path)   # Path object
print(settings.is_live)
```

2) DuckDB 接続を作って ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```
- run_daily_etl は calendar → prices → financials → 品質チェック の順で処理します。戻り値は ETLResult オブジェクトです。

3) ニュースのセンチメントスコアを生成する（OpenAI API キー必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # None なら OPENAI_API_KEY を参照
print(f"wrote {n_written} ai_scores")
```

4) 市場レジーム判定を行う
```python
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)  # 結果は market_regime テーブルに書き込まれる
```

5) 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# signal_events, order_requests, executions テーブルが作成されます
```

6) RSS を取得する（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

注意点 / 設計上の方針
- Look-ahead バイアス対策が各モジュールで考慮されています（target_date ベースのウィンドウ計算、DB クエリは date < target_date/排他条件 等）。
- OpenAI 呼び出しは失敗時にフェイルセーフ（スコア 0.0 を採用する等）となるよう設計されています。API キーは OPENAI_API_KEY または関数引数で渡してください。
- J-Quants API はレート制御とリトライを行います。get_id_token はリフレッシュトークンから id_token を取得します。
- RSS 取得は SSRF 対策・最大受信サイズ制限・トラッキングパラメータ除去など安全対策を実装しています。
- DuckDB の executemany に関する互換性（空リスト不可など）を考慮して実装されています。

ディレクトリ構成（主要ファイル）
---
(以下は src/kabusys 配下の主要モジュールと役割の抜粋)

- src/kabusys/
  - __init__.py                - パッケージメタ情報
  - config.py                  - 環境変数 / 設定管理 (settings)
  - ai/
    - __init__.py
    - news_nlp.py              - ニュースセンチメント解析 / score_news
    - regime_detector.py       - 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py        - J-Quants API クライアント（fetch / save 関数）
    - pipeline.py              - ETL パイプライン（run_daily_etl 他）
    - etl.py                   - ETLResult の再エクスポート
    - calendar_management.py   - 市場カレンダー管理・営業日ロジック
    - news_collector.py        - RSS 取得・正規化・保存ユーティリティ
    - stats.py                 - zscore_normalize 等の統計ユーティリティ
    - quality.py               - データ品質チェック（QualityIssue）
    - audit.py                 - 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py       - Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py   - 将来リターン / IC / 統計サマリー
  - research/*                  - 研究用ユーティリティ
  - その他（execution/strategy/monitoring などのサブパッケージが想定される）

開発 / テスト
---
- 自動的に .env が読み込まれるため、テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。
- OpenAI / J-Quants への外部コールを含む箇所はモック化（unittest.mock.patch）して単体テストを行うことを推奨します。モジュール内の _call_openai_api 等はテストで差し替え可能です。
- DuckDB はインメモリ接続（":memory:"）をサポートしているため、単体テストでファイルを作らず簡単にテーブル操作を試せます。

よくある質問（短縮）
---
Q: OpenAI キーはどこで設定しますか？
A: 環境変数 OPENAI_API_KEY を設定するか、score_news/score_regime に api_key 引数を渡します。

Q: .env の自動読み込みを無効にできますか？
A: はい。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: データベースファイルのデフォルト場所は？
A: DUCKDB_PATH は data/kabusys.duckdb、SQLite は data/monitoring.db がデフォルトです（settings で確認・上書き可）。

貢献・拡張
---
- 新しい ETL 対象やニュースソースの追加、モデル（OpenAI）設定の切替、監査スキーマの拡張はモジュールを追加/拡張する形で行えます。API の呼び出しは各モジュールで抽象化されているため、テストや差し替えが容易です。

ライセンスや責任
---
- この README はコードベースの仕様説明を目的としています。実運用での自動売買は法規制や証券会社との契約、十分なテスト・リスク管理が必要です。実運用時は必ず安全対策と監査を行ってください。

付録: 最低限の .env.example（参考）
---
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

以上。必要であれば README に入れるコマンド例や CI / systemd / cron ジョブの設定例、より詳細な API 仕様（関数引数・戻り値の表）も作成できます。どの部分を詳しく載せたいか教えてください。