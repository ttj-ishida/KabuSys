# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ。  
データ取り込み（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター計算、ETL、監査ログ（DuckDB）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやリサーチ基盤を構築するための内部ライブラリです。主な役割は次のとおりです。

- J-Quants API からの株価・財務・市場カレンダー取得（レートリミット / リトライ / トークンリフレッシュ対応）
- RSS を使ったニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースのセンチメント評価 / 市場レジーム判定
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および研究ユーティリティ
- 監査ログテーブル定義・初期化（注文のトレーサビリティ用、DuckDB）

設計方針として、バックテストやルックアヘッドバイアス防止のために「現在時刻を勝手に参照しない」実装や、DB 上での冪等保存（ON CONFLICT / DELETE→INSERT）を多用しています。

---

## 機能一覧

- データ取得 / 保存
  - J-Quants: 日足（OHLCV）、財務データ、上場情報、マーケットカレンダー
  - Redis 等は使わず DuckDB を主な永続化先として想定
- ETL
  - 差分取得（最終取得日からの差分）／バックフィル
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL の統合実行（run_daily_etl）
- ニュース処理
  - RSS 取得（fetch_rss）・前処理（URL 除去・正規化）
  - 銘柄との紐付け（news_symbols 経由）
- NLP / AI
  - 銘柄ごとのニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）— ETF 1321 の MA200 とマクロニュースの LLM スコアを合成
- 監査（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化
  - 監査 DB の初期化ユーティリティ（init_audit_db）
- 研究支援
  - ファクター算出（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリー
- カレンダー
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（J-Quants からの差分更新）

---

## 必要条件

- Python 3.10 以上（型ヒントで `X | Y` を使用しているため）
- 主な依存パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ: urllib, json, datetime, logging, hashlib など）

実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。

---

## 環境変数（必須 / 推奨）

重要な環境変数は以下の通りです（src/kabusys/config.py を参照）。

必須（少なくとも実行する機能に応じて）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注系と連携する場合）
- SLACK_BOT_TOKEN — Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
- OPENAI_API_KEY — OpenAI API を使う場合（score_news / score_regime 内で参照可能）

その他（デフォルトあり）:
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — sqlite（監視DBなど、デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化

自動で .env / .env.local をプロジェクトルートから読み込む仕組みがあります（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

サンプル .env（README 用）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （もし pyproject.toml / requirements.txt があればそれを使ってください）
   - pip install -e .

4. 環境変数を用意
   - プロジェクトルートに .env を作成 or 環境変数をエクスポート
   - 例: 上記サンプル .env を参照

5. DuckDB データベースの準備
   - デフォルトでは data/kabusys.duckdb を使用します。必要に応じてフォルダ作成は init 関数が行いますが、手動で作成しても問題ありません。

---

## 使い方（代表的な例）

以下はライブラリをインポートして利用する簡単な例です。実行には適切な環境変数（特に OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）が必要です。

- DuckDB 接続を作る（設定ファイルのパスを使用）
```py
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（J-Quants からのデータ取得・保存・品質チェック）
```py
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI を使って銘柄ごとのセンチメントを ai_scores に保存）
```py
from kabusys.ai.news_nlp import score_news
from datetime import date

num_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {num_written} scores")
```

- 市場レジームの判定（ETF 1321 の MA200 とマクロニュースを合成）
```py
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を作る（監査専用 DuckDB を初期化）
```py
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions) が作成されます
```

- カレンダー関連ユーティリティ
```py
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- score_news / score_regime は OpenAI API を呼びます。api_key を関数に明示的に渡すか環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl 等は J-Quants API を叩きます。JQUANTS_REFRESH_TOKEN を設定してください。

---

## 開発・テスト上の注意点

- ルックアヘッドバイアスに注意: 多くの関数は「target_date」を明示的に受け取り、内部で date.today() を直接参照しないように設計されています。バックテスト時は必ず過去の時点の状態でデータを用意してください。
- 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env/.env.local を読み込みます。テスト中に自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部はテスト容易性を考慮し、モック（unittest.mock.patch）しやすい実装になっています。
- DuckDB の executemany に対する互換性（空リストを渡せない等）を考慮してコードが書かれています（DuckDB 0.10 を想定）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの NLP スコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - news_collector.py      — RSS 取得・前処理
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — Zスコア等の統計ユーティリティ
    - audit.py               — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー

（上記は主要なファイルを抜粋したもので、さらに細かい補助モジュールが含まれます）

---

## セキュリティ・運用上の注意

- API トークンやパスワードは絶対に漏洩しないよう管理してください（.env をリポジトリに含めない、Secrets 管理を利用する等）。
- 本ライブラリには発注（実際の売買）と連携するコードがあります。live 環境での実行は十分な検証とリスク管理を行ってから行ってください（KABUSYS_ENV=live）。
- RSS 取得では SSRF 対策（リダイレクト時の検査、プライベートアドレス拒否）や XML 関連の脆弱性対策（defusedxml）を実装していますが、運用中のログ・監査は必須です。

---

## 参考（実装上のポイント）

- J-Quants クライアントは固定間隔スロットリング (120 req/min) とトークン自動リフレッシュ（401 応答時）を備えています。
- News NLP / Regime detector は OpenAI の JSON Mode を使い、レスポンスのパース・バリデーション・リトライを慎重に行います。
- ETL は差分ベース、かつバックフィルを行い、品質チェックで問題を検出してから運用判断が行える設計です。
- 監査ログは UUID をキーにして完全なトレーサビリティを確保するスキーマになっています。

---

必要であれば README にサンプル .env.example やより詳細なコマンド（systemd / cron のジョブ例、Dockerfile、CI 設定例）を追加できます。どの情報を優先して追記しますか？