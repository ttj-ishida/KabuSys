# KabuSys

KabuSys は日本株向けのデータパイプライン・リサーチ・AI分析・監査ログを備えた自動売買／研究プラットフォームのコアライブラリです。DuckDB をデータ層に使い、J‑Quants API / RSS / OpenAI を組み合わせてデータ収集、品質チェック、ファクター計算、ニュースセンチメント評価、マーケットレジーム判定、監査ログの永続化などを行います。

主な設計方針は「ルックアヘッドバイアス回避」「冪等処理」「外部APIの堅牢なリトライ/フォールバック」です。

---

## 主な機能

- ETL（J‑Quants からの株価・財務・カレンダーの差分取得と DuckDB 保存）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック（欠損、重複、スパイク、日付不整合）
  - run_all_checks 等
- ニュース収集（RSS）と前処理、raw_news / news_symbols への保存
  - news_collector.fetch_rss 等（SSRF 対策・レスポンスサイズ制限あり）
- ニュース NLP（OpenAI を用いた銘柄別センチメント付与）
  - ai.news_nlp.score_news
- マクロセンチメント＋ETF MA200 を用いた市場レジーム判定
  - ai.regime_detector.score_regime
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - research.factor_research.calc_momentum / calc_volatility / calc_value
  - research.feature_exploration の IC・forward returns・統計サマリー等
- 監査ログ（signal → order_request → execution までのトレーサビリティ）
  - data.audit.init_audit_db / init_audit_schema
- 汎用統計ユーティリティ（Zスコア正規化）
  - data.stats.zscore_normalize
- 設定管理
  - kabusys.config.settings（.env 自動読み込み機能あり）

---

## 要件（主な依存パッケージ）

- Python 3.9+
- duckdb
- openai
- defusedxml
- （標準ライブラリ：urllib, json, datetime, logging 等）

実行に必要な外部サービス／認証情報:
- J‑Quants API リフレッシュトークン（JQUANTS_REFRESH_TOKEN）
- OpenAI API キー（OPENAI_API_KEY） — ニュース NLP / レジーム判定で使用
- kabuステーション API 周りの設定（発注等を行う場合）
- Slack トークン等（通知用途）

（実行環境に合わせて追加パッケージが必要な場合があります。）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトを配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows の場合は .venv\Scripts\activate）
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - その他、プロジェクトの requirements.txt があればそれを使用してください
4. 環境変数の設定
   - プロジェクトルート（pyproject.toml か .git が存在するディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（kabusys.config により自動ロード）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
5. データ格納ディレクトリを作成（必要なら）
   - デフォルト DuckDB パス: data/kabusys.duckdb
   - 監視用 SQLite パス: data/monitoring.db
   - PID ファイル等の出力先は設定で変更可能

.env に設定すべき代表的なキー（例）

- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- KABUSYS_ENV=development  # (development|paper_trading|live)
- LOG_LEVEL=INFO

.env の読み込みルールやパースは kabusys.config が実装しています（コメント行、クォート等の扱いに対応）。

---

## 使い方（基本例）

以下はライブラリをインポートして操作する基本的なサンプルです。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB に接続して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は .env や環境変数で上書き可能
conn = duckdb.connect(str(settings.duckdb_path))

# 今日を対象に ETL を実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())  # ETL 結果の概要
```

- ニュースセンチメント（OpenAI を使用）で ai_scores を更新する

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# API キーを引数で明示的に渡すこともできます (api_key="sk-...")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 MA200 + マクロニュース）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化

```python
from kabusys.data.audit import init_audit_db

# ファイル DB を初期化して接続を取得
conn = init_audit_db("data/audit.duckdb")
# あるいは in-memory:
# conn = init_audit_db(":memory:")
```

- 研究用ファクター計算・IC 計算

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
factors = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

注意点：
- OpenAI 呼び出し箇所はネットワークエラー・レート制限・不正レスポンスに対してフェイルセーフ（0.0 スコアやスキップ）を採用しています。
- ETL・保存操作は冪等（ON CONFLICT）で実装済みです。

---

## 設定 (kabusys.config)

- settings オブジェクトから各種設定を取得できます。
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
  - settings.slack_bot_token / settings.slack_channel_id
  - settings.duckdb_path（Path）
  - settings.sqlite_path（Path）
  - settings.pid_file_path（Path）
  - settings.cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
  - settings.env（development, paper_trading, live）
  - settings.log_level

- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
  - OS 環境変数は上書き保護されます（`.env.local` は上書きを許容）。
  - 自動ロードが不要な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

（ローカルの `src/kabusys` 配下の主要モジュールを列挙）

- kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py  — ニュース NLP（OpenAI 利用）
    - regime_detector.py  — 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py  — 市場カレンダー管理
    - etl.py (API) — ETL 結果公開
    - pipeline.py  — 日次 ETL パイプライン実装
    - stats.py  — 統計ユーティリティ（z-score）
    - quality.py  — データ品質チェック
    - audit.py  — 監査ログ（DDL / 初期化）
    - jquants_client.py  — J‑Quants API クライアント（取得＋DuckDB保存）
    - news_collector.py  — RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py  — モメンタム／ボラティリティ／バリュー等の計算
    - feature_exploration.py  — 将来リターン計算、IC、統計サマリー
  - research パッケージは data.stats を利用して正規化等を実施

（上記に加えて、プロジェクトルートに pyproject.toml / .env.example 等がある想定）

---

## 開発 / テスト時のヒント

- OpenAI の外部呼び出しは内部で _call_openai_api をラップしている箇所があり、テスト時は unittest.mock.patch で差し替え可能です（news_nlp / regime_detector にそれぞれ別実装あり）。
- news_collector はネットワーク／SSRF 対策を実装しているため、外部 RSS をテストする際はモック化がおすすめです。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、コード中で空チェックが入っています（実装参照）。

---

## トラブルシューティング

- .env が読み込まれない場合:
  - プロジェクトルートが正しく検出されているか (.git または pyproject.toml の存在) を確認してください。
  - 自動ロードを無効化している環境変数がないか確認: KABUSYS_DISABLE_AUTO_ENV_LOAD
- OpenAI / J‑Quants の認証エラー:
  - 環境変数（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）が正しいか確認してください。
  - jquants_client は 401 時にトークンを自動リフレッシュする挙動を持ちます（設定したリフレッシュトークンを利用）。
- DuckDB スキーマ不整合やテーブル未作成:
  - ETL 実行前にデータベースに期待するテーブル（raw_prices, raw_financials, market_calendar 等）が作成されているか確認してください（初期化スクリプトを用意するか、ETL 実行で作成される前提の箇所もあります）。

---

## ライセンス / 貢献

本 README はコードベースに基づく簡易ドキュメントです。実運用前に必ずセキュリティ（API トークン管理・ネットワーク制約）、テスト、監査要件を確認してください。貢献・バグ報告・機能提案はリポジトリの issue / pull request で受け付けてください。

---

以上。必要であれば、README に含めるサンプル .env.example、より詳細な API 使用例、あるいは CLI や Systemd / Cron ジョブの起動例なども作成します。どの情報を追加しますか？