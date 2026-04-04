# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。ETL、ニュース収集・NLP、マーケットレジーム判定、ファクター計算、監査ログ等の機能を備え、DuckDB を中心にデータパイプラインや研究ワークフロー、実行監視をサポートします。

---

## 主な特徴（概要）

- ETL（J-Quants からの株価・財務・カレンダー取得）と品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と LLM による銘柄別ニュースセンチメント算出（OpenAI）
- マクロニュース + ETF（1321）200日移動平均乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量探索ユーティリティ（forward returns / IC / summary）
- DuckDB を用いた監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ
- J-Quants クライアント（レートリミット・リトライ・トークンリフレッシュ対応）
- .env / 環境変数ベースの設定管理（自動ロード機構付き）

---

## 機能一覧（モジュール別）

- kabusys.config
  - 環境変数管理、自動 .env ロード（.env → .env.local、OS 環境変数を優先）
  - 主な設定: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, KABU_API_BASE_URL, DUCKDB_PATH, など
- kabusys.data
  - jquants_client: J-Quants API 取得 / DuckDB 保存（差分取得・ページネーション対応）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（ETL パイプライン）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - news_collector: RSS 収集と前処理（SSRF 対策・XML ハードニング）
  - audit: 監査ログスキーマ定義と初期化（冪等、UTC タイムスタンプ）
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - stats: zscore 正規化などの統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント算出・ai_scores 書き込み
  - regime_detector.score_regime: ETF（1321）MA とマクロセンチメント合成による市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提・要件

- Python 3.10 以上（型注釈に `X | Y` を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - openai (v1 SDK の OpenAI クライアントを使用)
  - defusedxml
- ネットワークアクセス: J-Quants API, OpenAI, RSS ソース など
- J-Quants リフレッシュトークン、OpenAI API キーなどの外部認証情報

（インストール用の pyproject / requirements ファイルがある前提で `pip install -e .` / `pip install -r requirements.txt` を推奨）

---

## セットアップ手順

1. リポジトリをクローン（プロジェクトルートに pyproject.toml や .git があることを想定）
   - git clone ...
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject があれば `pip install -e .`）
4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、システム環境変数として必要なキーをセットします。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=your_openai_api_key
     - KABU_API_PASSWORD=your_kabu_station_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - LINE_CHANNEL_ACCESS_TOKEN=
     - LINE_USER_ID=
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development  # development | paper_trading | live
     - LOG_LEVEL=INFO
   - 自動 .env ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

サンプル .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡易ガイド）

以下は一般的な利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の返り値）を受け取ります。

- DuckDB に接続する（ファイルは settings.duckdb_path が既定）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（市場カレンダー・株価・財務を差分取得して品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（target_date に対する前日15:00～当日08:30 JST のウィンドウ）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written_count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み件数: {written_count}")
```

- 市場レジーム判定を実行（ETF 1321 の MA とマクロセンチメントを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマを初期化（監査用 DB を新規作成して初期化する）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # または別ファイルパス
```

- ファクター計算 / 研究用関数
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は [{ "date": ..., "code": "1234", "mom_1m": ..., ...}, ...]
```

注意点:
- OpenAI 呼び出しを行う機能（news_nlp, regime_detector）は OPENAI_API_KEY が必要です。api_key を直接渡すこともできます（引数 api_key）。
- J-Quants 呼び出しは JQUANTS_REFRESH_TOKEN を必要とします。get_id_token() が内部で使用します。
- ETL は外部 API に依存するためネットワーク環境と API レート制限・認証情報を適切に設定してください。

---

## 自動環境変数読み込みの挙動

- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env`→`.env.local` の順で読み込みます。
- OS 環境変数は上書きされません（.env.local は上書きし得るが OS 環境変数は protected）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時などに有用）。

---

## 主要なディレクトリ構成（ソースツリー抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — 銘柄別ニュース NLU / スコア書込
    - regime_detector.py     — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - news_collector.py      — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理／営業日ロジック
    - audit.py               — 監査ログスキーマ初期化
    - stats.py               — 統計ユーティリティ（zscore 等）
    - etl.py                 — ETL インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — forward returns / IC / summary
  - research/* (その他研究用ユーティリティ)
- pyproject.toml (想定)
- .env.example (推奨して追加)

---

## 動作上の注意（運用・開発）

- Look-ahead バイアス防止: ほとんどの関数は内部で datetime.today() / date.today() を直接参照せず、明示的な target_date を受け取るように設計されています。バックテストでは target_date を明示的に渡してください。
- OpenAI 呼び出しは JSON Mode を使用し、API エラー・パースエラー時はフェイルセーフでスコアを 0.0 に落とす実装が含まれます（システムの継続性優先）。
- J-Quants クライアントはレート制限（120 req/min）を意識した内部レートリミッターとリトライを実装しています。
- DuckDB の executemany に関わる互換性注意（空の params での挙動）に配慮したコードになっています。
- RSS 取得は SSRF / XML 攻撃に対する防御措置（URL 正規化、ホスト検査、defusedxml 利用、最大バイト制限）を実装しています。

---

## 貢献 / 拡張案

- 追加のニュースソースや RSS フィードの管理を外部設定化
- 監視・実行モジュール（execution / monitoring）との連携（現在 __all__ に含まれるが実装拡張の余地あり）
- ポートフォリオ管理・注文送信（kabu API 連携）の実装（kabu_api_password と kabu_api_base_url を利用）

---

問題や改善案、具体的な使い方のサンプル（スクリプト化や CI 実行例）が必要であれば、用途に合わせた README の追加節や実行スクリプト例を作成します。どのユースケース（ETL バッチ/監査DB初期化/ニューススコアリング/レジーム判定 等）を優先しますか？