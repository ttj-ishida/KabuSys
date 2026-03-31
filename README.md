# KabuSys

日本株向けの自動売買・データプラットフォーム（ライブラリ）です。  
J-Quants からのデータ取得・ETL、ニュース収集と LLM によるセンチメント評価、ファクター計算、監査ログ（発注／約定トレーサビリティ）、市場レジーム判定などを統合的に提供します。

主な想定用途:
- データパイプライン（株価 / 財務 / カレンダー）の自動取得と品質チェック
- ニュースを用いた AI スコアリング（銘柄別センチメント）
- ファクター計算とリサーチ用ユーティリティ
- 発注から約定までの監査ログ（DuckDB ベース）
- 市場レジーム（bull / neutral / bear）判定（ETF MA + マクロニュース）

---

## 機能一覧

- ETLパイプライン
  - 差分取得（J-Quants）→ DuckDB へ冪等保存
  - 市場カレンダーの差分更新・バックフィル
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- J-Quants API クライアント
  - 株価日足、財務データ、JPX カレンダー、上場銘柄一覧
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ
- ニュース収集
  - RSS 取得、前処理、SSRF 対策、トラッキングパラメータ除去、raw_news へ冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコアを ai_scores に書き込み（gpt-4o-mini + JSON mode を使用）
  - レート・エラーに対するリトライとフェイルセーフ
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成
  - 判定結果を market_regime テーブルへ冪等保存
- 研究（research）
  - Momentum / Value / Volatility ファクター計算
  - 将来リターン計算、IC（Spearman）、統計サマリ等
- 監査（audit）
  - signal_events / order_requests / executions テーブルとインデックスを作成する初期化ユーティリティ
- 共通ユーティリティ
  - 設定管理（.env の自動読み込み、環境変数ラッパ）
  - 統計ユーティリティ（Z スコア正規化 等）

---

## 要件

- Python 3.10+
- 依存パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで多くを実装しています）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発パッケージを editable install にする場合:
pip install -e .
```

（プロジェクトの setup/pyproject.toml がある場合はそちらからインストールしてください）

---

## 環境設定 (.env)

パッケージ起動時に自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: デフォルト DB パス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視設定
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

.env のパースはシェル風のクォート、コメント、export キーワードに対応しています。

---

## セットアップ手順（ローカル実行の基本）

1. リポジトリをクローン
2. 仮想環境を作成して有効化
3. 依存をインストール（duckdb, openai, defusedxml 等）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. データ格納先のディレクトリを作成（例: data/）
6. DuckDB 接続を用意してスキーマ初期化や ETL を実行

例:
```bash
git clone <repo>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
mkdir -p data
# .env を作成 (上記参照)
```

---

## 使い方（主要なユースケース）

以下は Python REPL / スクリプトから呼び出す基本的な例です。すべて DuckDB 接続（duckdb.connect(...)）を渡して実行します。

- DuckDB 接続の利用例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（カレンダー・株価・財務・品質チェック）:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースの AI スコアリング（target_date に対して前日 15:00 JST 〜 当日 08:30 JST のウィンドウ）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026,3,20))
print("written", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照
```

- 監査ログ DB の初期化（監査専用 DB に初期テーブルを作る）:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

- 研究系ユーティリティ（ファクター計算等）:
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

m = calc_momentum(conn, date(2026,3,20))
v = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

注意:
- OpenAI の呼び出しは gpt-4o-mini を使用し、JSON モードでレスポンスを期待します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API 呼び出しでは rate limiting / retry / token refresh をライブラリ側で処理します。JQUANTS_REFRESH_TOKEN を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュールの一覧（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                  -- 環境変数 / .env の自動読み込みと設定アクセス
  - ai/
    - __init__.py
    - news_nlp.py              -- ニュースセンチメント（銘柄単位）スコアリング
    - regime_detector.py       -- 市場レジーム判定（ETF MA + マクロ記事）
  - data/
    - __init__.py
    - pipeline.py              -- ETL パイプライン（run_daily_etl 等）
    - jquants_client.py        -- J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py        -- RSS ニュース収集
    - calendar_management.py   -- 市場カレンダー判定 / 更新ジョブ
    - quality.py               -- データ品質チェック
    - stats.py                 -- 統計ユーティリティ（zscore_normalize）
    - audit.py                 -- 監査スキーマ初期化（signal/order/execution）
    - etl.py                   -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py       -- Momentum / Value / Volatility の計算
    - feature_exploration.py   -- 将来リターン / IC / サマリ等
  - monitoring/                 -- （存在するなら監視ロジック）
  - strategy/                   -- （戦略層の実装想定）
  - execution/                  -- （発注実行・kabu API 連携想定）

この README にある API はライブラリの公開関数を中心に抜粋しています。実際の関数・クラスのシグネチャは各モジュールの docstring を参照してください。

---

## 設計上の注意点（重要）

- Look-ahead bias の回避を重視しています。各モジュールは内部で datetime.today()/date.today() を直接参照しないよう配慮し、target_date 引数で日付を明示的に渡すことを想定します。
- DuckDB をデータ格納に利用。挿入は ON CONFLICT DO UPDATE 等で冪等性を担保します。
- 外部 API（OpenAI / J-Quants / RSS）利用部はフェイルセーフ設計。API エラーがあっても基本的に処理を継続し、ログに記録することで運用しやすくしています。
- セキュリティ対策（ニュース収集）: SSRF 防止、トラッキングパラメータ除去、defusedxml による XML パース保護、レスポンスサイズ制限など。

---

## 開発・運用上のヒント

- テスト実行時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 env 読み込みを無効化すると便利です。
- DuckDB のファイルパスは settings.duckdb_path で取得できます。CI では ":memory:" を使うと簡便です。
- OpenAI の API 呼び出しは外部コールに依存するため、ユニットテストではモック（patch）しておくと高速・安定します（コード内でもモックしやすい設計になっています）。
- J-Quants の rate limit に注意。jquants_client はモジュール内でレート制御を行いますが、ETL 実行頻度を運用で管理してください。

---

もし README をプロジェクトのルートで使う形（pyproject.toml / requirements.txt を含めたインストール手順や CI 用の例、さらに詳しい API リファレンスやサンプルワークフロー）に拡張したい場合は、その要望に合わせて追記します。