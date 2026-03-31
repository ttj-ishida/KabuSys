# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
DuckDB をデータ層に用い、J-Quants / RSS / OpenAI 等の外部サービスと連携して以下を提供します：

- 日次 ETL（株価・財務・市場カレンダー）の差分取得・保存・品質チェック
- ニュース収集（RSS）と銘柄別 NLP スコアリング（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索ユーティリティ
- 発注監査ログ用スキーマ（監査トレース、冪等化）
- J-Quants API クライアント（取得・保存・リトライ・レート制御）

この README はソースツリー（src/kabusys 以下）を元に機能・セットアップ・使用方法・ディレクトリ構成を説明します。

主要機能
- ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
- データ品質チェック: 欠損・スパイク・重複・日付不整合（kabusys.data.quality）
- ニュース収集: RSS 取得・正規化・SSRF 対策・前処理（kabusys.data.news_collector）
- ニュースNLP: 銘柄単位のセンチメントスコアを OpenAI で算出し ai_scores に保存（kabusys.ai.news_nlp）
- 市場レジーム判定: ETF(1321)のMA乖離とマクロニュースを合成して 'bull'/'neutral'/'bear' を判定（kabusys.ai.regime_detector）
- ファクター計算・探索: momentum/value/volatility 等（kabusys.research）
- 統計ユーティリティ: zscore 正規化など（kabusys.data.stats）
- J-Quants クライアント: データ取得・保存・ページネーション・トークン自動リフレッシュ（kabusys.data.jquants_client）
- 監査ログスキーマ初期化: audit テーブル群の作成・インデックス設定（kabusys.data.audit）

セットアップ手順（開発環境）
1. Python 3.10+ を用意してください。
2. 仮想環境を作成・有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクト化されている場合）pip install -e .

   主な依存候補:
   - duckdb
   - openai
   - defusedxml

4. 環境変数／.env の準備
   リポジトリルート（.git または pyproject.toml がある親ディレクトリ）に .env を置くと自動で読み込まれます（.env.local があればそちらが優先で上書き）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の環境変数（Settings による）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabu API パスワード（kabuステーション連携）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知対象チャンネル ID

その他の設定（任意／デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動読み込みを抑制
- OPENAI_API_KEY: OpenAI 呼び出しに使うキー（score_news/score_regime は引数でも受け取れます）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視系 SQLite（デフォルト data/monitoring.db）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）

サンプル .env（例）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（主要 API の例）
- DuckDB 接続の作成と ETL 実行例
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# 日次 ETL を実行（target_date を指定しなければ今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア計算（OpenAI API キーを環境変数に設定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores に書き込む
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査ログを書き込む
```

- 研究用途（ファクター計算 / IC 等）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

設計上の注意点・テスト容易性
- 多くの外部呼び出し（OpenAI, J-Quants, HTTP）は呼び出し時にキーを引数注入可能で、ユニットテスト時にモック差替えが容易です。
- ETL / データ取得は差分取得・バックフィル挙動を持ち、look-ahead bias を避けるため target_date 未満のデータしか使わない実装方針です。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われます。パッケージ配布後も CWD に依存せず正しく動作することを意図しています。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義（JQUANTS_REFRESH_TOKEN 等）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメントスコア（OpenAI ベース）
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存 / レート制御）
    - pipeline.py            — ETL パイプラインと run_daily_etl エントリ
    - etl.py                 — ETLResult の公開
    - news_collector.py      — RSS 取得・正規化・SSRF 対策
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - audit.py               — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — momentum/volatility/value の計算
    - feature_exploration.py — forward returns / IC / summary / rank 等

ライセンス・貢献
- 本 README はコード内の実装を説明するドキュメントです。実際のライセンス情報（LICENSE ファイル）がプロジェクトに含まれている場合はそちらを参照してください。
- 貢献（バグ報告・プルリクエスト）はリポジトリの Issue / PR フローに従ってください。

付録：よくある実行上のトラブルと対処
- OpenAI 呼び出しで失敗する
  - OPENAI_API_KEY が正しく設定されているか確認。テストは score_news/score_regime に api_key を直接渡して行うと再現しやすい。
  - ネットワーク障害や rate-limit 時は内部でリトライ・フォールバック（0.0）を行う設計なのでログを確認してください。
- J-Quants API で 401 が返る
  - settings.jquants_refresh_token を確認。jquants_client は 401 を検知するとトークンを自動リフレッシュして再試行します。
- .env が読まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。またプロジェクトルート判定は .git または pyproject.toml を探索するため、.env の置き場所を確認してください。

質問や README の補足情報（例: 具体的な .sql スキーマ、より詳細な ETL 運用手順、監査テーブルのクエリ例など）が必要であれば教えてください。必要に応じて追記・サンプルコードを追加します。