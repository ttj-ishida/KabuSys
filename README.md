# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants API からデータを取得して DuckDB に保存し、ニュースセンチメント / 市場レジーム判定 / ファクター計算 / データ品質チェック / 監査ログ等の機能を提供します。設計はルックアヘッドバイアス対策や冪等性・堅牢な API リトライを重視しています。

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単な例）
- 環境変数（主要）
- ディレクトリ構成

---

## プロジェクト概要
- J-Quants API から株価・財務・マーケットカレンダーを差分取得し DuckDB に格納する ETL パイプライン。
- RSS ニュース収集と LLM を用いたニュースセンチメント（銘柄別）評価。
- ETF を用いた市場レジーム（bull/neutral/bear）判定（移動平均 + マクロニュースセンチメントの合成）。
- ファクター計算（モメンタム・バリュー・ボラティリティ等）・特徴量探索（将来リターン、IC 等）。
- データ品質チェック（欠損・スパイク・重複・日付不整合）。
- 取引監査ログ（signal / order_request / executions）用のスキーマ初期化ユーティリティ。

設計上のポイント：
- ルックアヘッドバイアスを避ける（内部で date.today() を安易に参照しない実装）。
- DuckDB を主要なデータストアに採用。
- J-Quants / OpenAI 呼び出しに堅牢なリトライ・レート制御を実装。
- .env の自動読み込み機能を持つ（配布後も安全に動作するようプロジェクトルート探索あり）。

---

## 機能一覧（主なモジュール）
- kabusys.config
  - 環境変数読み込み・設定ラッパー（自動 .env ロード、必須チェック）。
- kabusys.data
  - pipeline: ETL の実行（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - jquants_client: J-Quants API の取得・保存ユーティリティ（rate limit / token refresh / save_*）
  - news_collector: RSS 取得・前処理・raw_news 保存
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースで市場レジームを判定
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

1. リポジトリをクローン（省略）

2. Python 仮想環境を作成・有効化（例）
```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows (PowerShell 等)
```

3. 依存パッケージをインストール
（requirements.txt がある想定、または最低限以下をインストール）
```bash
pip install duckdb openai defusedxml
# 他に必要なライブラリがあれば追加でインストールしてください
```

4. パッケージを開発モードでインストール（プロジェクトルートに setup.cfg/pyproject.toml がある場合）
```bash
pip install -e .
```

5. 環境変数の設定
- プロジェクトルートに `.env` または `.env.local` を作成し、下記の必須変数を設定します（例は後述）。
- 自動読み込みはデフォルトで有効。テスト等で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

6. DuckDB の初期化（監査 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で参照）
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン（通知用途）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — データ用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")

注意: 必須変数は kabusys.config.Settings のプロパティで _require によってチェックされ、未設定時は ValueError を発生させます。

---

## 使い方（簡単な例）

事前準備: DuckDB 接続（例：ファイル DB を使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行（市場カレンダー取得 → 株価/財務取得 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを計算して ai_scores に保存
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"written: {n_written}")
```

3) 市場レジームスコアを計算して market_regime テーブルに保存
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) ファクター計算（research）
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

5) 監査スキーマ初期化（既存 DB に追加）
```python
from kabusys.data.audit import init_audit_schema
# conn は既に接続された duckdb 接続
init_audit_schema(conn, transactional=True)
```

---

## 運用上の注意
- OpenAI / J-Quants の API 呼び出しにはキーが必要です。テスト時は各モジュールの内部呼び出し関数をモックしてください。
- news_nlp / regime_detector は外部 LLM に依存するため、API の失敗時はフェイルセーフ（0.0 など）で継続する設計です。しかし結果の品質に影響するため監視を推奨します。
- ETL の差分ロジックは既存データの最終日から backfill を行うため、初回は長めに取得されます。
- calendar_management は market_calendar が不十分な場合に曜日ベースでフォールバックしますが、本番では JPX カレンダーの取得を確実に行ってください。
- DuckDB に対する executemany の空パラメータなど、古いバージョン固有の仕様を考慮した実装になっています。DuckDB の互換性に注意してください。

---

## ディレクトリ構成 (抜粋)
プロジェクトは src/kabusys 以下に実装されています。主要ファイル・ディレクトリと説明は以下の通り。

- src/kabusys/
  - __init__.py — パッケージ定義、__version__
  - config.py — 環境変数 / 設定の管理（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM による銘柄別センチメント（score_news）
    - regime_detector.py — ETF + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py — J-Quants API クライアント（fetch / save 関数）
    - news_collector.py — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py — データ品質チェック群
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログスキーマ定義と初期化（init_audit_schema / init_audit_db）
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank
  - research/*（補助的な分析ツール等）
  - その他モジュール（strategy / execution / monitoring 等はパッケージ外観に含まれる想定）

---

## 最後に / 開発メモ
- テストを行う際は外部 API 呼び出しをモックしてください（news_nlp._call_openai_api など、モジュール内の呼び出しを個別に差し替える設計です）。
- .env の自動読み込みはプロジェクトルート (.git または pyproject.toml を基準) を探索して行います。CI やテストで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 実運用環境では KABUSYS_ENV を "paper_trading" や "live" に設定して取り扱いを分けてください。

README に記載されていない細かな API や戻り値の仕様はソースコメント（docstring）を参照してください。必要であれば、より具体的な操作例・スクリプト・運用手順を追加で作成できます。