# KabuSys

日本株向けのデータプラットフォーム & 自動売買リサーチ基盤のミニマル実装です。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 主要機能（概要）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務、上場情報、JPX カレンダーを差分取得して DuckDB に保存
  - 差分更新・バックフィル・ページネーション・再試行・レート制御を備える
- ニュース収集
  - RSS 取得、URL 正規化、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF / gzip / XML 攻撃対策を考慮
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメントを LLM（gpt-4o-mini）でスコア化し ai_scores へ書き込み
  - トークン過大対策、バッチ処理、堅牢なレスポンス検証とリトライ
- 市場レジーム判定
  - ETF（1321）の 200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジームを判定
- 研究用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算、将来リターン、IC・統計サマリー、Z スコア正規化
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック、QualityIssue を返す
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義、初期化用ユーティリティ（DuckDB）
  - 発注の冪等性とトレーサビリティを保証する設計

---

## 必要条件・依存関係

- Python 3.10+
- 主な依存パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス:
  - J-Quants API（データ取得）
  - OpenAI（ニュース NLP / レジーム判定）
  - RSS ソース（ニュース収集）

（プロジェクトに requirements.txt がある場合はそれに従ってください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージとして提供していれば:
# pip install -e .
```

---

## 環境変数（主要）

アプリ設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動ロードされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

重要なキー（.env.example を作成してください）:

- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime に未指定時に参照）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV           : development / paper_trading / live （デフォルト: development）
- LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL

注意:
- 設定値が未設定の場合、Settings プロパティは ValueError を投げる設計の項目があります（必須キー）。

---

## セットアップ手順（手引き）

1. リポジトリをクローンして仮想環境を作る
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # プロジェクトで requirements.txt や pyproject を提供していればそちらを利用
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を設定してください。
   - 例 `.env`（テンプレート）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_key
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB の準備（任意）
   - デフォルトでは data/kabusys.duckdb を使用します。初回は ETL 実行時にテーブルがなければ作成処理を実行するユーティリティを用意してください（スキーマ初期化関数等）。

---

## 使い方（主なエントリポイント・コード例）

以下は簡単な Python からの利用例です。必要に応じて適切な接続先や日付を指定してください。

- 設定の参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続 & 日次 ETL の実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai_scores への書き込み）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn: DuckDB 接続
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key を渡さないと OPENAI_API_KEY を参照
print("書込み銘柄数:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
```

- 監査スキーマを既存接続に追加:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意点:
- score_news / score_regime は OpenAI を呼ぶため API キーと通信が必要です。テスト時は内部の _call_openai_api をモックできます（unit tests を意図）。
- ETL は J-Quants API 呼び出しを行います。get_id_token は settings.jquants_refresh_token を使用します。

---

## 主要モジュールとディレクトリ構成

リポジトリ内の主要なファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         - 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                      - ニュースの LLM スコアリング（ai_scores へ書込）
    - regime_detector.py               - 市場レジーム判定（ma200 + マクロニュース）
  - data/
    - __init__.py
    - pipeline.py                      - ETL のメイン実装（run_daily_etl 等）
    - jquants_client.py                - J-Quants API クライアント + 保存ロジック
    - calendar_management.py           - 市場カレンダーの管理・判定ユーティリティ
    - news_collector.py                - RSS 収集・前処理・保存
    - stats.py                         - 汎用統計（zscore_normalize）
    - quality.py                       - データ品質チェック
    - audit.py                         - 監査ログ（DDL / 初期化）
    - pipeline.py                      - ETL pipeline 実装（ETLResult 等）
    - etl.py                           - ETL インターフェース (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py               - Momentum/Volatility/Value の計算
    - feature_exploration.py           - 将来リターン・IC・統計サマリーなど
  - monitoring/ (存在すれば監視用コード)
  - execution/, strategy/ など（コードベース拡張ポイント）

（実際のツリーはリポジトリのファイル一覧を参照してください）

---

## 開発・運用上の注意

- Look-ahead bias 回避:
  - 多くの関数は date 引数で明示的に基準日を受け取り、内部で date.today()/datetime.today() を直接参照しない設計になっています。バックテスト時は必ず過去の時点のみを読めるよう DB を整備してください。
- 冪等性:
  - ETL の DB 書き込みは ON CONFLICT DO UPDATE 等で冪等に設計されています。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants）失敗時は可能な限りフェイルセーフ（デフォルトスコアやスキップ）で継続する箇所が多くあります。重要箇所はログ出力されます。
- セキュリティ:
  - RSS 取得や URL 正規化に SSRF 対策、defusedxml による XML 防御、受信サイズ制限などを設けています。
- 自動環境読み込み:
  - config モジュールはプロジェクトルート（.git か pyproject.toml）を検出して .env / .env.local を自動読み込みします。自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途に便利です）。

---

## テスト・モック化のヒント

- OpenAI 呼び出し部分は各モジュールで `_call_openai_api` のラッパー関数を用意しており、ユニットテスト時にはこれを patch / mock してレスポンスを制御できます。
- network / API 呼び出しは jquants_client._request や news_collector._urlopen をモックすることで外部依存を切り離せます。
- DuckDB は ":memory:" でインメモリ接続が可能なのでテスト用 DB 準備が容易です。

---

この README はコードベースの概要と基本的な使い方をまとめたものです。詳細な API 仕様やスキーマ、運用手順（ジョブスケジューラ、監視、ロールアウト等）は別途ドキュメント（DataPlatform.md / StrategyModel.md 等）に従ってください。