# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター算出、監査ログ（発注・約定トレーサビリティ）などを提供します。

注意: これはライブラリ（パッケージ）用の README であり、実行可能な CLI は別途用意する想定です。下記サンプルは Python API を直接呼ぶ形での利用例です。

---

## プロジェクト概要

- ETL（J-Quants API）で株価・財務・市場カレンダーを差分取得し DuckDB に保存
- ニュース収集（RSS）→ raw_news 保存・銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / マクロセンチメント評価
- 日次レジーム（bull / neutral / bear）判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- 設定は環境変数（または .env / .env.local）で管理。自動ロード機構あり

設計上の特徴:
- ルックアヘッドバイアス対策（datetime.today() を計算内部で参照しない等）
- 冪等性（DB への保存は ON CONFLICT などで上書き）
- API 呼び出しに対するリトライ / バックオフ、フェイルセーフ（API 失敗時は部分スキップして継続）
- DuckDB を中核 DB として使用

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）
- ニュース処理 / NLP
  - RSS 収集（kabusys.data.news_collector）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究（Research）
  - ファクター計算（kabusys.research.factor_research: calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（kabusys.research.feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank）
  - 統計ユーティリティ（kabusys.data.stats.zscore_normalize）
- データ品質チェック（kabusys.data.quality）
- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db：監査用テーブルを初期化
- 設定管理（kabusys.config）
  - .env / .env.local 自動ロード（プロジェクトルート検出）と Settings オブジェクト

---

## セットアップ手順

前提:
- Python 3.10 以上（typing の | を使用）
- DuckDB, OpenAI SDK 等のライブラリが必要

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（例）
   - 実際の requirements.txt がない場合、最低限以下を入れてください：
   ```bash
   pip install duckdb openai defusedxml
   ```
   - パッケージを開発モードでインストールする場合（setup.py / pyproject.toml がある想定）:
   ```bash
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env` と（必要なら）`.env.local` を配置すると自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。
   - 必須環境変数の例:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（news/regime の呼び出し時に使用）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（発注等のため）
   - その他オプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/…
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE（paper_trading 用、instant/partial/never/reject）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID

   例 `.env`（最小）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（主な API とサンプル）

以下は Python REPL やスクリプトから直接呼ぶ例です。

1. DuckDB 接続を作って日次 ETL を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュースのスコアリング（OpenAI を使用）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
   n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
   print("written:", n_written)
   ```

3. 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメント合成）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. 監査ログ DB の初期化（監査専用 DB を作る）
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は監査テーブルが作成された DuckDB 接続
   ```

5. 研究用ユーティリティ（ファクター計算）
   ```python
   from datetime import date
   import duckdb
   from kabusys.research.factor_research import calc_momentum

   conn = duckdb.connect("data/kabusys.duckdb")
   records = calc_momentum(conn, target_date=date(2026, 3, 20))
   ```

注意点:
- OpenAI を使う関数は api_key を引数で受け取れます（テストやキー切り替えに便利）。
- 各関数は「ルックアヘッドバイアス対策」が施されており、内部で現在日時を勝手に参照しない設計です。バックテスト等で使用する際は target_date を明示してください。

---

## 設定（環境変数 / .env）

主要な環境変数（抜粋）：

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（news/regime 等で使用）
- KABU_API_PASSWORD (必須 for kabu station usage)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_FILL_MODE: instant|partial|never|reject（paper trading 用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（デフォルト）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化

設定は kabusys.config.Settings 経由で取得できます:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

自動 .env ロード:
- プロジェクトルートはこのパッケージファイル位置から上の階層に `.git` または `pyproject.toml` を探索して決定されます。
- 自動ロード順序: OS 環境変数 > .env.local (override=True) > .env (override=False)
- テスト等で自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成（主要ファイル）

下記は src/kabusys 以下の主要モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースセンチメント、score_news
    - regime_detector.py              — 市場レジーム判定、score_regime
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント + 保存関数
    - pipeline.py                     — ETL パイプライン / run_daily_etl
    - etl.py                          — ETL 用の型再エクスポート
    - news_collector.py               — RSS 収集・前処理
    - calendar_management.py          — 市場カレンダー管理 / 営業日判定
    - quality.py                      — データ品質チェック
    - stats.py                        — 統計ユーティリティ（z-score）
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py              — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py          — calc_forward_returns / calc_ic / rank / factor_summary

（実際のリポジトリにはさらに strategy / execution / monitoring 等のパッケージ参照用トップレベルがある想定です。kabusys.__all__ には data/ strategy/ execution/ monitoring が公開されています。）

---

## 設計上の重要な注意点 / ベストプラクティス

- ルックアヘッドバイアスに厳格に対処しています。バックテスト等で関数を使う場合は target_date を必ず指定してください。
- DB へ保存する処理は冪等性を重視（ON CONFLICT や個別 DELETE→INSERT の戦略）しています。部分失敗が発生しても既存の有効データを保護する設計です。
- OpenAI/J-Quants 等の外部 API 呼び出しにはリトライ / バックオフを実装。API 失敗時はフェイルセーフでスコア 0 やスキップを行い、処理を継続する箇所が多くあります。
- ニュース収集では SSRF 対策（リダイレクト検査・プライベート IP 拒否）、XML の保護（defusedxml）を行っています。
- ロギングは各モジュールに組み込まれているので運用時は LOG_LEVEL を適切に設定してください。

---

## 追加情報 / 開発者向け

- テスト用のフックやモックポイントが所々に用意されています（例: OpenAI 呼び出し関数を unittest.mock.patch で差し替え可能）。
- DuckDB の互換性対応（executemany の空リスト問題、日付型変換処理など）に配慮した実装が多く含まれます。
- パッケージバージョンは kabusys.__version__ にて管理（現行: 0.1.0）。

---

必要であれば以下を追加します:
- .env.example のテンプレート
- requirements.txt / pyproject.toml の推奨依存関係
- さらに詳しい関数別 API リファレンス
- CI / デプロイ手順（監視・自動再起動等）

要望があれば README の補足（.env.example の具体例、より多くのコードサンプル、CLI スクリプト例など）を作成します。