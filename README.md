# KabuSys — 日本株自動売買基盤ライブラリ

KabuSys は日本株向けのデータプラットフォーム、分析、AI を用いたニュースセンチメント・市場レジーム判定、監査ログ、ETL パイプライン等を備えたライブラリ群です。本リポジトリは DuckDB を中心としたローカルデータベースへデータを保存し、J-Quants API / RSS / OpenAI を活用して自動化バッチ処理・研究用途に対応します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しない等）
- DuckDB を用いた効率的な SQL 処理
- 外部 API 呼び出しにはリトライ・レート制御を実装
- ETL / 品質チェックは冪等性・部分失敗耐性を重視

---

## 特徴（機能一覧）

- データ取得・ETL
  - J-Quants API クライアント（株価日足 / 財務 / JPX カレンダー）
  - 差分取得／ページネーション対応／トークン自動更新
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集・NLP（AI）
  - RSS フィード収集・前処理（SSRF 対策、トラッキング除去、サイズ制限）
  - ニュース × 銘柄の集約 → OpenAI によるバッチセンチメント評価（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成、score_regime）

- 研究（Research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等
  - Z スコア正規化ユーティリティ

- 監査・トレーサビリティ
  - signal_events, order_requests, executions 等の監査テーブル定義
  - 監査 DB 初期化ユーティリティ（init_audit_db / init_audit_schema）

- 設定管理
  - .env / 環境変数自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で安全に設定参照

---

## 必要条件（依存関係）

主に以下のパッケージが必要です（要件はプロジェクトに合わせて適宜追加してください）：

- Python 3.10+
- duckdb
- openai
- defusedxml

pip の requirements ファイルを用意している場合はそちらを利用してください。例（プロジェクトに合わせて適宜変更）:

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または個別に pip install duckdb openai defusedxml

4. 環境変数 / .env を準備
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に `.env` と `.env.local` を設置できます。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須の環境変数（Settings により参照されるもの）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD：kabu API のパスワード（発注等の将来的機能向け）
- SLACK_BOT_TOKEN：Slack 通知用トークン（通知を使う場合）
- SLACK_CHANNEL_ID：Slack チャンネル ID（通知を使う場合）

OpenAI を使う機能を利用する場合
- OPENAI_API_KEY：OpenAI API キー（score_news / score_regime で使用）

任意（デフォルト値あり）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

.env の簡単な例（プロジェクトルートに配置）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

---

## 使い方（主なユースケース）

以下はライブラリを直接インポートして使う例です。実行には DuckDB データベースファイルへの書き込み権限が必要です。

1) DuckDB 接続を作る（監査 DB 初期化例）

from pathlib import Path
import duckdb
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)  # ファイルがなければ親ディレクトリを自動作成して初期化

2) 日次 ETL を実行してデータ取得（J-Quants のトークンが設定済みであること）

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) ニュースセンチメントスコア（ai.news_nlp.score_news）

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None: 環境変数 OPENAI_API_KEY を使用
print(f"written {written_count} scores")

4) 市場レジーム判定（ai.regime_detector.score_regime）

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

5) 研究機能（ファクター計算や前方リターン等）

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
forward = calc_forward_returns(conn, date(2026, 3, 20))
ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")
print("IC:", ic)

6) データ品質チェック全実行

from datetime import date
import duckdb
from kabusys.data.quality import run_all_checks

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)

メモ:
- OpenAI 呼び出しはネットワークやレート制限で失敗する場合があるため、score_news / score_regime はフォールバック（スコア=0 等）やログ出力を行います。
- ETL 関連は J-Quants API に依存します。初回は J-Quants のリフレッシュトークン設定と API 利用可能か確認してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数・設定管理（settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントを OpenAI で評価、ai_scores へ書き込み
  - regime_detector.py — ETF 1321 MA200 とマクロニュース合成による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limit）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETLResult の再エクスポート
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック
  - news_collector.py — RSS フィード収集、前処理、raw_news 保存
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - audit.py — 監査ログ用スキーマ定義 & 初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティ算出
  - feature_exploration.py — 将来リターン / IC / 統計サマリ

---

## 注意点・運用上のメモ

- 自動で .env を読み込む処理はプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト環境などで自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の出力は JSON mode（response_format）に依存していますが、稀に余計な前後テキストが混入することがあるためライブラリ内で復元処理・バリデーションを行っています。
- J-Quants API 呼び出しは固定間隔スロットリングとリトライを行うため、短時間に大量リクエストを投げないでください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンの挙動を考慮した実装になっています（空チェックあり）。
- 監査テーブルは削除しない運用を想定しており、order_request_id による冪等性を重視しています。

---

必要であれば README に以下を追加できます：
- 具体的な SQL スキーマ（テーブル定義）
- CI / デプロイ手順（コンテナ化や systemd サービス等）
- 開発用の make コマンドやテスト実行手順

追加希望があれば教えてください。