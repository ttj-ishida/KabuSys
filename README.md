# KabuSys

日本株向けのデータプラットフォーム兼自動売買ユーティリティ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、LLM を用いた市場レジーム判定、ファクター算出・分析、監査ログ（発注 → 約定トレース）などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（バックテストでの将来情報参照を避ける実装）
- DuckDB を用いたローカル永続化（冪等な保存）
- API 呼び出しのリトライ・レート制御（J-Quants / OpenAI）
- セキュリティ配慮（RSS の SSRF 対策、XML に対する防御）
- 部分失敗耐性（ETL や LLM 呼び出しのフェイルセーフ）

バージョン: 0.1.0

---

## 機能一覧

- data
  - ETL パイプライン: run_daily_etl（株価 / 財務 / カレンダー取得、品質チェック）
  - J-Quants クライアント: データ取得（株価日足 / 財務 / 上場銘柄 / マーケットカレンダー）、保存関数（DuckDB へ冪等保存）
  - カレンダー管理: 営業日判定 / next/prev_trading_day / calendar_update_job
  - ニュース収集: RSS フィード取得、前処理、raw_news / news_symbols への保存（SSRF 対策、サイズ制限等）
  - 品質チェック: 欠損・スパイク・重複・日付不整合の検出（QualityIssue）
  - 監査ログ: signal_events / order_requests / executions テーブルの初期化・操作ヘルパー
  - 統計ユーティリティ: zscore_normalize など
- ai
  - news_nlp: RSS のニュースを LLM（gpt-4o-mini 等）で銘柄ごとにセンチメントスコア化し ai_scores に書き込む（バッチ送信、JSON mode、リトライ）
  - regime_detector: ETF（1321）200日 MA 乖離とマクロニュース（LLM）を合成して日次市場レジーム判定（bull/neutral/bear）
- research
  - ファクター計算: モメンタム / バリュー / ボラティリティ 等
  - 特徴量探索: 将来リターン計算 / IC 計算 / 統計サマリー 等
- config
  - 環境変数読み込み（.env / .env.local の自動ロード、環境変数保護）、Settings オブジェクト

主な設計上の安全機能・注意点（抜粋）：
- J-Quants の API レート制御（120 req/min）
- OpenAI 呼び出しは冪等・リトライ・パース失敗時はフォールバック（0.0）
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要条件（推奨）

- Python 3.10+
- DuckDB（Python パッケージ）
- openai（OpenAI Python SDK）
- defusedxml（RSS の安全な XML パース）
- その他: 標準ライブラリ以外の依存パッケージを requirements.txt 等で管理してください。

例（仮）:
pip install duckdb openai defusedxml

※ 実際のアプリでは extras や requirements ファイルを用意してください。

---

## セットアップ手順

1. リポジトリをクローン / コードを配置
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .\.venv\Scripts\activate
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - その他、プロジェクト固有の依存があれば追加でインストールしてください
4. 環境変数を設定（.env をプロジェクトルートに配置）
   - 自動ロード: パッケージインポート時に .env / .env.local を自動検出して読み込みます（プロジェクトルートは .git または pyproject.toml を基準に探索）
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット

推奨する .env のキー（最低限必要なもの）:
- JQUANTS_REFRESH_TOKEN=<あなたの J-Quants リフレッシュトークン>
- KABU_API_PASSWORD=<kabu ステーション API パスワード>
- SLACK_BOT_TOKEN=<Slack Bot トークン>
- SLACK_CHANNEL_ID=<Slack 通知先チャンネルID>
- OPENAI_API_KEY=<OpenAI API キー>  # ai モジュール利用時に必要
- KABUSYS_ENV=development  # 有効値: development / paper_trading / live
- LOG_LEVEL=INFO
- DUCKDB_PATH=data/kabusys.duckdb  # 省略時のデフォルト
- SQLITE_PATH=data/monitoring.db

例 (.env.example)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（例）

まず Settings と DB 接続を取得する例：

from kabusys.config import settings
import duckdb

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))

