# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。J-Quants API や各種ニュースソース、OpenAI を組み合わせてデータ収集（ETL）、品質チェック、ファクター計算、ニュースセンチメント分析、マーケットレジーム判定、監査ログ管理などを行えるよう設計されています。

主な設計方針:
- ルックアヘッドバイアスを防ぐ（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を中心としたローカル DB 操作（冪等性を保った保存処理）
- 外部 API 呼び出しに対して堅牢なリトライ・バックオフ・レート制御
- OpenAI（gpt-4o-mini）を用いたニュース NLP、LLM 呼び出しのフェイルセーフ設計

---

## 機能一覧

- 環境・設定管理
  - .env/.env.local からの自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ラッパー（Settings オブジェクト）
- データ ETL（J-Quants 経由）
  - 株価日足（OHLCV）取得・保存（差分フェッチ、ページネーション対応）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェック（QualityIssue 報告）
- ニュース収集・NLP（raw_news → ai_scores）
  - RSS フィード収集（SSRF 対策、サイズ上限、トラッキングパラメータ除去）
  - OpenAI を用いた銘柄ごとのセンチメントスコアリング（バッチ・JSON モード）
- マーケットレジーム判定
  - ETF（1321）200日移動平均乖離 + マクロニュース由来の LLM センチメントを合成して daily regime 判定
- リサーチ用ユーティリティ
  - ファクター（モメンタム、ボラティリティ、バリュー等）計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - Zスコア正規化等の統計ユーティリティ
- 監査ログ（audit）
  - signal → order_request → execution までトレース可能な監査テーブル定義・初期化

---

## 動作要件

- Python 3.10 以上（型の union 演算子 (|) を使用しているため）
- 推奨パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、OpenAI API、RSS フィード

（プロジェクトに requirements.txt がある場合はそちらを優先してください）

---

## 環境変数 / .env

必須（アプリ実行に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション等のパスワード（発注連携時）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルト値あり）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動読み込みの制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テスト等で使用）。

例（.env の一部）
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt や pyproject.toml があればそれを使用）
   - 例: pip install -r requirements.txt

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、必要な環境変数をエクスポートしてください。
   - 自動ロードは src/kabusys/config.py によりプロジェクトルート (.git または pyproject.toml を基準) から .env/.env.local を読み込みます。

5. 初期 DB 作成（監査用等）
   - Python REPL またはスクリプトから監査 DB を初期化できます（DuckDB を使用）:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（代表的な例）

以下はライブラリを直接インポートして利用するサンプルコード例です。

- 日次 ETL を実行する
```
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングする（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- マーケットレジームを判定して保存する
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査スキーマを初期化する（既存接続に追加）
```
from kabusys.data.audit import init_audit_schema
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- ファクター計算（リサーチ用）
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

---

## 注意事項 / 運用上のポイント

- OpenAI 呼び出しはリトライ・バックオフを備えていますが、API トークンの管理（レート・コスト）は利用者の責任です。モデルは gpt-4o-mini を想定しています。
- J-Quants API はレート制限（120 req/min）を守る設計になっています。ID トークンの自動リフレッシュやページネーション処理を行います。
- ETL / LLM 系の処理は外部 API 依存のため、実行時にネットワーク接続と適切な環境変数が必要です。
- DuckDB の executemany に空リストを与えるとエラーになるバージョン（例: 0.10）に配慮した実装が含まれています。
- ローカルでのテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化すると制御しやすくなります。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの LLM センチメント解析
    - regime_detector.py    — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult 再エクスポート
    - news_collector.py     — RSS 収集、raw_news への保存
    - calendar_management.py— 市場カレンダー管理 / 営業日判定
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py    — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
  - ai/__init__.py
  - research/__init__.py
  - data/etl.py

（コメント・ドキュメントが各モジュールヘッダに詳細に記載されています）

---

必要に応じて README にサンプル .env.example、CI 用のセットアップ手順、ローカルデータ初期化スクリプト例などを追加できます。追加希望があれば目的（開発・デプロイ・CI など）を教えてください。