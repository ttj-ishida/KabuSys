# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームおよび自動売買（リサーチ・ETL・AI・監査）ユーティリティ群を提供する Python パッケージです。J-Quants / kabuステーション / OpenAI と連携してデータ取得、品質チェック、AI によるニュース分析、マーケットレジーム判定、研究用ファクター計算、監査ログ管理などを行います。

主な設計方針:
- ルックアヘッドバイアスを避ける（date.today()/datetime.today() を参照しない実装方針を維持）
- DuckDB を中心としたローカルデータベースで ETL と解析を実行
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON Mode）
- J-Quants API 経由で株価・財務・カレンダーを差分取得（ID トークン自動リフレッシュ、レート制御、リトライ）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を DuckDB に保存

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 設定オブジェクト: `kabusys.config.settings`
- データ ETL（J-Quants）
  - 日次株価（raw_prices）取得・保存（ページネーション・冪等保存）
  - 財務データ取得・保存（raw_financials）
  - 市場カレンダー取得・保存（market_calendar）
  - ETL パイプライン: `kabusys.data.pipeline.run_daily_etl`
- データ品質チェック
  - 欠損データ / スパイク検出 / 重複 / 日付整合性チェック
  - QualityIssue データクラスで検出内容を返す
- ニュース収集 / 前処理
  - RSS 取得（SSRF 対策、サイズ制限、URL 正規化）
  - raw_news / news_symbols の保存補助
- AI（OpenAI）関連
  - ニュースセンチメントで銘柄毎スコアを生成: `kabusys.ai.news_nlp.score_news`
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）: `kabusys.ai.regime_detector.score_regime`
- 研究用ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）: `kabusys.research`
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - 監査スキーマ初期化 / 専用 DB 初期化: `kabusys.data.audit.init_audit_schema` / `init_audit_db`

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントの一部で union 型等を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 代表的な依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml に依存をまとめてください。

3. リポジトリのルートに .env を配置（自動読み込みが有効）
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を起点に行われます。
   - 自動読み込みを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

4. 必要な環境変数（最小例）
   - J-Quants:
     - JQUANTS_REFRESH_TOKEN=<your_refresh_token>
   - kabuステーション:
     - KABU_API_PASSWORD=<your_kabu_password>
     - (任意) KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - Slack（監視等で使用する場合）:
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - OpenAI:
     - OPENAI_API_KEY=<your_openai_api_key>
   - DB パス（任意、デフォルトを使用することも可）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=yourpw
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（サンプル）

以下は Python スクリプトからの利用例です。DuckDB 接続は `duckdb.connect(path)` で作成します。

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定（1321 MA200 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算（例: momentum）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
```

- 監査用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル(signal_events, order_requests, executions) が作成されます
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- OpenAI を使用する関数は API キー（OPENAI_API_KEY または関数の api_key 引数）を必要とします。
- J-Quants 関連は JQUANTS_REFRESH_TOKEN 必須。`jquants_client.get_id_token()` が内部で使います。
- ETL / AI 呼び出しは side-effect（DB 書き込み）があります。バックテスト等で使用する際は注意してください。

---

## ディレクトリ構成

リポジトリ（要点）の概観:

- src/
  - kabusys/
    - __init__.py  (バージョン: 0.1.0)
    - config.py  (環境変数読み込み・Settings)
    - ai/
      - __init__.py
      - news_nlp.py  (ニュースセンチメント → ai_scores)
      - regime_detector.py  (市場レジーム判定)
    - data/
      - __init__.py
      - calendar_management.py  (市場カレンダー管理 / 営業日判定)
      - etl.py  (ETL インターフェース再エクスポート)
      - pipeline.py  (日次 ETL パイプライン実装)
      - stats.py  (z-score 等統計ユーティリティ)
      - quality.py  (データ品質チェック)
      - audit.py  (監査ログスキーマ・初期化)
      - jquants_client.py  (J-Quants API クライアント & 保存処理)
      - news_collector.py  (RSS 収集・前処理)
    - research/
      - __init__.py
      - factor_research.py  (モメンタム/ボラティリティ/バリュー)
      - feature_exploration.py (forward_returns, IC, summary, rank)
    - other top-level modules: strategy, execution, monitoring (公開配列に含まれるが実装は別ファイル群)

上記ファイルのうち主要な処理は data/ と ai/、research/ にまとまっています。

---

## 開発・テスト時の注意点

- 自動 .env 読み込み:
  - パッケージは起動時にプロジェクトルートを検出して `.env` / `.env.local` を自動的に読み込みます。テストでこれを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB executemany の制約:
  - 一部実装で DuckDB 0.10 の executemany の空リスト制約に対応するため、空チェックが実装されています。DuckDB バージョンに依存する挙動に注意してください。
- OpenAI 呼び出し:
  - ニュース系は gpt-4o-mini（JSON Mode）を使用する想定です。API のレスポンス破損やタイムアウトに備えたリトライとフォールバック（スコア=0）を実装しています。
- J-Quants:
  - レート制限（120 req/min）をモジュール内で制御しています。ID トークンは自動リフレッシュされます（401 時に一回リトライ）。
- セキュリティ:
  - RSS フェッチは SSRF 対策、gzip サイズ制限、defusedxml を使用した XML パースなど安全対策が組み込まれています。

---

## トラブルシューティング

- 環境変数が見つからない:
  - `kabusys.config._require` が未設定の必須キーで ValueError を出します。.env.example を参考に .env を作成してください。
- OpenAI 呼び出しで失敗する:
  - APIキーの確認、クォータ、ネットワーク。失敗時は多くの関数でフォールバック（0 やスキップ）により継続しますが、ログを確認してください。
- J-Quants API エラー:
  - トークン期限切れ、ネットワーク、またはレート制限が原因です。ログおよびエラーメッセージを確認してください。

---

## 参考

- 主要エントリポイント:
  - ETL: `kabusys.data.pipeline.run_daily_etl`
  - ニュース AI: `kabusys.ai.news_nlp.score_news`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime`
  - 監査 DB 初期化: `kabusys.data.audit.init_audit_db`

ご不明点や README に追加してほしいサンプル（CLI 実行例や systemd / cron の設定例など）があれば教えてください。