# KabuSys

日本株自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
ETL / データ品質チェック / ニュース収集・NLP スコアリング / 市場レジーム判定 / 監査ログなど、量的運用に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株を対象とした自動売買・データ基盤モジュール群です。主に以下を提供します。

- J-Quants API との統合（差分 ETL、ページネーション、トークンリフレッシュ、レート制御）
- DuckDB ベースの永続化（raw_prices / raw_financials / market_calendar など）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と LLM を用いた銘柄別/マクロセンチメント評価
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 監査ログ（signal / order_request / executions テーブル）と初期化ユーティリティ
- カレンダー管理（JPX カレンダーの取得・営業日判定）
- 設定管理（.env 自動ロード / 環境変数）

設計方針として「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗時はスキップやデフォルト値）」を重視しています。

---

## 機能一覧

主な機能（モジュール別）:

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - 環境変数ラッパ（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API の取得・保存・認証・レート制御
  - pipeline / etl: 日次差分 ETL（prices / financials / calendar）と ETLResult
  - quality: データ品質チェック（欠損・スパイク・重複・日付整合性）
  - news_collector: RSS 取得・前処理・SSRF対策・raw_news 保存用ユーティリティ
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - audit: 監査ログテーブル初期化 (init_audit_schema / init_audit_db)
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM で銘柄別に評価し ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA とマクロセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

その他:
- DuckDB を用いた SQL ベースのデータ操作（高速な分析処理）
- OpenAI API（gpt-4o-mini 等）の JSON Mode を想定した LLM 呼び出し（冪等・リトライ実装）
- ニュース収集での URL 正規化・ID 生成・受信サイズ制限・XML 派生攻撃対策（defusedxml 使用）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨
- Git、ネットワークアクセス（J-Quants / OpenAI）環境

1. リポジトリをクローン
   - git clone <repo-url>
   - ルートに pyproject.toml や .git がある想定です（config の自動 .env ロードに利用）。

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （必要に応じて追加パッケージをインストールしてください。プロジェクトでは他にも logging, urllib 等の標準ライブラリのみで動作する部分が多いです。）

4. パッケージをインストール（任意）
   - pip install -e .

5. 環境変数（.env）を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
- その他監視関連フラグ（PID_FILE_PATH, KILL_FLAG_PATH 等）

例 .env（簡易）
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## 使い方（代表的な API と実行例）

以下は Python スクリプトや REPL から直接呼び出す代表的な例です。

- DuckDB 接続を開く（例）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は today）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニューススコア（LLM）を計算して ai_scores に保存
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB の初期化（監査専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- 研究用ファクターを計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

factors = calc_momentum(conn, target_date=date(2026, 3, 20))
# z スコア正規化例
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(factors, ["mom_1m", "mom_3m", "mom_6m"])
```

- ニュース収集（RSS を取得して raw_news に保存する処理は news_collector の上位ラッパー実装を想定）
  - fetch_rss は URL のバリデーションや SSRF 防御・gzip 対応を行います。
  - RSS から得た記事を DB に入れる処理はプロジェクト側でトランザクションを用いて実行してください。

テスト時のハック（OpenAI API をモックする場合）
- 単体テストでは次の内部関数を patch すると LLM 呼び出しを差し替えられます:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api

---

## 設定（settings）について

コード上で settings オブジェクトを介して設定値にアクセスできます（kabusys.config.settings）。

主なプロパティ：
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url
- settings.line_channel_access_token / settings.line_user_id
- settings.duckdb_path / settings.sqlite_path
- settings.pid_file_path / settings.kill_flag_path / settings.kill_flag_clear_on_start
- settings.cpu_threshold_pct / settings.memory_threshold_pct / settings.disk_threshold_pct
- settings.env / settings.log_level / settings.is_live / settings.is_paper / settings.is_dev

.env 自動読み込みの挙動:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に `.env` → `.env.local` の順で読み込みます。
- OS 環境変数は上書きされません（`.env.local` は上書き可）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須環境変数については settings の該当プロパティ（例: jquants_refresh_token）が呼ばれた時点でチェックされ、未設定の場合は ValueError を送出します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - quality.py
  - stats.py
  - news_collector.py
  - calendar_management.py
  - audit.py
  - (その他 ETL ヘルパなど)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (パッケージエクスポートに含まれる想定)
- execution/, strategy/ など（パッケージエクスポートに含まれる想定）

（上記はコードベースの主要ファイルを抜粋しています）

---

## 注意点 / 運用上の留意事項

- 「ルックアヘッドバイアス防止」のため、多くの関数は内部で datetime.today()/date.today() を直接参照しない設計です。バックテストやバッチ運用では target_date を明示的に渡してください。
- OpenAI / J-Quants API 呼び出し部分はリトライ・バックオフ・フェイルセーフを実装していますが、API料金やレート制限には注意してください。
- news_collector は外部から取得した XML を処理するため defusedxml を使い XML 系攻撃対策をしています。RSS ソースの信頼性とパブリックアクセスに注意してください。
- DuckDB の executemany に関するバージョン差異（空リスト不可など）を考慮した実装になっていますが、使用する DuckDB のバージョンで互換性を確認してください。
- 監査ログテーブルは削除しない前提（ON DELETE RESTRICT）です。運用上のパージポリシーは別途設計してください。

---

## 連絡先・貢献

この README はコードベースの現状を要約したもので、詳細な API や運用手順はプロジェクトの設計ドキュメント（StrategyModel.md / DataPlatform.md 等）を参照してください。バグ報告・提案は Issue を立ててください。

--- 

以上。README に追加したいサンプルコマンドや CI 手順、requirements.txt の内容など要望があれば教えてください。