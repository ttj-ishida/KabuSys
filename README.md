# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI 利用）による銘柄センチメント算出、ファクター計算・リサーチユーティリティ、監査ログ（発注〜約定トレーサビリティ）などを含みます。

主な設計方針：
- DuckDB を中心としたローカルデータプラットフォーム
- Look‑ahead バイアス対策（内部処理で現在時刻を直接参照しない設計）
- API 呼び出しに対する堅牢なリトライ / フェイルセーフ
- 冪等性（DB 書き込みは ON CONFLICT を使用）とトレーサビリティ重視

---

## 機能一覧

- 設定管理
  - .env からの自動読み込み（プロジェクトルート検出）と必須設定チェック
- データ ETL（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得・保存
  - レートリミット制御、トークン自動リフレッシュ、ページネーション対応
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF/サイズ制限等のセキュリティ考慮
- ニュース NLP / AI
  - 銘柄別ニュースを OpenAI（gpt-4o-mini）でスコア化して ai_scores に保存（score_news）
  - マクロニュース + ETF MA 乖離を組み合わせた市場レジーム判定（score_regime）
  - JSON mode を使った堅牢な応答パース、リトライ・フォールバック処理
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化、統計サマリー
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付整合性チェック
- カレンダー管理
  - market_calendar を参照した営業日判定 / next/prev_trading_day 等
  - JPX カレンダー差分更新ジョブ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の DDL 定義と初期化ユーティリティ
  - 発注から約定までの UUID ベースのトレース設計

---

## 必要環境 / 依存

- Python 3.10 以上（PEP 604 の union 型（|）を使用）
- 主な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース）

実際のインストールはプロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。最低限の手動インストール例:

pip install duckdb openai defusedxml

（パッケージ名やバージョンは運用環境に合わせて固定してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存インストール
   - pip install -r requirements.txt
   - または最小: pip install duckdb openai defusedxml

3. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（少なくとも実運用で必要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注等を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

OpenAI 関連:
- OPENAI_API_KEY — score_news / score_regime が使用する場合に必要（関数呼び出し時に api_key を直接渡すことも可能）

設定ファイルの例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid
```

4. データディレクトリ作成（必要に応じて）
```
mkdir -p data
```

---

## 使い方（主なユースケース）

以下はモジュール API を使った簡単な例です。すべての関数は DuckDB の接続オブジェクト（duckdb.connect(...) の返り値）を受け取ります。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（ai スコア）を生成する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```

- 市場レジームスコアを計算する
```python
from kabusys.ai.regime_detector import score_regime
# conn は DuckDB 接続、target_date は判定したい日
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査 DB 初期化（監査ログ専用）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って監査テーブルにアクセス
```

- カレンダー判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026,3,20)))
print(next_trading_day(conn, date(2026,3,20)))
```

備考:
- OpenAI 呼び出しは API キーを引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- score_news / score_regime は外部 API に依存するため、ネットワーク・料金・レート制限に注意してください。
- ETL / 保存処理は冪等性を考慮して実装されており、部分的な再実行に耐える設計です。

---

## ディレクトリ構成（抜粋）

プロジェクトソースは `src/kabusys` 配下にあります。主なモジュールは以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント / 保存関数
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETL 公開インターフェース（ETLResult 再エクスポート）
    - calendar_management.py     — 市場カレンダー管理 / is_trading_day 等
    - news_collector.py          — RSS 収集・前処理
    - quality.py                 — データ品質チェック
    - stats.py                   — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログの DDL と初期化
  - research/
    - __init__.py
    - factor_research.py         — momentum/volatility/value の計算
    - feature_exploration.py     — forward returns, IC, summary
  - ai/, data/, research/ はそれぞれ公開関数を __all__ で整理

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 運用上の注意

- API キー管理は厳格に行ってください（特に OpenAI / J-Quants のキー）。
- OpenAI に送るプロンプトやバッチサイズはコストとレート制限に注意して調整してください（news_nlp はデフォルトで 20 銘柄バッチ）。
- DuckDB ファイルはバックアップを検討してください。監査ログは削除しない前提の設計です。
- news_collector では SSRF 対策やサイズ制限を実装していますが、RSS ソースの追加時は信頼性を確認してください。
- 自動ロードされる .env はプロジェクトルートの .git または pyproject.toml を基準に検出します。CI やテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと明示的に制御できます。

---

## 開発 / 貢献

- 単体テスト・モック用に各種内部呼び出し（例: OpenAI 呼び出し）を差し替えやすい設計になっています。
- プルリクエスト時は新しい外部依存や設定項目を README とドキュメントに追記してください。

---

README に記載のない細かい API 仕様や追加ユーティリティについては、各モジュールの docstring（ソース内のコメント）を参照してください。必要であれば、特定の機能についての使い方例やサンプルスクリプトを追加で用意します。