日次 ETL を実行する（J-Quants からデータを取得して保存、品質チェックまで）:

from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

ニューススコアリング（LLM で銘柄別センチメントを ai_scores に書き込む）:

from kabusys.ai.news_nlp import score_news
from datetime import date

# APIキーを明示的に渡すことも可能（None の場合は OPENAI_API_KEY 環境変数を参照）
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)

市場レジーム判定（1321 の MA とマクロニュースを合成）:

from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

監査ログ（発注／約定トレース）用 DB の初期化:

from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# 監査専用 DB を作成して接続を得る（:memory: も可）
audit_conn = init_audit_db(settings.duckdb_path)

J-Quants クライアントを直接利用する例（テスト / ad-hoc）:

from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,1))

ローカルテスト・モックのヒント:
- OpenAI 呼び出しはモジュール内の _call_openai_api を unittest.mock.patch で差し替え可能（news_nlp / regime_detector 両方でテスト可能）。
- .env 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動でテスト用環境を注入。

---

## 設定詳細

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env → .env.local の順で読み込みます。
  - OS 環境（process env）が優先され、.env.local は既存の OS 環境を上書きします（ただし protected keys は保護されます）。
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings（kabusys.config.Settings）
  - jquants_refresh_token: JQUANTS_REFRESH_TOKEN 必須
  - kabu_api_password: KABU_API_PASSWORD 必須
  - kabu_api_base_url: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - slack_bot_token / slack_channel_id: Slack 通知に必須
  - duckdb_path: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - sqlite_path: SQLITE_PATH（デフォルト data/monitoring.db）
  - env: KABUSYS_ENV（development / paper_trading / live）
  - log_level: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## ディレクトリ構成

src/kabusys/
- __init__.py
- config.py                          — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                       — ニュースの LLM スコアリング（ai_scores へ書込）
  - regime_detector.py                — 市場レジーム判定（ETF 1321 MA + マクロ LLM）
- data/
  - __init__.py
  - jquants_client.py                 — J-Quants API クライアント + 保存ユーティリティ
  - pipeline.py                       — ETL パイプライン（run_daily_etl など）
  - etl.py                            — ETL 公開インターフェース（ETLResult 再エクスポート）
  - news_collector.py                 — RSS 収集・前処理・保存（SSRF 対策）
  - calendar_management.py            — 市場カレンダー / 営業日判定
  - stats.py                          — zscore_normalize 等の統計ユーティリティ
  - quality.py                        — データ品質チェック
  - audit.py                          — 監査ログ（signal / order / execution）DDL・初期化
- research/
  - __init__.py
  - factor_research.py                — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py            — 将来リターン / IC / 統計サマリー 等
- research パッケージは data.stats を利用してファクターの正規化などを行います

（上記は主要ファイルのみ抜粋）

---

## 注意事項 / トラブルシューティング

- OpenAI / J-Quants API キーは必須の操作があるため .env に正しく設定してください。キーが無い場合は ValueError が投げられます。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、コード内で明示的に空チェックをしています。古い DuckDB を使う場合は互換性に注意してください。
- news_collector は外部 RSS にアクセスするため、ネットワーク・DNS の状態やホストの IP 解決に依存します。SSRF 対策によりプライベートアドレスへは接続しません。
- ETL や LLM の呼び出しで一部ステップが失敗しても他のステップは継続する設計です。run_daily_etl は ETLResult を返し、errors / quality_issues を確認してください。
- 開発環境・paper_trading・live を KABUSYS_ENV で切り替え可能です。live モードでは発注・実取引に繋がる処理を有効にするような実装・設定を行ってください（本リポジトリの範囲外の運用ルールも必要）。

---

README に記載した以外にも細かいユーティリティ・設計上の配慮（ルックアヘッド防止、ログ出力、リトライ戦略など）が各モジュールにコメントとして記載されています。運用にあたっては各モジュールの docstring を参照し、テストやステージング環境で十分に検証してから本番に移行してください。