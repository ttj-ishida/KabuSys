# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）です。  
本リポジトリはデータ収集（J-Quants）、データ品質チェック、ファクター計算、ニュースNLP（OpenAIを利用したセンチメント解析）、市場レジーム判定、監査ログ（トレーサビリティ）など、投資アルゴリズム開発と運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 特徴（概要）

- J-Quants API を用いた株価・財務・市場カレンダーの差分ETL（ページネーション・レート制御・自動リフレッシュ対応）
- DuckDB を用いたローカル永続化（冪等保存：ON CONFLICT DO UPDATE）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS）およびニュースの前処理、SSRF対策、トラッキングパラメータ除去
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄ごとの ai_score）と市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの合成）
- 監査ログ（signal → order_request → executions）テーブルと初期化ユーティリティ
- 研究モジュール：モメンタム／バリュー／ボラティリティ等のファクター計算、将来リターン・IC 計算、Zスコア正規化

設計上の留意点：
- ルックアヘッドバイアス回避のため、内部処理で date.today()/datetime.today() を直接参照しない設計が採用されています（呼び出し側で target_date を明示することを推奨）。
- API 呼び出しは堅牢なリトライ・バックオフ、レート制御を実装。
- ニュース取得・解析においては安全性（SSRF対策、XML安全パーサ）を考慮。

---

## 主な機能一覧

- kabusys.data
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch / save 系関数
  - market_calendar 管理・営業日判定ユーティリティ
  - news_collector: RSS 取得・正規化・保存ユーティリティ
  - data quality チェック: check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
  - audit: 監査テーブル初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize
- kabusys.ai
  - news_nlp.score_news: ニュースセンチメントの集計・ai_scores への書き込み
  - regime_detector.score_regime: 市場レジーム判定（ma200 と マクロニュースの合成）
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- 設定管理: kabusys.config.settings（.env 自動読み込み機能あり）

---

## セットアップ

前提
- Python 3.10 以上（PEP 604 の型シンタックスを使用）
- ネットワーク接続（J-Quants / OpenAI を使用する場合）

依存パッケージ（主要）:
- duckdb
- openai
- defusedxml

インストール（例）:

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクト配布の requirements.txt がある場合は `pip install -r requirements.txt`）

3. 開発モードでインストール（オプション）
   - pip install -e .

環境変数 / .env
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込みます（優先度: OS 環境 > .env.local > .env）。
- 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセット。

主な環境変数（必須/任意）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（実装による）
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー（score_news / score_regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN (任意) — LINE 通知用
- LINE_USER_ID (任意)
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

例（.env の抜粋）
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトでの実行例です。各例では duckdb 接続を作成して関数を呼び出します。

1) ETL（デイリー ETL）実行
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しない場合は today が使われます（ただし内部はルックアヘッド回避のため営業日に調整される）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI 必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None で環境変数 OPENAI_API_KEY を使用
print(f"ai_scores に書き込んだ銘柄数: {written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査DB の初期化（監査ログ専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# 以後 conn を使って監査テーブルへ書き込みが可能
```

5) 設定参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env)
```

注意点：
- score_news / score_regime など OpenAI を呼ぶ関数は api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl は内部で calendar ETL → prices ETL → financials ETL → 品質チェック の順に処理します。各ステップは個別に例外処理され、可能な限り他ステップへ影響を与えない設計です。
- DuckDB の executemany は空リストを許容しないバージョンの差異に合わせた保護コードがあります。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - .env 自動ロード、settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py           — ニュースセンチメント解析と ai_scores 保存
  - regime_detector.py    — ETF 1321 MA200 とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py     — J-Quants API クライアント（取得・保存）
  - pipeline.py           — ETL パイプラインと run_daily_etl（ETLResult）
  - etl.py                — ETLResult の再エクスポート
  - calendar_management.py— 市場カレンダー管理、営業日ユーティリティ
  - news_collector.py     — RSS 取得・前処理・保存（SSRF対策、XML防御）
  - quality.py            — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py              — zscore_normalize 等の統計ユーティリティ
  - audit.py              — 監査ログ DDL / 初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py    — Momentum / Value / Volatility ファクター計算
  - feature_exploration.py— 将来リターン / IC / 統計サマリー等
- research.* その他研究用ユーティリティ
- その他（strategy, execution, monitoring 等のパッケージ名は __all__ に含まれますが、この抜粋では一部実装のみ）

---

## 運用上の注意 / ベストプラクティス

- API キーや機密情報は .env / 環境変数で管理し、リポジトリにコミットしないでください。
- 本ライブラリの AI 機能は外部API（OpenAI）を利用します。コストおよびレイテンシを考慮してバッチサイズや呼び出し頻度を調整してください。
- run_daily_etl 等は cron / CI ワークフローで定期実行する想定です。ETLResult をログ/モニタリングシステムに送ることを推奨します。
- ニュース収集は外部 RSS をスクレイピングするため、各媒体の利用規約・ロボットポリシーに従ってください。
- 本プロジェクトはルックアヘッドバイアス低減を重視した設計です。バックテスト用途で使用する際は、データ収集日時（fetched_at）/ target_date の扱いに注意してください。

---

必要であれば README に以下を追加できます：
- 具体的な API レート制御・リトライの挙動図
- テーブルスキーマの詳細（DDL）
- CI/CD 用の実行例（cron / systemd ユニット）
- サンプル .env.example

追加希望があれば教えてください。