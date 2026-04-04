# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。J-Quants からの市場データ取得・ETL、ニュース収集・LLM を使ったニュースセンチメント評価、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、取引アルゴリズム開発と運用に必要な機能群を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「DuckDB を中心としたローカル永続化」「API 呼び出しのフェイルセーフと冪等性」です。

---

目次
- プロジェクト概要
- 機能一覧
- 要件／依存関係
- セットアップ手順
- 環境変数（.env）と自動ロード
- 使い方（主要 API の例）
- ディレクトリ構成（ファイル一覧と説明）
- 補足 / 注意点

---

## プロジェクト概要

KabuSys は以下を主眼に置いたモジュール群の集合です。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）と LLM を用いた銘柄別ニュースセンチメント付与
- 日次の市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 研究用のファクター計算・特徴量解析ユーティリティ
- 監査ログ用スキーマ（シグナル→発注→約定のトレース）
- DuckDB によるローカル DB 保存、冪等的な保存ロジック

本 README ではセットアップと主要な使い方を紹介します。

---

## 機能一覧

- data
  - jquants_client: J-Quants へのリクエスト（レートリミット、リトライ、トークンリフレッシュ付き）
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - calendar_management: 営業日判定 / 前後営業日の検索 / カレンダー更新ジョブ
  - news_collector: RSS 収集、前処理、raw_news 保存
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit: 監査ログスキーマの初期化（signal_events, order_requests, executions）
  - stats: zscore 正規化等の統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを LLM に投げ銘柄別 ai_score を ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM センチメントを合成して market_regime に保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings: 環境変数ベースの設定管理（.env の自動ロードも提供）

---

## 要件／依存関係

- Python 3.10 以上（コード内での型ヒント `X | None` を使用）
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで賄える部分も多いですが、上記パッケージは主要機能に必須です。

インストール例（仮）:
pip install duckdb openai defusedxml

（実際はプロジェクトに requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （実際のパッケージはプロジェクトの requirements.txt / pyproject.toml を参照してください）

3. 環境変数 (.env) を用意
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）に .env を配置すると自動で読み込まれます（後述）。

4. DuckDB ファイル等の準備
   - デフォルトでは data/kabusys.duckdb, data/monitoring.db などを使用します。必要に応じてディレクトリを作成してください（モジュール側が自動で作ることもありますが、権限等に注意）。

5. Optional: 監査 DB 初期化
   - kabusys.data.audit.init_audit_db を用いて監査用 DuckDB を初期化します。

---

## 環境変数（.env）と自動ロード

kabusys.config.Settings が環境変数を参照して各種設定を提供します。主なキー:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API を使う場合のパスワード

任意 / デフォルト値あり
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY — OpenAI 呼び出しに必要（score_news や regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知に使う場合
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/...

自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env を自動読み込みします。読み込み順は OS 環境 > .env.local (override) > .env。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

.env の例:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要 API とサンプル）

以下は主要な処理の Python からの呼び出し例です。事前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY）を設定してください。

- DuckDB 接続準備（設定を使う例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（指定日分）を計算して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"スコアを書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを用いる）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
volatility = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

- 監査ログスキーマ初期化（別 DB にする場合の例）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # 既定のパスを使用する例
```

注意:
- OpenAI を使用する関数（score_news, score_regime など）は OPENAI_API_KEY を必要とします。api_key を直接引数で渡すこともできます。
- DuckDB における write 操作は多くが冪等（ON CONFLICT DO UPDATE / DO NOTHING）で安全に実行されます。

---

## ディレクトリ構成（主要ファイルと説明）

以下は `src/kabusys` 内の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義（version）
  - config.py — 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py — ai API の公開
    - news_nlp.py — ニュース NLP（LLM による銘柄別センチメント算出、ai_scores への書込）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（レート制御・リトライ・保存処理）
    - pipeline.py — ETL パイプライン（run_daily_etl 他）
    - calendar_management.py — 市場カレンダー管理（営業日判定、calendar_update_job）
    - news_collector.py — RSS ニュース収集・前処理
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - etl.py — ETLResult の再エクスポート
    - audit.py — 監査ログスキーマ定義と初期化ロジック
  - research/
    - __init__.py — 研究 API の公開
    - factor_research.py — ファクター計算（モメンタム / バリュー / ボラティリティ）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

（各モジュールは README の概要に記載した挙動・設計方針に沿って実装されています。詳細はソースコードの docstring を参照してください。）

---

## 補足 / 注意点

- Python バージョン: 型アノテーション（`X | None`）やその他構文に対応する Python 3.10 以上を推奨します。
- セキュリティ:
  - news_collector は SSRF 対策（プライベートホスト検出、リダイレクト検査）や XML パースの安全化（defusedxml）を実装していますが、公開環境での運用前に追加の監査を行ってください。
  - J-Quants や OpenAI の API キーは安全に管理してください。
- 実行環境:
  - 本ライブラリは本番発注処理（kabuステーション等）への連携機能を含みます。paper_trading / live 等の環境フラグを適切に設定して、誤発注を防いでください（KABUSYS_ENV）。
- テスト:
  - OpenAI や外部ネットワーク呼び出しはモック化してユニットテストを実行する想定です。モジュール内の _call_openai_api などはパッチして挙動を安定化できます。
- ロギング:
  - Settings.log_level を用いてログレベルを制御します。ETL / データ品質チェックは多くログを出力しますので運用時のログ設定を検討してください。

---

必要であれば、README にサンプル .env.example、requirements.txt、または CI / デプロイ手順（systemd サービス例、cron での ETL 実行など）を追加できます。どの部分を拡張したいか教えてください。