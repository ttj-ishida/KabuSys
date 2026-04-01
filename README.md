# KabuSys

KabuSys は日本株のデータ取得・解析・自動売買を支援するライブラリ群です。J-Quants や RSS からのデータ収集、DuckDB を用いたデータ基盤、AI（OpenAI）を用いたニュースセンチメント評価、リサーチ用ファクター計算、監査ログ（発注 → 約定の追跡）などを含みます。

主な用途
- 日次 ETL（株価・財務・市場カレンダー）パイプライン
- ニュースの NLP による銘柄別センチメント算出
- マクロニュースと ETF（1321）MA200 を合成した市場レジーム判定
- ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログ用の DuckDB スキーマ初期化・管理

---

## 機能一覧

- data/
  - jquants_client: J-Quants API 対応クライアント（ページネーション・レート制御・リトライ・保存処理）
  - pipeline / etl: 日次 ETL 実行（差分取得、バックフィル、品質チェック）
  - news_collector: RSS 収集と raw_news 保存（SSRF/サイズ/トラッキング対策）
  - calendar_management: JPX カレンダー管理・営業日演算
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - audit: 発注・約定の監査テーブル作成と DB 初期化ユーティリティ
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI へ投げて ai_scores に保存
  - regime_detector.score_regime: ETF(1321) MA200 乖離とマクロニュースセンチメントの合成で市場レジーム判定
- research/
  - factor_research: momentum / volatility / value 等の定量ファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等
- config:
  - 環境変数の管理（.env 自動ロード、必須項目チェック、便利な Path プロパティ）

設計方針の一部
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() を直接参照しない設計（ターゲット日を引数で与える）。
- API 呼び出しはリトライやフォールバックを備え、フェイルセーフな挙動。
- DuckDB を永続層に用い、冪等保存（ON CONFLICT）を考慮。

---

## 要件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ

具体的な依存はプロジェクトの pyproject.toml / requirements.txt を参照してください（本コードスニペットには同梱されていません）。

---

## セットアップ手順

1. リポジトリをクローン／取得
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install duckdb openai defusedxml
   - （実際のプロジェクトでは pyproject.toml / requirements.txt を使用）
4. 環境変数を設定（.env ファイル推奨）

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（実行・発注関連）
- SLACK_BOT_TOKEN: Slack Bot トークン（通知用）
- SLACK_CHANNEL_ID: Slack 通知チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必要）

任意（デフォルト有り）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_ENV: development / paper_trading / live

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、.env → .env.local の順で読み込みます。
- 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=secret_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=./data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

## 使い方（基本例）

準備: DuckDB 接続と settings
```python
from datetime import date
import duckdb
from kabusys.config import settings

# DuckDB ファイルに接続（settings.duckdb_path は pathlib.Path）
conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を明示して実行（省略時は today）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメントを算出して ai_scores に保存する
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは環境変数 OPENAI_API_KEY で渡すか、api_key 引数で指定可能
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n}")
```

市場レジーム（ETF 1321 MA200 とマクロニュース）を判定して market_regime テーブルに保存
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログ用 DB の初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで監査テーブル（signal_events, order_requests, executions）が作成されます
```

ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
records = calc_momentum(conn, date(2026, 3, 20))
# records は各銘柄ごとの辞書リスト（mom_1m, mom_3m, mom_6m, ma200_dev など）
```

ログレベルや実行環境
- LOG_LEVEL 環境変数でログレベルを設定できます。
- KABUSYS_ENV (development / paper_trading / live) によって挙動分岐がある箇所があります（主に安全設定）。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py : パッケージ初期化（version 等）
  - config.py : 環境変数読み込み・Settings クラス（必須項目チェック・Path プロパティ）
  - ai/
    - __init__.py
    - news_nlp.py : ニュースセンチメント解析と ai_scores 保存ロジック（OpenAI 呼び出し・バッチ処理・検証）
    - regime_detector.py : ETF 1321 MA200 とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py : ETL パイプライン（run_daily_etl, run_prices_etl, ...）
    - etl.py : ETLResult の公開再エクスポート
    - news_collector.py : RSS 収集と raw_news 保存（SSRF/サイズ/正規化対策）
    - calendar_management.py : 市場カレンダー管理と営業日演算
    - quality.py : データ品質チェック群
    - stats.py : Zスコアなどの統計ユーティリティ
    - audit.py : 監査ログスキーマ定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py : Momentum / Volatility / Value の計算
    - feature_exploration.py : 将来リターン計算、IC、統計サマリーなど

---

## 設計上の注意点 / トラブルシューティング

- 多くの関数は target_date を引数に取ります。内部で現在時刻を参照しないため、バックテストや再現性のある処理が可能です。
- OpenAI や J-Quants の API キーが未設定だと ValueError が発生します。エラーメッセージを参照して環境変数を確認してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI やテストで自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB による executemany の扱い等、メソッド内に DuckDB バージョン依存の注意点があります（空リストを渡せない等）。ETL 実行前に接続とテーブルスキーマの整合性を確認してください。
- news_collector は RSS のパースや外部 URL を扱うため、ネットワークや XML の不正な入力に対する防御（defusedxml、SSRF チェック、受信サイズ制限）を行っています。例外や警告はログに出力されます。

---

## 開発・貢献

- コードは機能ごとにモジュール化されています。ユニットテストは外部 API 呼び出しをモックすることを推奨します（例: news_nlp._call_openai_api のパッチなど）。
- リトライやレート制御は既に組み込まれていますが、実行環境・API 仕様変更に合わせて閾値・リトライポリシーを調整してください。

---

必要なら README に例示する SQL スキーマや追加の運用手順（cron / systemd の実行例、Slack 通知の使い方、発注フローの利用方法）も追記できます。追加したい項目があれば教えてください。