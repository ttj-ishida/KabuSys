# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
主に ETL（J-Quants からのデータ取得・保存）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注／約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API 経由での差分 ETL（株価 / 財務 / カレンダー）と DuckDB への冪等保存
- ニュース収集（RSS）と LLM を使った銘柄ごとのニュースセンチメント（ai_scores）生成
- 市場レジーム判定（ETF 1321 の 200 日 MA 乖離 + マクロニュースの LLM センチメント）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ（Z-score）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal_events, order_requests, executions）と初期化ユーティリティ
- 環境変数 / .env を使った設定管理（自動ロード機構あり）

---

## 機能一覧（モジュール単位）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - settings オブジェクト（J-Quants / kabu / Slack / DB / 環境切替など）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / 認証 / レート制御）
  - pipeline / etl: 日次 ETL（差分取得、保存、品質チェック）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS 取得・前処理・保存ユーティリティ（SSRF対策、サイズ制限等）
  - stats: 汎用統計（zscore_normalize）
  - quality: データ品質チェック（各種 QualityIssue を返す）
  - audit: 監査ログスキーマ定義と初期化ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に送って銘柄別センチメントを ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースから市場レジームを判定して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- その他（将来的に strategy / execution / monitoring などの層と連携する設計）

---

## 必須環境変数

主要な実行に必要な環境変数（一部）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 等で使用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注連携を行う場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack に投稿するチャネル ID

オプション・デフォルト値付き:

- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

※ .env をプロジェクトルートに置くと自動的に読み込まれます（.env.local は上書き）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python の準備
   - Python 3.10+ を推奨（type hint や一部機能での互換性を考慮）
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 代表的な依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）
4. 環境変数設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 最低限必要な変数を設定（例: JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）
   - 例 .env（テンプレート）
     - JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - KABUSYS_ENV=development
5. DuckDB 用データディレクトリの準備
   - デフォルトでは data/ 配下にファイルを作成します。必要に応じてディレクトリを作成してください。
     - mkdir -p data

---

## 使い方（簡単な利用例）

以下は Python REPL / スクリプトから利用する例です。DuckDB はファイルベースで接続します。

- 日次 ETL を実行する（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアを生成する（OpenAI API キーが環境変数または引数で必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ DB を初期化する（別 DB を作る例）
```python
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# 必要に応じて同接続を活用して order_events 等を記録
```

- 設定値は settings オブジェクトで参照可能
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- OpenAI 呼び出しはネットワークと料金が発生します。API キー設定と料金設定を確認してください。
- J-Quants の API にはリクエスト制限があります（本ライブラリはレート制御を備えていますが、利用ポリシーに従ってください）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なディレクトリ / ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 読み込み・settings
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py  — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLインターフェース（ETLResult 再エクスポート）
    - calendar_management.py — JPX カレンダー管理・営業日判定
    - news_collector.py   — RSS フィード収集と整形
    - stats.py            — 統計ユーティリティ（zscore_normalize）
    - quality.py          — データ品質チェック
    - audit.py            — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai, research などのユーティリティ群
- pyproject.toml / setup.cfg / requirements.txt （ない場合は手動で依存を管理）

---

## 運用上の注意点 / 設計上の方針

- ルックアヘッドバイアス防止
  - 多くの処理は datetime.today()/date.today() を内部で参照せず、明示的な target_date を受け取る設計です。
  - prices データ取得や NLP 集計は過去データのみを参照するように実装されています。
- 冪等保存
  - J-Quants から取得したレコードは DuckDB に対して ON CONFLICT DO UPDATE（冪等）で保存します。
- フェイルセーフ
  - OpenAI/API エラー時に処理を停止せずフォールバック（0.0 スコア等）して継続する設計箇所があります。ログを確認してください。
- セキュリティ
  - RSS 周りで SSRF 対策、XML パースに defusedxml を使用、レスポンスサイズ制限などを実装しています。
- テストしやすさ
  - OpenAI 呼び出し等は内部関数をモック/patch しやすいように分離しています。

---

## よくある利用フロー（例）

1. .env に JQUANTS_REFRESH_TOKEN と OPENAI_API_KEY を設定
2. DuckDB の接続先を settings.duckdb_path に合わせて準備
3. cron / バッチで日次 ETL（run_daily_etl）を実行
4. ETL 後に score_news / score_regime を実行し ai_scores / market_regime を更新
5. 研究環境では kabusys.research の関数でファクター検証を実施
6. 発注システムと連携する場合は audit スキーマでトレーサビリティを確保

---

## 開発・拡張のヒント

- OpenAI 関連のテストは _call_openai_api の差し替え（unittest.mock.patch）を推奨
- DuckDB を用いるため、テーブルスキーマが事前に準備されていることを確認してください（ETL 前に schema 初期化が必要な場合あり）
- jquants_client の API 呼び出しはページネーション対応済み。長時間の取得や大規模取得時はレート制御の影響を考慮してください

---

必要であれば、README に「テーブルスキーマ一覧」や「より詳細な .env.example」「デプロイ手順（systemd / cron / Docker）」などを追加できます。付録として追記を希望する点を教えてください。