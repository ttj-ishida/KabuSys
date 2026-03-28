# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）→ ETL → 品質チェック → 研究（ファクター計算）→ AI ニュース解析 → 監査ログ といった一連の機能を提供します。

主に DuckDB を内部データベースとして利用し、OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価や市場レジーム判定もサポートします。

---

## 主な特徴（ハイライト）

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場情報、JPXカレンダー等の差分取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
  - 品質チェック：欠損、スパイク、重複、日付不整合など
- ニュース収集
  - RSS フィードからの安全な収集（SSRF対策、トラッキングパラメータ除去、gzip対応、XML安全パーサ）
  - raw_news / news_symbols テーブルへ冪等保存
- AI ベースの NLP
  - 銘柄単位のニュースセンチメント評価（news_nlp.score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成 -> regime_detector.score_regime）
  - OpenAI API 呼び出しに対するリトライ/フォールバック実装
- 研究（Research）向けユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - シグナル -> 発注 -> 約定までトレース可能な監査スキーマの初期化・ユーティリティ（DuckDB）
  - 冪等キー、ステータス管理、UTC タイムスタンプ
- 設定管理
  - .env と OS 環境変数の読み込みサポート（自動ロード、.env.local 優先等）
  - 必須設定は Settings オブジェクト経由で取得（kabusys.config.settings）

設計上の注意点：
- ルックアヘッド・バイアス回避のため、内部処理は date 引数に依存し、 datetime.today()/date.today() に依存しない設計を意識しています（ETL / AI モジュール等）。
- DB 書き込みは可能な限り冪等に実装（ON CONFLICT 等）しています。

---

## 必要環境・依存

- Python 3.10+
- 主な依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

（実際のプロジェクト配布時は pyproject.toml / requirements.txt を参照してください）

---

## 環境変数（重要）

以下は最低限設定が必要／よく使われる環境変数です：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（実行モジュールから参照）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG | INFO | ...）（デフォルト: INFO）

自動的に .env と .env.local をプロジェクトルートから探索して読み込みます（OS 環境変数が優先）。自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡単な .env.example（README 用サンプル）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - またはプロジェクトに pyproject.toml があれば:
     - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、OS 環境変数に設定
   - 上記の必須変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定してください

5. データディレクトリ作成
   - mkdir -p data

備考:
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索します。
- テスト実行時に自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（主な API の例）

以下は最小限の使用例です。各関数は duckdb の接続オブジェクト（duckdb.connect() の返り値）を受け取ります。

1) DuckDB に接続して日次 ETL を実行する
```
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントをスコアリングする（OpenAI API 必要）
```
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {n_written}")
```

3) 市場レジーム判定を行う
```
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DuckDB 初期化
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

5) 研究用ファクター計算例
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

---

## 注意点・実装ノート

- Look-ahead バイアス対策:
  - 多くの処理（news_nlp, regime_detector, pipeline 等）は target_date を明示的に受け取り、対象データは target_date 未満／前後の範囲で制御することで将来情報の参照を防いでいます。
- 冪等性:
  - J-Quants データ保存関数は ON CONFLICT / DO UPDATE を用いて冪等性を確保します。
- リトライ / フォールバック:
  - OpenAI 呼び出しや J-Quants API 呼び出しはリトライと指数バックオフを実装。API 失敗時でも処理継続するフェイルセーフ設計の箇所があります（例: マクロセンチメントが取得できない場合は 0.0）。
- テスト用フック:
  - 一部の内部呼び出し（例: kabusys.ai.news_nlp._call_openai_api、kabusys.data.news_collector._urlopen 等）は unittest.mock.patch で差し替え可能です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント（OpenAI）
    - regime_detector.py          — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント & 保存ロジック
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETLResult 再エクスポート
    - calendar_management.py      — マーケットカレンダー管理 / 営業日ロジック
    - news_collector.py           — RSS ニュース収集・前処理
    - quality.py                  — データ品質チェック
    - stats.py                    — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                    — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py          — モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py      — 将来リターン / IC / 統計サマリー

（プロジェクトルート）
- pyproject.toml (期待)
- .env, .env.local （任意）
- data/ （デフォルトデータ格納場所）

---

## よくある運用コマンド / ジョブ例

- 日次 ETL（cron / Airflow 等で実行）
  - Python スクリプトで run_daily_etl を呼ぶ（上記サンプル参照）
- 夜間カレンダー更新のみ
  - data.calendar_management.calendar_update_job(conn)
- 定期ニュース収集
  - news_collector.fetch_rss(...) を複数のソースで実行し raw_news に保存
- OpenAI を使った定期スコアリング
  - news_nlp.score_news を毎朝実行 → ai_scores を更新
  - regime_detector.score_regime を毎営業日判定

---

## 補足・貢献

- バグ報告・機能追加は Issue を立ててください。
- 実運用に組み込む際は、秘密情報（API トークン等）の管理と rate limit（J-Quants, OpenAI）に注意してください。
- DuckDB ファイルのバックアップ、監査ログ（audit DB）運用ポリシーを事前に検討してください。

---

README に記載したサンプルはライブラリの公開された API に基づく簡易例です。実運用ではロギング設定、エラーハンドリング、リソース管理（接続のクローズ等）を適切に行ってください。