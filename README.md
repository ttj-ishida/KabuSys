# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP評価、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（注文・約定トレーサビリティ）などを提供します。

---

## 主な特徴（概要）
- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）を安全かつ冪等に実行
- ニュース RSS 収集と前処理、OpenAI を用いた銘柄別センチメントスコア算出（ai_score）
- マクロニュース + ETF（1321）の MA200 乖離を組み合わせた市場レジーム（bull/neutral/bear）判定
- ファクター生成（Momentum / Value / Volatility など）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution）を保持する DuckDB スキーマ初期化機能
- Look-ahead バイアス対策（日時参照・クエリ設計に配慮）、API リトライ/レート制御、フェイルセーフ設計

---

## 機能一覧（主要モジュール）
- kabusys.config
  - 環境変数読み込み・Settings（J-Quants トークン、kabu API、Slack、DB パス、実行環境など）
  - .env 自動ロード（プロジェクトルートを探索）
- kabusys.data
  - jquants_client: J-Quants との HTTP クライアント（レート制御、トークンリフレッシュ、保存関数）
  - pipeline / etl: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl、ETL 結果クラス
  - news_collector: RSS 取得、前処理、raw_news への保存（SSRF 対策等）
  - calendar_management: 営業日判定、calendar_update_job
  - quality: 品質チェック（missing, spike, duplicates, date consistency）
  - audit: 監査ログテーブル作成 / 初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースから銘柄ごとの ai_score を生成して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321) MA200 とマクロニュース（LLM）を合成して market_regime テーブルへ保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提・要件
- Python 3.10 以上（typing の | 演算子等を使用）
- 必要な Python パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）および適切な API キー

実際のプロジェクトでは requirements.txt を用意してください。以下は例示的なインストール手順を README の「セットアップ」で示します。

---

## 環境変数（重要）
主に Settings クラス、および AI モジュールで参照される環境変数の一覧（.env に設定してください）:

必須（Settings で require）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 認証パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — 通知先 Slack チャネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を使う場合（news_nlp / regime_detector は api_key 引数か環境変数で取得）

自動 .env ロードの制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとパッケージ起動時の .env 自動ロードを無効化できます。

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）
   - 開発時: pip install -e .

4. 環境変数（.env）を作成
   - プロジェクトルートに .env を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
   - 必要なキーを設定してください（上記参照）。

5. DuckDB ファイル等のディレクトリ作成
   - デフォルトでは data/ 以下に DB を置くので必要に応じて作成されます（モジュール側で自動作成する箇所あり）。

---

## 使い方：基本的な呼び出し例

以下は最小限の利用例です。すべての関数は DuckDB 接続オブジェクト（duckdb.connect(...) が返すオブジェクト）を受け取ります。

- DuckDB 接続の取得と ETL 実行（日次 ETL）
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア算出（OpenAI API が必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示するか、環境変数 OPENAI_API_KEY を設定する
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ（audit）用 DB 初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで監査テーブル（signal_events, order_requests, executions 等）が作成されます
```

注意点:
- AI 関連関数（score_news / score_regime）は api_key を引数で受け取れます。指定しない場合は環境変数 OPENAI_API_KEY を参照します。
- ETL / 保存処理は冪等に設計されています（ON CONFLICT DO UPDATE 等）。

---

## 自動 .env 読み込みの動作
- パッケージインポート時にプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、.env と .env.local を自動で読み込みます（既存 OS 環境変数は保護されます）。
- 無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（主にテストで利用）。

---

## ディレクトリ構成（主要ファイルの説明）
以下は `src/kabusys` 以下の主要ファイルとその役割の概観です。

- __init__.py
  - パッケージのバージョン・公開モジュール定義

- config.py
  - 環境変数の読み込み、Settings クラス（各種キー・パス・実行環境フラグ）

- ai/
  - news_nlp.py — RSS で集めた raw_news を OpenAI に投げ銘柄ごとの ai_scores を生成する処理
  - regime_detector.py — ETF(1321) MA200 と LLM マクロセンチメントを合成して market_regime に保存

- data/
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB への保存関数）
  - pipeline.py — run_daily_etl 等の ETL パイプライン
  - etl.py — ETLResult の再公開インターフェース
  - news_collector.py — RSS 取得・前処理・raw_news 保存（SSRF 対策等）
  - calendar_management.py — market_calendar の管理、営業日判定ユーティリティ
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマ定義と初期化ツール
  - stats.py — zscore_normalize 等の統計ユーティリティ

- research/
  - factor_research.py — Momentum / Value / Volatility の計算
  - feature_exploration.py — 将来リターン計算、IC, 統計サマリーなど

- その他
  - monitoring, execution, strategy 等のサブパッケージを想定（パッケージ公開配列に含まれますが、実装は別途追加）

（リポジトリ全体のファイル構造は実際のソースに合わせて確認してください）

---

## 運用上の注意
- 本コードは実運用の注文（実際の売買）機能とは分離して開発されています。実際の発注やライブ運用を行う場合は、十分なテスト、監査、リスク制御を行ってください。
- OpenAI や J-Quants API の呼び出しにはコストとレート制限があります。設定とリトライ挙動（指数バックオフ・最大リトライ回数等）を理解したうえで利用してください。
- DuckDB に対する executemany の空リスト渡しやタイムゾーン等の扱いに注意（コード内に互換性処理が記載されています）。
- 監査ログは削除しない想定のため、ディスク管理・バックアップ設計を検討してください。

---

必要であれば、README に以下を追記できます：
- CI / テストの実行方法
- 既知の制約・TODO
- 詳細な API リファレンス（関数ごとの使用例と引数説明）
- デプロイ / Cron（ジョブ）実行例（systemd / Kubernetes CronJob など）

ご希望があれば上記のいずれかを詳しく追記します。