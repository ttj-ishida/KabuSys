# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、ファクター計算、監査ログ、AI を使った市場レジーム判定などを含みます。

主に DuckDB をデータストアに、OpenAI（gpt-4o-mini など）をニュースNLP に利用する設計です。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート判定）
  - 必須環境変数の取得ユーティリティ
- データ取得・ETL（J-Quants）
  - 日次株価（OHLCV）、四半期財務、JPX カレンダーの差分取得・保存（ページネーション/冪等）
  - ETL の集約実行（run_daily_etl）
- データ品質チェック
  - 欠損チェック、スパイク検出、重複チェック、日付整合性チェック
  - 問題は QualityIssue として収集・返却
- ニュース収集
  - RSS 取得、前処理、SSRF/サイズ/トラッキングパラメータ対策、raw_news への冪等保存想定
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - マクロニュースから市場レジーム判定（score_regime）
  - API 呼び出しはリトライ/バックオフを考慮
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化ユーティリティ
- 監査ログ（監査テーブルの初期化）
  - signal_events / order_requests / executions などのスキーマ定義と初期化ユーティリティ
- JPX カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job

---

## 動作要件（推奨）

- Python 3.10+（型ヒントの union operator `|` を使用）
- 必要なライブラリ（一部）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで動く機能も多いが、OpenAI / DuckDB を使う場合は上記が必要）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージとしてインストール可能であれば:
# pip install -e .
```

※ 本リポジトリに pyproject.toml/setup.py がある場合はそれに従ってインストールしてください。

---

## 環境変数（主要）

プロジェクトは .env / .env.local をプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から自動読み込みします。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（名前と用途）:

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携用）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知関連（任意）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH 等の監視関連設定
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

.env の書式は shell 形式に準拠（export プレフィックス・クォート・コメントに対応）。

---

## セットアップ手順（概要）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境作成 & 有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存ライブラリのインストール
   ```bash
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使用してください）

4. .env を作成（プロジェクトルート）
   - 必須: JQUANTS_REFRESH_TOKEN
   - OpenAI を使う場合: OPENAI_API_KEY
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     ```

5. データディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な例）

以下は Python からの呼び出し例です。DuckDB 接続は `duckdb.connect(path)` を使います。

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示するか、環境変数 OPENAI_API_KEY を設定
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

- 市場レジームスコアを算出して market_regime に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降、conn を使って監査テーブルにアクセスできます
```

- ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records: list[dict] を分析 / 正規化して利用
```

---

## 自動 .env 読み込みについて

- パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` と `.env.local` を自動読み込みします。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` を上書きする用途
- 自動読み込みを無効にする:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードをスキップします（テスト時などに便利）。

---

## ディレクトリ構成（src/kabusys 配下の主なファイル）

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
    - stats.py
    - quality.py
    - audit.py
    - (その他: etl/pipeline に関連するユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research のユーティリティは kabusys.data.stats も参照
  - そのほか: strategy/, execution/, monitoring/（パッケージ __all__ に名前あり。実装は別途）

（README の対象コードベースは上記のモジュール群を中心に設計されています）

---

## ログ・監視

- ログレベルは環境変数 `LOG_LEVEL` で制御します（デフォルト: INFO）。
- 監視用の閾値や pid/kill フラグは Settings（config.py）で定義されており、環境変数経由で変更できます。

---

## 設計上の注意点 / ポリシー

- Look-ahead bias（将来情報の漏洩）を防ぐ設計:
  - 各スコア/ETL で対象日の判定に datetime.today()/date.today() を直接使用しない設計が意識されています（関数に target_date を明示的に渡す）。
  - 取得日時（fetched_at）は UTC で記録。
- 冪等性:
  - データ保存は ON CONFLICT / DELETE → INSERT のような冪等処理を行うよう設計されています。
- API 呼び出し:
  - リトライと指数バックオフ、HTTP ステータス別の扱い（401 トークン更新、429 の Retry-After 参照等）を組み込んでいます。
- セキュリティ:
  - RSS の取得では SSRF 対策（ホストのプライベート判定、リダイレクト検査）、受信サイズ制限、defusedxml の利用等を行っています。

---

## 追加情報 / 開発者向け

- テスト可能性:
  - OpenAI / HTTP 呼び出し部分はモック差し替えを想定した作り（内部の _call_openai_api や _urlopen をテストでパッチ）になっています。
- 拡張:
  - strategy / execution / monitoring モジュールと接続することで実際の発注フローに統合できます（実稼働時は十分な安全チェックを行ってください）。
- 依存管理・パッケージ化:
  - プロジェクトルートに pyproject.toml / setup.py がある場合はそちらでインストール & テスト実行してください。

---

必要であれば、README に .env.example のテンプレートや、よくあるトラブルシュート（OpenAI のエラー対応、DuckDB ファイル権限、J-Quants トークン更新手順など）を追加できます。どの追加情報がほしいか教えてください。