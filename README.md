# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群。  
J-Quants などの外部データソースからの ETL、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注→約定トレース）などのユーティリティを提供します。

主な設計方針：
- ルックアヘッドバイアス防止（内部で datetime.today()/date.today() を直接参照しない関数設計）
- DuckDB を主要なローカル時系列データストアとして利用
- OpenAI（gpt-4o-mini）を用いたニュース NLP（JSON モード）で銘柄別センチメントを算出
- 冪等処理（INSERT ... ON CONFLICT / トランザクション管理）を重視

---

## 機能一覧（ハイレベル）
- 環境変数・設定管理（kabusys.config）
  - .env / .env.local を自動ロード（無効化可）
  - 必須変数チェック
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants から株価・財務・カレンダー取得、DuckDB へ保存（差分更新・ページング対応）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar 更新ジョブ、news collector（RSS）等
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して OpenAI に送信
  - 銘柄ごとの ai_score を ai_scores テーブルへ書き込み
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定
- 研究用ユーティリティ（kabusys.research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z スコア正規化
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルを作成、トレーサビリティを保証
  - init_audit_db / init_audit_schema による初期化

---

## 前提・依存
- Python 3.10+
- 主要依存（抜粋）:
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続: J-Quants API、OpenAI API、RSS ソースなどへのアクセス
- 環境変数（下記参照）を適切に設定

---

## セットアップ手順

1. リポジトリをクローン／取得

   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成・有効化（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）

   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実際にはプロジェクトの requirements.txt / pyproject.toml があればそちらを使用してください。

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある階層）に `.env` / `.env.local` を置くと自動ロードされます。
   - 自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例: `.env`（テンプレート）

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境 / ログ
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 簡単な使い方（コード例）

以下は主なユースケースのサンプルです。実運用ではエラー処理・ロギング・トランザクションを適切に追加してください。

- DuckDB 接続と日次 ETL 実行（データ取得→保存→品質チェック）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- AI ニューススコアリング（OpenAI API キーが必要）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定（MA200 とマクロニュース）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化（監査専用 DB）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等が作成されます
```

- 研究用ファクター計算

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート基準）
  - settings オブジェクトで必須環境変数をプロパティとして参照

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（リフレッシュトークンを使った ID トークン取得）
  - 内部でレートリミット・リトライ・401 の自動リフレッシュを実装

- kabusys.data.pipeline
  - run_daily_etl: カレンダー→株価→財務→品質チェックの一括パイプライン
  - 個別 ETL: run_prices_etl, run_financials_etl, run_calendar_etl

- kabusys.ai.news_nlp
  - calc_news_window: 記事ウィンドウ（前日15:00 JST～当日08:30 JST）を計算
  - score_news: 銘柄ごとの記事を集約し OpenAI に渡して ai_scores へ保存

- kabusys.ai.regime_detector
  - score_regime: ETF 1321 の MA200 とマクロニュースの LLM 出力を合成して market_regime テーブルへ書込み

- kabusys.data.news_collector
  - RSS フィード収集、安全対策（SSRF・XML Bomb・サイズ制限・トラッキング除去）
  - raw_news / news_symbols への冪等保存（記事ID は正規化 URL の SHA-256 の一部）

- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行し QualityIssue を返す

- kabusys.research
  - calc_forward_returns / calc_ic / rank / factor_summary / zscore_normalize 等の研究ユーティリティ

---

## ディレクトリ構成

プロジェクトの主要ファイル（src 配下の抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
      - audit.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/      (コードリストには存在するトップレベルのみ示唆)
    - execution/       (発注・約定に関わるモジュール群)
    - strategy/        (戦略生成ロジック)
    - data/            (上記参照)

（実際のリポジトリにはさらに補助モジュール・テスト・スクリプトが含まれる可能性があります）

---

## 注意点・運用上のヒント
- OpenAI 呼び出しは API コスト・レート制限に注意してください。news_nlp/regime_detector ではリトライ・バッチ化・チャンク化を実装していますが、実行頻度・バッチサイズは運用に合わせて調整してください。
- J-Quants 呼び出しは 120 req/min のレートリミットを守る実装がありますが、長時間ジョブやページネーション処理のエラーハンドリングを確認してください。
- DuckDB の executemany はバージョンによって空リストの扱いに差があるため、該当箇所では空確認を行っています（pipeline / news_nlp など）。
- テスト時に .env の自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監査ログ（audit）を初期化する際は UTC タイムゾーンに固定されます。init_audit_db は transactional=True で安全に初期化します。

---

## 貢献・開発
- コードはモジュール単位に分かれており、ユニットテストは各モジュールのネットワーク呼び出しをモックして実装することを推奨します（例: OpenAI 呼び出し / HTTP リクエスト / urllib のオープンなど）。
- 新しいデータ取得ソースや戦略を追加する場合は、ETL の冪等性・品質チェック・監査ログへの書き込み方針に沿って設計してください。

---

必要であれば、README に以下を追加できます：
- 実際の requirements.txt / pyproject.toml ベースのインストール手順
- 開発用の Docker / CI 設定例
- 具体的な DB スキーマ（CREATE TABLE 文）やサンプル .env.example ファイルの完全版

追加希望があれば教えてください。