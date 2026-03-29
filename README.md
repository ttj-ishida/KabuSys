# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）

概要、主要機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。  
主な目的は以下です。

- J-Quants API から株価・財務・マーケットカレンダー等のデータを取得して ETL（差分取得・保存・品質チェック）を実行するデータパイプライン
- ニュース収集（RSS）と LLM を用いたニュースセンチメント解析（銘柄別スコア、マクロセンチメント）
- ファクター計算・リサーチ支援（モメンタム、ボラティリティ、バリュー等）
- 取引監査ログ（signal → order_request → execution のトレーサビリティ）を保持する監査データベース
- 市場レジーム判定や戦略実行・約定連携のためのユーティリティ群

設計上の重点点:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を使ったローカル永続化（冪等保存）
- API 呼び出しに対する堅牢なリトライ・レート制御
- ニュース収集での SSRF 対策やサイズ制限などセキュリティ考慮
- OpenAI（gpt-4o-mini 等）を用いた JSON モードの出力を前提とした LLM 呼び出し

---

## 主な機能一覧

- 環境変数読み込み / 設定管理（kabusys.config）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可）
  - 必須キーの検査（例: JQUANTS_REFRESH_TOKEN など）
- データ ETL（kabusys.data.pipeline）
  - 差分取得、保存、品質チェック（欠損・スパイク・重複・日付不整合）
  - J-Quants クライアント（kabusys.data.jquants_client）：レート制限・トークン自動リフレッシュ・ページネーション対応
- ニュース収集（kabusys.data.news_collector）
  - RSS から収集して raw_news に保存、記事ID は正規化 URL のハッシュで冪等性を担保
  - SSRF 保護、gzip サイズ上限、トラッキングパラメータ除去等の防衛策あり
- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとにニュースを集約して OpenAI に送信し、銘柄別センチメント（ai_scores）を生成
  - バッチ処理、リトライ、レスポンス検証、スコアクリッピングを実装
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成して daily レジーム判定
  - 失敗時はフェイルセーフ（マクロ部分は 0.0）
- リサーチ / ファクター（kabusys.research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - zscore_normalize 等のユーティリティ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブルを初期化する関数を提供
  - UUID ベースのトレーサビリティ、created_at / updated_at の運用方針

---

## 必要条件・依存関係

- Python 3.10+（コード内で型ヒントのユニオン表現や modern typing を利用）
- 推奨ライブラリ（代表例）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime, logging 等）

実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。ない場合は以下のように手動でインストールします。

例:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install duckdb openai defusedxml
# 必要に応じて他ライブラリを追加
```

---

## 環境変数

以下の環境変数が参照されます（プロダクション利用時は .env を用意してください）:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD     : kabuステーション API のパスワード
- SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID      : Slack 通知先チャネル ID
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 呼び出し時に参照）

任意 / デフォルト有り:
- KABUSYS_ENV           : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動で .env を読み込まない
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

.env の例（最低限の必須キーを記載）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   （プロジェクトに pyproject.toml / requirements.txt があればそれを利用してください）
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成して必須キーを設定するか、
   - シェルに直接エクスポートしておく（CI 等ではこちら）

5. DuckDB 初期化（監査用 DB の例）
   Python REPL かスクリプトで:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb の接続（使用後は close してください）
   ```

---

## 使い方（代表的な関数・ワークフローの例）

- 日次 ETL を実行してデータを更新する（run_daily_etl）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定を実行して market_regime テーブルへ保存
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマの初期化（既存 DB に監査テーブルを追加）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。使用には OPENAI_API_KEY の設定が必要です。
- ETL / ニュース収集は外部 API（J-Quants や各 RSS）へアクセスするため、適切なトークンとネットワーク環境が必要です。
- 実行中の DB トランザクションや接続は適切に管理してください（DuckDB の特性上トランザクションの取り扱いに注意）。

---

## ディレクトリ構成

（主要なファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（銘柄別センチメント）
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py        — マーケットカレンダー管理 / 営業日判定
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py             — J-Quants API クライアント（取得 + 保存）
    - news_collector.py             — RSS ニュース収集（SSRF 対策等）
    - quality.py                    — データ品質チェック（欠損/スパイク/重複/日付整合）
    - stats.py                      — zscore_normalize 等統計ユーティリティ
    - audit.py                      — 監査ログ（テーブル定義・初期化）
    - etl.py                        — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン/IC/統計サマリ等
  - (他: strategy/, execution/, monitoring/ 等のサブパッケージが想定される)

この README に記載されていない追加モジュールや CLI、デプロイ手順がある場合は各モジュールの docstring を参照してください（各 Python モジュールに詳細な設計コメント／処理フローが記載されています）。

---

## 運用上の注意

- 本リポジトリは実際に資金を動かすシステムに接続する前に十分なテスト・レビューが必要です。特に order/exec 周りの冪等性・エラーハンドリングを重点的に検証してください。
- OpenAI 呼び出しはコストがかかるため、ローカルテストではモック（unittest.mock.patch）を利用することを推奨します。コード中にもモック差替えを想定したフックが用意されています。
- J-Quants API のレート制限や認証方式に従って運用してください（モジュール側にレート制御・トークン自動更新のロジックあり）。
- ニュース収集では外部 RSS の挙動（スキーマ・文字コード・サイズ）に配慮し、タイムアウトやサイズ上限の設定を有効にしてください。

---

## 貢献 / 開発

- バグ修正・機能追加はプルリクエストを歓迎します。PR では関連するユニットテストと説明を添えてください。
- 大きな設計変更（API 変更・DB スキーマ変更等）は事前に Issue で議論してください。

---

README の内容は随時更新されるべきです。具体的な利用シナリオ（バックテスト・ペーパー取引・本番）や運用手順は別途ドキュメント（運用マニュアル）にまとめることを推奨します。