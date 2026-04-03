# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買リサーチ／実行ライブラリです。  
DuckDB をデータレイヤーに用い、J-Quants API や RSS ニュース、OpenAI を組み合わせて以下の処理を提供します。

- 日次 ETL（株価 / 財務 / 市場カレンダー）の差分取得・保存・品質チェック
- ニュースの収集・前処理・LLM による銘柄センチメント算出
- マーケットレジーム判定（ETF MA200 とマクロニュースの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）および統計ユーティリティ
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ
- J-Quants / kabuステーション のクライアント、品質チェック、ニュース収集等

このリポジトリはモジュール単位で分かれており、研究（research）、データ（data）、AI（ai）、監視／実行層（execution/monitoring）などの責務が分離されています。

---

## 主な機能一覧

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェックの一連処理
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別実行
- J-Quants クライアント（kabusys.data.jquants_client）
  - トークン管理、ページネーション、リトライ、レート制御、DuckDB 保存（冪等）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、SSRF 対策、記事ID 正規化、raw_news への保存
- ニュース NLP（kabusys.ai.news_nlp）
  - ニュースを銘柄ごとにまとめ、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores に保存
- レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200日 MA 乖離とマクロニュース LLM スコアを合成して market_regime に保存
- 研究ユーティリティ（kabusys.research）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC 計算、ランク関数、統計サマリ
- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク・日付不整合などを検出し QualityIssue を返す
- 監査ログ初期化（kabusys.data.audit）
  - 監査用テーブル/インデックスの冪等初期化、専用 DB の初期化補助
- 設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルート基準）、環境変数ラッパー settings

---

## セットアップ手順（開発用）

以下は一般的な Python パッケージとしてのセットアップ例です。実際の requirements はプロジェクトの配布に合わせて調整してください。

1. Python 仮想環境を作成・アクティベート
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt や pyproject.toml を使って管理してください。  
   （このリポジトリには requirements ファイルが無い想定なので最低限の例を載せています）

3. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須・推奨の環境変数（kabusys.config.Settings を参照）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使う場合）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・プロセスマネジメント用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

.env 解析はコメント、export プレフィクス、クォート、エスケープ等に耐性を持った実装です。

---

## 使い方（コード例）

以下は代表的なユースケースの簡単な例です。各関数は duckdb の接続オブジェクト（duckdb.connect() の返却）を受け取ります。

- 日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使う例
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("data/kabusys.duckdb"))
# OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored", n_written)
```

- 市場レジームを判定して market_regime に保存する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str("data/kabusys.duckdb"))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って order_requests / executions テーブルへアクセス
```

- ファクター計算・統計

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- J-Quants API 呼び出し（fetch_*）は settings.jquants_refresh_token を必要とします（JQUANTS_REFRESH_TOKEN 環境変数）。

---

## 主要 API の挙動メモ

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）から `.env` → `.env.local` の順で読み込む。
  - OS 環境変数はデフォルトで優先され、.env.local は既存変数を上書きします（ただし OS の変数は保護される）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。

- News NLP / Regime Detector のフェイルセーフ
  - LLM 呼び出しが失敗した場合はゼロ（中立）スコアでフォールバックし、処理継続する設計です（ログに警告）。

- J-Quants クライアント
  - 固定間隔のレート制御（120 req/min）を実装
  - 401 時はリフレッシュトークンで自動更新して再試行
  - ページネーション対応、JSON パース失敗やリトライ対応あり
  - DuckDB への保存関数は ON CONFLICT DO UPDATE で冪等性を担保

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - pipeline.py
    - etl.py (ETLResult 再エクスポート)
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research (utils): zscore_normalize は data.stats にあり research から利用
  - (execution/, monitoring/ 等はパッケージ公開リストに含まれますが本スナップショットに実装がある場合は同階層に配置)

各モジュールはコメントに設計方針が詳述されており、DuckDB 接続を受け取るインターフェースで統一されています。

---

## 運用上の注意

- Look-ahead bias を避けるため、多くの関数は内部で date.today() や datetime.now() を直接参照しないように設計されています。バックテストや再現性のため、明示的な target_date を渡すことを推奨します。
- OpenAI へのプロンプトは JSON 出力を期待する（response_format 等で構造化レスポンスを要求）。レスポンスパース失敗は中立フォールバックとなります。
- DuckDB の executemany はバージョン依存の挙動（空リストの扱い等）があるため、モジュール内で対策済みです。
- 監査ログスキーマは冪等に初期化できるよう設計されています。init_audit_db を使用して独立した DB を作成することを推奨します。

---

## ライセンス / 貢献

（ここにはライセンスや貢献ルールを記載してください。リポジトリ内の LICENSE ファイルに従って下さい。）

---

この README はコードベースの主要部分を要約したものです。個々のモジュールの詳細実装や追加オプションは該当ソースファイルの docstring と実装コメントを参照してください。必要であれば、使用例やデプロイ手順（systemd / supervisor / Docker）、CI/CD、テスト方法（ユニットテスト・モック戦略）などの追補ドキュメントも作成できます。