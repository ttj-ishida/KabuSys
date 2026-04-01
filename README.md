# KabuSys

日本株自動売買システムのライブラリ (KabuSys)

軽量なデータパイプライン、ニュース NLP（LLM）評価、リサーチ用ファクター計算、監査ログスキーマ、J-Quants / kabuAPI クライアントなどを含むモジュール群です。バックテスト/リサーチと実運用（paper/live）の両方を想定した設計がなされています。

---

## 主な機能

- データ取得・ETL
  - J-Quants から株価日足 / 財務データ / 市場カレンダーの差分取得（ページネーション・レート制御・自動トークンリフレッシュ対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL の統合エントリポイント（run_daily_etl）

- データ品質チェック
  - 欠損、重複、将来日付、株価スパイクなどを検出する品質チェック群（quality.run_all_checks）

- ニュース収集・NLP
  - RSS から記事収集（SSRF対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコアリング（news_nlp.score_news）
  - マクロニュースとETF（1321）の MA200 による市場レジーム判定（regime_detector.score_regime）

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution のトレーサブルな監査テーブル定義と初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）

- 設定管理
  - .env ファイルと環境変数からの設定読み込み／バリデーション（kabusys.config.settings）
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## セットアップ手順

以下は開発環境向けの基本手順です。プロジェクトの配布パッケージや CI に合わせて調整してください。

1. Python 仮想環境を作成・有効化（例: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - requirements.txt がない場合、主要依存をインストールしてください（例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt/pyproject.toml があればそちらを使ってください）
   
3. パッケージをインストール（開発モード）
   - プロジェクトルートで:
     pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置することで自動で読み込まれます（kabusys.config が実行時にロード）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必要な外部 API キー・情報を用意
   - J-Quants のリフレッシュトークン、OpenAI API キー、kabu API のパスワード、Slack トークンなどを設定します（下記「環境変数」を参照）。

---

## 必要な環境変数（主なもの）

（.env に設定してください。デフォルト値のあるものは注記します）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite （監視用 DB）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行監視用 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（パーセンテージ）
- KABUSYS_ENV: 実行環境（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

注: 必須環境変数が未設定の場合、kabusys.config.Settings の該当プロパティを参照した際に ValueError が発生します。

---

## 使い方（主な例）

以下はライブラリをインポートして使う基本的な例です。DuckDB に接続して各機能を呼ぶ想定です。

- DuckDB 接続を作成する例

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（J-Quants からデータ取得 → 保存 → 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl

# target_date を指定するか、None で今日として扱う
result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI 必須）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))
print("scored codes:", written)
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロ記事を組み合わせる）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は DuckDB 接続（監査テーブルが作成済み）
```

- リサーチ用ファクター計算の呼び出し例

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

---

## 実行/運用上の注意

- Look-ahead バイアス対策
  - 各 AI / リサーチ関数は内部で datetime.today() を直接参照しないよう設計されています。必ず target_date を明示して実行してください。

- LLM API
  - OpenAI 呼び出しはリトライ・バックオフ処理を行いますが、API キーや使用量には注意してください。
  - news_nlp と regime_detector は JSON Mode を使って厳密な JSON レスポンスを期待しています（パース失敗時はフェイルセーフでスキップ or 0.0 を返す実装です）。

- ETL の堅牢性
  - run_daily_etl は各ステップで例外を捕捉して継続する設計です。結果は ETLResult オブジェクトで確認できます。

- セキュリティ
  - news_collector は RSS 取得時に SSRF 対策やレスポンスサイズ制限、トラッキング除去などを実施しています。独自ソース追加時もこれらのポリシーを遵守してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュール）

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py               — ニュース NLP（銘柄別スコア）
    - regime_detector.py       — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETL 型再エクスポート（ETLResult）
    - news_collector.py        — RSS 収集（SSRF 対策等）
    - calendar_management.py   — 市場カレンダー管理（is_trading_day 等）
    - quality.py               — データ品質チェック
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py       — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー

---

## 開発メモ / 備考

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- KABUSYS_ENV の値は 'development' / 'paper_trading' / 'live' のいずれかである必要があります。

- ログレベルの制約は CONFIG 内でバリデーションされます（DEBUG, INFO, WARNING, ERROR, CRITICAL）。

- DuckDB について
  - デフォルト DB パスは data/kabusys.duckdb です。DockDB のバージョン依存の SQL 動作に注意してください（コメント内に互換性に関する注記あり）。

---

必要であれば、README に含める具体的なコマンド、CI 設定例、依存パッケージの正確な一覧（requirements.txt）や .env.example のテンプレートも作成します。どの情報を追加しますか？