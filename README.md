# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ集です。  
主に以下を提供します。

- J-Quants API からの差分 ETL（株価・財務・カレンダー）
- ニュースの収集・NLP スコアリング（OpenAI を用いたセンチメント）
- 市場レジーム判定（ETF とマクロニュースの合成）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）用スキーマ初期化
- 研究（ファクター計算・IC / フォワードリターン等）のユーティリティ
- データ品質チェック、カレンダー管理、ニュース収集などのユーティリティ群

このリポジトリはライブラリ群として設計されており、実際の注文発行ロジックや運用ランナーは含まれていません。バックテスト・研究用途および運用バッチを組むための基盤を提供します。

---

## 主な機能一覧

- Data ETL
  - J-Quants からの株価日足・財務・上場情報・市場カレンダー取得（ページネーション・レート制御・再試行対応）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL エントリ run_daily_etl（カレンダー調整・バックフィル・品質チェック含む）
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合等の検出
- ニュース処理（news_collector / news_nlp）
  - RSS 収集（SSRF 対策・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント集約（batch, JSON mode, リトライ）
- 市場レジーム判定（regime_detector）
  - ETF（1321）の 200 日 MA 乖離とマクロニュース LLM センチメントを合成して日次レジーム判定
- 研究ツール（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のスキーマ定義と初期化ユーティリティ
- 設定管理（config）
  - .env / .env.local 自動読み込み（プロジェクトルート判定）と Settings API

---

## 前提 / 必要環境

- Python 3.10+
  - （モジュール内でパイプライン型ヒント（A | B）や型アノテーションを使用）
- 主な依存パッケージ
  - duckdb
  - openai
  - defusedxml
- その他：標準ライブラリを広く利用（urllib, json, datetime, logging 等）

requirements.txt がない場合は最低限以下をインストールしてください（例）:

pip install duckdb openai defusedxml

必要に応じて slack 連携等の追加パッケージを導入してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 依存パッケージをインストール
   - pip install -e .   # パッケージセットアップがある場合
   - または: pip install duckdb openai defusedxml
4. 環境変数（.env）を用意
   - プロジェクトルートに `.env` として配置すると自動読み込みされます（.git または pyproject.toml を基準にルート探索）
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
5. 必須の環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...  # OpenAI を使う機能を利用する場合
   - （オプション）DUCKDB_PATH=data/kabusys.duckdb
   - （オプション）SQLITE_PATH=data/monitoring.db
   - （オプション）KABUSYS_ENV=development|paper_trading|live
   - （オプション）LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

サンプル .env（プロジェクトルート）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的な API / ワークフロー）

以下は簡単な Python スニペット例です。実運用ではログ設定、例外ハンドリング、ジョブスケジューラなどを組み合わせてください。

- DuckDB 接続の取得（例: settings で指定したパスを使用）

from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行（株価 / 財務 / カレンダーの差分 ETL + 品質チェック）

from datetime import date
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())

- ニュースのセンチメントスコアを生成（OpenAI のキーは env または引数で）

from kabusys.ai.news_nlp import score_news
from datetime import date
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("written:", n_written)

- 市場レジームをスコアリングして保存

from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査用 DuckDB を初期化（別 DB で管理することを推奨）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn は初期化済みの接続を返す

- 研究用ファクター計算（例: momentum）

from kabusys.research.factor_research import calc_momentum
from datetime import date
factors = calc_momentum(conn, target_date=date(2026,3,20))

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数を受け取ります。None の場合は環境変数 OPENAI_API_KEY を参照します。
- 外部 API 呼び出し（J-Quants / OpenAI）は呼び出し元で適切に例外処理してください。モジュール側でもフォールバック/安全措置は実装されていますが、運用側の再試行戦略は別途必要です。

---

## 主な設定項目（環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu ステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: sqlite（監視用）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU/MEM/DISK 閾値等: 監視用設定
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化します

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定読み込み
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースセンチメント（OpenAI）
  - regime_detector.py             — マーケットレジーム判定
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント & 保存
  - pipeline.py                    — ETL パイプラインと run_daily_etl
  - etl.py                         — ETLResult 再エクスポート
  - calendar_management.py         — 市場カレンダー管理ユーティリティ
  - news_collector.py              — RSS 取得 / 正規化 / 保存
  - quality.py                     — データ品質チェック
  - stats.py                       — 共通統計ユーティリティ（zscore 等）
  - audit.py                       — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py             — Momentum / Volatility / Value 等
  - feature_exploration.py         — 将来リターン・IC・統計サマリー etc.
- ai/..., research/..., data/...   — 各モジュールの詳細実装ファイル

（上記はリポジトリ内の主なファイルを抜粋しています）

---

## 運用上の注意 / 設計方針（抜粋）

- Look-ahead bias を避けるため、ほとんどの処理は明示的な target_date を受け取り、内部で datetime.today() を直接参照しない設計になっています。
- J-Quants / OpenAI 呼び出しはリトライ／バックオフ／レート制御を実装していますが、運用では更に監視・アラートや再試行ポリシーを設けることを推奨します。
- DuckDB への書き込みは基本的に冪等（ON CONFLICT）を前提にしており、部分失敗時のデータ保護を意識した設計です。
- ニュース収集は SSRF や XML 脆弱性対策（defusedxml）などセキュリティ配慮が組み込まれています。

---

## 開発・テスト

- 自動ロードされる .env をテストから隔離したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（config モジュールで検出）。
- OpenAI / J-Quants など外部 API を呼ぶ箇所はモック容易に実装されています（内部の API 呼び出しラッパーをパッチ可能）。

---

もし README に追加したい具体的な実行スクリプト（systemd ユニット例、cron / Airflow タスク例）、CI 設定、あるいは .env.example の詳細テンプレートが必要であれば教えてください。README を用途（開発者向け／運用者向け）に合わせて拡張します。