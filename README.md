# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
J-Quants API と kabuステーション、OpenAI を組み合わせて、データ収集（ETL）・品質検査・ニュース NLP（銘柄センチメント）・市場レジーム判定・ファクター計算・監査ログなどを提供します。

主な設計方針：
- ルックアヘッドバイアス防止（内部で datetime.today() を不用意に参照しない）
- DuckDB を中心としたローカルデータレイヤ（冪等保存、ON CONFLICT を多用）
- 外部 API（J-Quants / OpenAI）への堅牢なリトライ・レート制御
- セキュリティ（SSRF 対策、XML パースの安全化 等）
- テストしやすさ（依存注入・モック差替えポイントを確保）

バージョン: 0.1.0

---

## 機能一覧

- データ収集 / ETL
  - J-Quants API クライアント（株価日足、財務、上場情報、マーケットカレンダー）
  - 差分取得、ページネーション、トークン自動更新、レート制御
  - ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合チェック（quality モジュール）
- ニュース収集 / 前処理
  - RSS 収集（SSRF 対策・gzip制限・トラッキングパラメータ削除）
  - raw_news / news_symbols への冪等保存
- AI（OpenAI）連携
  - 銘柄毎ニュースセンチメント（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - JSON-mode とリトライ/フェイルセーフ設計
- リサーチ / ファクター
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- カレンダー管理
  - JPX カレンダーの差分取得・営業日判定・隣接営業日の探索
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等の監査テーブル定義と初期化
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize 等）
  - 設定管理（.env 自動読み込み / Settings）

---

## 要求環境 / 依存関係

- Python 3.10+（型記法（|）を使用）
- 主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

※ 実運用ではパッケージ管理ファイル（requirements.txt / pyproject.toml）に合わせてインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン（またはソースを配置）
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （実運用では pip install -e . や requirements.txt に従ってください）
4. 環境変数を用意（.env または環境変数）
   - プロジェクトルートに .env / .env.local を置くと自動ロードされます（config モジュールが自動で読み込みます）。
   - 自動ロードを無効化する場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabu API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャネル ID
   - OPENAI_API_KEY: OpenAI API キー（AI 関連機能で利用）
   - （任意）KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - （任意）LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
   - （任意）DUCKDB_PATH: デフォルト data/kabusys.duckdb
   - （任意）SQLITE_PATH: 監視用 sqlite のパス（data/monitoring.db）
6. DuckDB データベースと監査スキーマ初期化（例）
   - Python REPL またはスクリプトで:
     from kabusys.config import settings
     import duckdb
     conn = duckdb.connect(str(settings.duckdb_path))
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## サンプル使い方（短いコード例）

以下は最小限の使用例スニペットです。実行は仮想環境内で行ってください。

- ETL を1日分実行（run_daily_etl）:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを生成（score_news）:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数で設定しておくか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

- 市場レジームを判定（score_regime）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
# api_key 引数に OpenAI API キーを渡すか、環境変数 OPENAI_API_KEY を設定
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用の DuckDB を新規初期化して接続を取得:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- データ品質チェック実行:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャネル ID
- OPENAI_API_KEY (AI 機能用): OpenAI API キー（news_nlp / regime_detector）
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意): SQLite 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意): development | paper_trading | live（検証環境切替）
- LOG_LEVEL (任意): DEBUG|INFO|WARNING|ERROR|CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化

※ .env のパースはプロジェクトルート（.git または pyproject.toml を起点）にある .env / .env.local を参照します。

---

## ディレクトリ構成（主要ファイル）

（src 配下の kabusys パッケージを中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースから銘柄センチメントを生成（OpenAI）
    - regime_detector.py      — ETF MA + マクロニュースで市場レジーム判定（OpenAI）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存・ETL 用）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - calendar_management.py  — JPX カレンダー管理・営業日判定
    - news_collector.py       — RSS 収集・前処理・保存
    - quality.py              — データ品質チェック群
    - stats.py                — 汎用統計ユーティリティ（zscore 正規化等）
    - audit.py                — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum, value, volatility）
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - ai, research, data 以外にも strategy/execution/monitoring 等の公開領域が想定されています（パッケージエクスポート参照）

---

## 注意事項 / 補足

- OpenAI 呼び出しはコストとレート制限に注意してください。APIキーは秘匿管理を推奨します。
- J-Quants の API レート制限（例: 120 req/min）を守るため内部的にスロットリングを行っています。大量取得時は時間を要する場合があります。
- ETL / AI の関数はルックアヘッドバイアス回避のため、内部で現在時刻を暗黙に参照しない設計がされています。バックテストで使用する場合は target_date を明示してください。
- DuckDB のバージョンによる挙動差異（executemany の空リスト扱い等）に注意して実装されていますが、使用する DuckDB バージョンでの確認を推奨します。
- RSS フィード取得は外部ネットワークを介します。fetch_rss は SSRF 対策や応答サイズ制限を実装していますが、運用環境のネットワークポリシーも確認してください。

---

必要であれば、README に含めるサンプル .env.example、CI / テスト手順、より詳細な API 使用例（例: ETL の cron 設定、Slack 通知フロー、実運用での order_requests→executions の流れ）を追記できます。どの項目を優先して追記しますか？