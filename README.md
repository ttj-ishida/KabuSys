# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュースNLP、レジーム判定、研究用ファクター計算、監査ログなどのモジュール群を提供します。

主な設計方針として「ルックアヘッドバイアスの防止」「DuckDB を用いたローカルデータレイク」「外部 API 呼び出しのフェイルセーフ化」「冪等性」を重視しています。

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価（日次 OHLCV）・財務データ・JPX カレンダーの差分取得、DuckDB への冪等保存（pipeline / jquants_client）
  - 日次 ETL パイプライン（run_daily_etl）によりカレンダー→株価→財務→品質チェックを一括実行

- データ品質チェック（quality）
  - 欠損（OHLC）検出、前日比スパイク検出、主キー重複検出、日付不整合検出

- ニュース収集（news_collector）
  - RSS フィード取得、前処理、SSRF 対策、raw_news テーブルへの冪等保存

- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出（ai_scores への書き込み）
  - バッチ・トークン制限対策、レスポンス検証、リトライ実装

- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム判定（bull/neutral/bear）

- 研究用ユーティリティ（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）、将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化

- 監査ログ（data.audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用テーブル定義、初期化ユーティリティ（DuckDB）

- その他ユーティリティ
  - 環境変数管理（config）、データ統計ユーティリティ（data.stats）など

---

## 動作要件（想定）

- Python 3.10+
- 主要依存パッケージ（プロジェクトの requirements.txt を用意している場合はそちらを参照してくださいが、最低限）:
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API / OpenAI / RSS ソース へのアクセス）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、src 配下をパッケージとして使えるようにする（推奨: editable install）

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -e ".[dev]"     # または最低限の依存を個別にインストール
   ```

   必要なパッケージの例:
   ```
   pip install duckdb openai defusedxml
   ```

2. .env ファイルをプロジェクトルートに配置（config モジュールが自動で読み込みます）
   - 自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます
   - テスト等で自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. DuckDB データベースなどのディレクトリを作成（必要に応じて）
   - デフォルトでは data/kabusys.duckdb、data/monitoring.db を使用します（環境変数で変更可）

---

## 必須 / 推奨 環境変数（.env 例）

アプリケーション設定は環境変数から読み込まれます。以下は主要なキー例です（必須は . に示す）。

例 (.env):
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI（省略可: 各関数呼び出しで api_key を渡すことも可能）
OPENAI_API_KEY=your_openai_api_key

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_channel_id

# DB / ファイルパス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid

# 実行環境 / ログ
KABUSYS_ENV=development        # development | paper_trading | live
LOG_LEVEL=INFO
```

- config.Settings は必須キーを `_require` で検証します（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動 .env ロードを無効化できます。

---

## 使い方（代表的な呼び出し例）

以下は Python REPL / スクリプトからの利用例です。各例で DuckDB 接続オブジェクト（duckdb.connect(...) の戻り値）を渡します。

- 日次 ETL を実行（run_daily_etl）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（score_news）
  - OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

- 市場レジームの算出（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB の初期化（init_audit_db）

```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duck.db")
# テーブル作成済みの conn が戻る
```

- 研究用ファクター計算（例: モメンタム）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト
```

注意:
- OpenAI 呼び出しは gpt-4o-mini を指定しており、API 呼び出しの失敗時はフェイルセーフ（デフォルトスコア 0）で継続する実装です。
- J-Quants API にはレート制限と認証トークンのリフレッシュ処理があります。get_id_token / fetch_* 関数を利用してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（今回のコードベースより抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数読み取り・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュースNLP スコアリング（OpenAI）
    - regime_detector.py                — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py            — 市場カレンダー管理、営業日ユーティリティ
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - etl.py                            — ETL 型の再公開（ETLResult）
    - stats.py                          — 統計ユーティリティ（zscore_normalize）
    - quality.py                        — データ品質チェック
    - audit.py                          — 監査ログ（DDL / init）
    - jquants_client.py                 — J-Quants API クライアント（fetch/save）
    - news_collector.py                 — RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py                — ファクター計算（momentum/value/volatility）
    - feature_exploration.py            — 将来リターン / IC / 統計サマリ等
  - research/*（上に示したファイル）
  - ai/*（上に示したファイル）

（プロジェクト全体のファイルは状況により異なります。ここでは提供されたコードを基に主要モジュールを列挙しています。）

---

## 運用上の注意 / ベストプラクティス

- API キー・認証情報は必ず安全に管理し、公開リポジトリや CI のログに含めないでください。
- J-Quants / OpenAI のレート制限、課金設定、利用規約を確認してください。
- ETL 実行・AI スコア処理は外部 API に依存するため、ジョブ実行時にはログとリトライを監視してください。
- DuckDB ファイルは定期バックアップを推奨します。監査ログは消さない想定です。
- バックテストでライブラリを利用する際は「ルックアヘッドバイアス防止」の実装ポリシー（target_date 未満のデータのみ使用する等）に注意して下さい。

---

## トラブルシューティング

- 環境変数が見つからない:
  - settings のプロパティは未設定時に ValueError を投げます。必要なキーを .env に設定するか、環境変数としてエクスポートしてください。
  - 自動 .env 読み込みを無効化していると .env は読み込まれません（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

- OpenAI / J-Quants API 呼び出しでタイムアウト・レート制限:
  - モジュールはリトライ・指数バックオフを備えていますが、長時間失敗する場合は API キーやネットワーク、レート制限状況を確認してください。

- DuckDB に関するエラー:
  - executemany に空リストを渡すとエラーになるバージョン対策を実装していますが、古い/特殊なバージョンを使用している場合は互換性をご確認ください。

---

## 貢献 / 拡張

- 新しいデータソースの追加、ニュースソースの拡張、戦略モジュール（strategy）や実行・監視（execution / monitoring）モジュールの実装を歓迎します。
- 単体テスト・統合テストの追加、CI での DB 初期化・モックを用いた外部 API のエミュレーションを推奨します。

---

もし README に含めたい追加情報（例: 実行スクリプト、systemd ユニット、具体的な .env.example ファイル内容、依存関係の完全なリスト等）があれば教えてください。必要に応じて追記・整形します。