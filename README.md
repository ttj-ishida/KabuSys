# KabuSys — 日本株自動売買システム（README）

このドキュメントは、提供されたコードベース（src/kabusys）に基づく README.md です。プロジェクトの概要、主要機能、セットアップ手順、使い方（主要ユースケースのサンプル）、およびディレクトリ構成を日本語でまとめています。

注意：本リポジトリには外部 API（J-Quants / OpenAI / kabuステーション 等）へのアクセスを伴う処理が含まれます。実運用やバックテストで用いる際は、API キーの管理や実行環境の安全性（テスト環境と本番環境の分離）に十分ご注意ください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必須環境変数
- セットアップ手順
- 使い方（サンプル）
  - 環境変数の読み込み
  - ETL（データパイプライン）実行
  - ニュースセンチメントスコア（AI）
  - 市場レジーム判定（AI + ETF MA）
  - 監査ログ（監査DB）初期化
- ディレクトリ構成（主要ファイルの説明）
- 開発上の注意点 / 補足

---

プロジェクト概要
- KabuSys は日本株を対象としたデータプラットフォームと自動売買基盤の骨組みを提供します。
- 主に以下の機能を持ちます：
  - J-Quants API からの株価・財務・カレンダー等データの差分取得（ETL）
  - ニュース収集（RSS）と OpenAI を用いた銘柄センチメントの算出（AI スコア）
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを組み合わせた市場レジーム判定
  - データ品質チェック、マーケットカレンダー管理、監査ログ（注文 → 約定のトレーサビリティ）
  - 研究用ユーティリティ（ファクター計算、将来リターン計算、IC 計算、Z スコア正規化）

---

主な機能一覧
- data.jquants_client: J-Quants API 呼び出し、ページネーション、リトライ、DuckDB への冪等保存
- data.pipeline: 日次 ETL（カレンダー／価格／財務）と品質チェックの統合フロー
- data.news_collector: RSS 取得、前処理、SSRF 対策、raw_news への保存ロジック
- data.calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
- data.quality: 欠損・スパイク・重複・日付不整合チェック
- data.audit: 監査ログ（signal_events / order_requests / executions）テーブル定義と初期化
- ai.news_nlp: OpenAI を用いた銘柄別ニュースセンチメント算出（gpt-4o-mini・JSON モード）
- ai.regime_detector: ETF MA とマクロニュース（LLM）を合成して日次市場レジーム判定
- research: ファクター計算（momentum / value / volatility）および特徴量探索ユーティリティ
- config: .env 自動読み込み、環境変数ラッパー（settings オブジェクト）

---

必須環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（モニタリング等）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（AI モジュールが必要な場合）
- 環境派生設定:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DB パス（任意、デフォルトは下記）
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)

.env の自動読込:
- パッケージ内 config モジュールはプロジェクトルート（.git または pyproject.toml を探す）を起点に自動で .env → .env.local を読み込みます。
- 読込優先順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用途等）。

---

セットアップ手順（ローカル開発向け）
1. Python バージョン
   - Python 3.10+ を推奨（型注釈で | を利用しているため 3.10 以上が望ましい）。

2. リポジトリをクローンしてパッケージをインストール
   - 例:
     ```bash
     git clone <repo-url>
     cd <repo>
     pip install -e .
     ```
   - 依存パッケージ（最小例）:
     - duckdb
     - openai
     - defusedxml
     - （必要に応じて）slack-sdk 等

   - 直接インストール例:
     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数の用意
   - プロジェクトルートに .env（または .env.local）を作成して上記必須環境変数を設定します。
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=secret
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     ```

4. DuckDB ファイルの格納先ディレクトリ作成（必要時）
   - デフォルトでは data/kabusys.duckdb を使用します。存在しない場合は自動で作成する関数もありますが、事前にディレクトリを作っておくと安心です。

---

使い方（例）

- 事前準備:
  - 必須環境変数を設定しておく（上記参照）。
  - Python から duckdb を使える状態にしておく。

1) settings（環境変数）の利用例
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

2) DuckDB 接続を作って ETL を実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```
- run_daily_etl は market calendar → prices → financials → 品質チェック の順で処理します。
- エラーが生じても個々のステップは捕捉され、ETLResult に集約されます。

3) ニュースセンチメント（AI）スコア計算
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で読込
print(f"書き込んだ銘柄数: {n_written}")
```
- score_news は raw_news / news_symbols テーブルを使って銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）で JSON 返却を期待してスコアを算出します。
- API 呼び出し失敗時はフェイルセーフでスコアをスキップし続行します。

4) 市場レジーム判定（ETF MA + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で読込
print("完了:", res)
```
- ETF（1321）200日移動平均乖離とマクロニュースセントメントを合成して market_regime テーブルへ冪等書き込みします。

5) 監査DB（監査ログ）初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリが無ければ作成されます
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

6) ニュース RSS の取得（単体テスト用途）
- news_collector.fetch_rss を使って RSS の記事リストを取得できます（SSRF 対策・サイズチェック付き）。
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

---

ディレクトリ構成（主要ファイル・モジュールと短い説明）
- src/kabusys/
  - __init__.py
  - config.py
    - .env 読み込み、settings オブジェクト（環境設定の一元管理）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄別に集約し OpenAI でセンチメントを算出 → ai_scores に書き込む
    - regime_detector.py
      - ETF 1321 の MA 乖離 + マクロニュースセンチメントで市場レジーム判定 → market_regime に書込
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント／保存ロジック（rate limit / retry / token refresh）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py
      - pipeline.ETLResult の再エクスポート
    - news_collector.py
      - RSS 収集、前処理、SSRF 対策
    - calendar_management.py
      - market_calendar の管理と営業日ユーティリティ
    - stats.py
      - zscore_normalize 等の統計ユーティリティ（research でも利用）
    - quality.py
      - 欠損・スパイク・重複・日付不整合チェック
    - audit.py
      - 監査ログスキーマ定義と初期化ロジック
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / バリュー / ボラティリティ等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC 計算、統計サマリー、ランク関数
  - （注）パッケージ __all__ では "strategy", "execution", "monitoring" を公開対象に含めていますが、ここに示されたソース一覧にはそれらの実装が含まれていません（将来的な拡張または別ファイルに存在する想定）。

---

開発上の注意点 / 補足
- Look-ahead bias 対策:
  - 多くの関数は datetime.today()/date.today() を直接参照せず、明示的な target_date を受け取る設計になっています（バックテストで正しく取り扱うため）。
- DuckDB 互換性:
  - DuckDB の executemany の挙動や配列バインドの差異に注意して実装済み（空リストの扱い等）。
- OpenAI / J-Quants 呼び出し:
  - 再試行・バックオフ・5xx/429 の扱いなど堅牢化されている一方で、API キーの取得・設定は利用者側で適切に管理してください。
- テストとモック:
  - ai モジュール内の _call_openai_api などは unittest.mock.patch により差し替え可能に設計されています。単体テストで実際の API にアクセスしないようにすることを推奨します。
- .env 読込:
  - プロジェクトルートの特定は __file__ の親ディレクトリ探索により行うので、CWD に依存しません。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動ロードを無効化できます。

---

以上が本コードベースの README.md（日本語）です。必要であれば、
- 具体的な SQL スキーマ（raw_prices / raw_news / ai_scores / market_regime など）の完全定義を README に追記、
- 実行例（cron / systemd / docker-compose）や CI 用のテスト実行手順を追加、
- セキュリティ（シークレット管理）や運用監視の章を追加
といった補完も可能です。どの情報を追加したいか教えてください。