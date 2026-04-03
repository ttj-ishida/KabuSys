# KabuSys

KabuSys は日本株の自動売買・データ基盤・リサーチ用ライブラリ群です。J-Quants / RSS / OpenAI（LLM）などを組み合わせて、データ収集（ETL）、品質チェック、ニュースの AI スコアリング、マーケットレジーム判定、ファクター計算、監査ログ管理などを提供します。

主な目的は「バックテスト・リサーチ用の高品質データ基盤」と「アルゴリズム売買の監査可能な実行フロー」を両立することです。

バージョン: 0.1.0

---

## 特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）・財務データ・上場情報・JPXカレンダーを差分取得（ページネーション対応）
  - 差分更新・バックフィル機能・取得時刻（fetched_at）の記録で Look-ahead バイアスを抑制
- データ保存（DuckDB）
  - 冪等（ON CONFLICT DO UPDATE）での保存
  - 品質チェック・監査ログ用スキーマ初期化ユーティリティ
- データ品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合の検出
- マーケットカレンダー管理
  - market_calendar を元に営業日判定・次/前営業日検索・日付範囲の営業日リスト取得
  - J-Quants から夜間バッチで差分取得するジョブ
- ニュース収集と前処理
  - RSS フィード収集（SSRF対策、トラッキングパラメータ除去、コンテンツ前処理）
  - raw_news / news_symbols との紐付けを前提にした保存ロジック
- ニュースの AI スコアリング
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（ai_scores）生成
  - バッチ処理・リトライ・レスポンス検証・スコアクリッピング実装
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム判定（bull/neutral/bear）
  - LLM 呼び出し失敗時はフェイルセーフ（ゼロフォールバック）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリー
  - クロスセクション Z スコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマと初期化ユーティリティ
  - order_request_id を冪等キーとする設計

---

## 前提・依存

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続が必要（J-Quants API, RSS, OpenAI）

必要に応じて pyproject.toml / requirements.txt を用意してください。最低限のインストール例:

pip install duckdb openai defusedxml

（プロジェクトにセットアップスクリプトがある場合はそちらを使ってください）

---

## セットアップ手順

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

3. リポジトリを配置・インストール（開発時）
   - pip install -e .   （プロジェクトにインストール設定がある場合）

4. 環境変数設定
   プロジェクトルートに .env または .env.local を作成することで環境変数を自動で読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   必須／推奨の環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携時）
   - OPENAI_API_KEY: OpenAI API キー（AI スコアリング時、関数引数からも渡せる）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / ...（デフォルト INFO）

   .env の例:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な操作例）

ここでは Python からの基本的な利用例を示します。関数は各モジュールから直接インポートして使用します。OpenAI のキーは環境変数 OPENAI_API_KEY で読み込まれますが、api_key 引数で明示的に渡すことも可能です。

- DuckDB 接続の作成と設定の取得

from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（株価・財務・カレンダーの差分取得と品質チェック）

from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- ニュースの AI スコアリング（target_date のウィンドウに対して ai_scores を更新）

from kabusys.ai.news_nlp import score_news
from datetime import date
count = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI キーは環境変数または api_key 引数で

- 市場レジーム判定（market_regime テーブルへ書き込み）

from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマ初期化（監査用 DB を新規作成して初期化）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- リサーチ用ファクター計算

from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))

- データ品質チェックを個別／一括で実行

from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)

注意点:
- OpenAI 呼び出しは有料 API を利用します。API キーや使用量に注意してください。
- run_daily_etl 等はネットワーク・API エラーを内部でキャッチしつつ進める設計ですが、ETLResult に errors が記録されます。運用ではログと ETLResult の監視を推奨します。
- Look-ahead バイアス対策: 各処理は内部で date 引数と DB の fetched_at を用いてルックアヘッドを避けるよう設計されています。バックテスト等では target_date を明示的に渡すことを推奨します。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン。get_id_token で使用。
- KABU_API_PASSWORD (必須 for kabu): kabuステーション API のパスワード（発注連携時）。
- OPENAI_API_KEY (必須 for AI 機能): OpenAI の API キー（news_nlp / regime_detector 等で使用）。
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- KABUSYS_ENV: development / paper_trading / live（動作モード）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

詳細は kabusys.config.Settings のプロパティを参照してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数・設定管理（.env 自動読み込み機構）
- ai/
  - __init__.py
  - news_nlp.py         — ニュースの LLM スコアリング（ai_scores への保存）
  - regime_detector.py  — マーケットレジーム判定（1321 MA200 + マクロLLM）
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETL インターフェース（ETLResult の再エクスポート）
  - quality.py          — データ品質チェック
  - stats.py            — 共通統計ユーティリティ（zscore_normalize）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py   — RSS 収集（SSRF/サイズ制限/前処理）
  - audit.py            — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py  — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

補助:
- requirements や CI 設定があればプロジェクトルートに配置してください。
- .env.example を用意すると初期セットアップが容易になります（本リポジトリに .env.example がある前提）。

---

## 運用上の注意

- API レート制限やエラー時のリトライは組み込まれていますが、運用環境では外部サービスの SLA を考慮したスケジューリングを行ってください（J-Quants の 120 req/min 制限など）。
- OpenAI の呼び出しはコストが発生します。バッチ頻度やモデルを運用ポリシーに合わせて調整してください。
- DuckDB ファイルのバックアップやスキーママイグレーション方針を定めてください。監査ログは削除しない想定で設計されています。
- 本ライブラリはバックテスト・リサーチ向けに Look-ahead バイアスを抑える設計を行っていますが、呼び出し方次第でバイアスを招く可能性は残ります。特にバックテストループ内での外部 API 呼び出しは避け、事前にデータを ETL してから評価することを推奨します。

---

## テスト・開発

- 自動 env ロードを無効化してユニットテストを実行する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants の呼び出しはユニットテストではモックする設計になっています（モジュール内の _call_openai_api などを patch）。
- DuckDB は :memory: を指定してテスト用のインメモリ DB として利用可能です。

---

ご要望があれば README に追加する具体的なサンプルスクリプト（cron 用の ETL スクリプト、ニュース収集スケジューラ、監査 DB 初期化スクリプトなど）を作成します。必要な項目を教えてください。