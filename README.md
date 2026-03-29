KabuSys
=======
日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。本リポジトリはデータ取得（ETL）・品質チェック・ニュース収集・AIによるニュース/レジーム評価・ファクター計算・監査ログなど、量的投資や自動売買システムの基盤処理を提供します。

主な特徴
--------
- J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
- 日次 ETL パイプライン（株価 / 財務 / 市場カレンダーの差分取得・保存）
- データ品質チェック（欠損/重複/スパイク/日付不整合）
- ニュース収集（RSS → raw_news、SSRF/サイズ制限/トラッキング除去対応）
- ニュース NLP：OpenAI を用いた銘柄別センチメントスコアリング（ai_scores）
- 市場レジーム判定：ETF（1321）MA とマクロニュース LLM から判定（bull/neutral/bear）
- 研究ユーティリティ：ファクター計算（momentum/value/volatility）・特徴量解析（forward returns, IC, summary）
- 監査ログ（signal/order_request/executions）テーブル定義・初期化（冪等）
- DuckDB ベースのストレージ設計（デフォルト path: data/kabusys.duckdb）

必要な環境変数
--------------
自動ロードはプロジェクトルートの .env / .env.local → OS 環境変数の順で行われます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。

必須（実行する機能により必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token 用）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注機能使用時）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）を使う際に必要

任意 / デフォルト:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite 等（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）

セットアップ（開発用）
--------------------
1. Python 仮想環境作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   必要な主なライブラリ:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリのみで書かれている部分が多いですが、OpenAI / DuckDB / defusedxml は必要です）

   例:
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

3. 環境変数を準備
   - プロジェクトルートに .env または .env.local を作成（既存の .env.example を参照）
   - 例 (.env):
       JQUANTS_REFRESH_TOKEN=xxxxxxxx
       OPENAI_API_KEY=sk-xxxx...
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       KABU_API_PASSWORD=your_password
       KABUSYS_ENV=development

4. DuckDB 用ディレクトリ作成（必要なら）
   - mkdir -p data

使い方（サンプル）
-----------------

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を省略すると今日（ローカル）を対象
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアを算出して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # 例: 2026-03-20 のウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）
  written = score_news(conn, date(2026, 3, 20))
  print("書き込んだ銘柄数:", written)
  ```

- マーケットレジーム（1321 の MA + マクロニュース）評価
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化して接続を得る
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 初期化により UTC timezone が設定され、テーブルが作成されます
  ```

重要な挙動・設計上の注意
-----------------------
- Look-ahead バイアス防止: ETL / スコアリング関数は内部で date.today() 等を無暗に参照せず、呼び出し側で target_date を明示することが想定されています（可能な限り過去の情報だけを使う）。
- 環境変数の自動ロード: パッケージは .env / .env.local をプロジェクトルートから自動読み込みします（CWD ではなく __file__ を起点にルートを探索）。テストなどで無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- エラー設計: 多くの外部API呼び出し（OpenAI / J-Quants）はリトライやフォールバック（例: マクロ取得失敗時は中立 0.0）を備えています。致命的な欠損（必須 env 未設定 等）は ValueError を投げますのでログを確認してください。
- DuckDB executemany の制約を考慮: 空パラメータの executemany は避けるように実装されています（空リストは送らない）。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースの主要な構成です（src/kabusys 配下を想定）:

- src/kabusys/
  - __init__.py (パッケージ定義、バージョン)
  - config.py (環境変数 / 設定管理)
  - ai/
    - __init__.py
    - news_nlp.py      (ニュースセンチメントのスコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント + DuckDB 保存関数)
    - pipeline.py         (ETL パイプライン / run_daily_etl 等)
    - etl.py              (ETLResult の再エクスポート)
    - calendar_management.py (市場カレンダー管理 / 営業日判定)
    - news_collector.py   (RSS ニュース収集)
    - quality.py          (データ品質チェック)
    - stats.py            (統計ユーティリティ / zscore_normalize)
    - audit.py            (監査ログスキーマ定義 / 初期化)
  - research/
    - __init__.py
    - factor_research.py  (モメンタム/バリュー/ボラティリティ計算)
    - feature_exploration.py (forward returns, IC, summary, rank)
  - research/ 他 modules...
  - その他: strategy / execution / monitoring パッケージを __all__ に含める設計（実装はプロジェクト拡張に応じて追加）

ログと実行モード
----------------
- KABUSYS_ENV: development / paper_trading / live の 3 モードで動作を切替可能。settings.is_live / is_paper / is_dev で参照できます。
- LOG_LEVEL 環境変数でログレベルを設定可能。デフォルトは INFO。

トラブルシューティング（よくある問題）
-------------------------------------
- ValueError: 環境変数が未設定 といった例外が出る場合は .env を用意するか OS 環境変数を設定してください。
- OpenAI / J-Quants API 呼び出し失敗: ネットワーク・認証情報を確認し、レート制限に引っかかっていないかログを確認してください。J-Quants クライアントは 401 時に自動で ID トークンを更新しますが、refresh token が無効だと失敗します。
- DuckDB にテーブルがない／スキーマが不足している場合はデータ初期化用のスクリプトや schema 初期化ロジックを用意して実行してください（audit.init_audit_db などはスキーマを作成します）。

開発者向けメモ
--------------
- テスト時は環境変数自動ロードを無効に（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）して、必要な env をテスト側で注入してください。
- OpenAI 呼び出し関数はユニットテストでモックしやすいように内部関数を分離しています（kabusys.ai.news_nlp._call_openai_api などを patch 可能）。
- DuckDB の日付/タイムゾーンの扱いに注意（audit.init は UTC に固定）。

ライセンス
---------
(本リポジトリにライセンス表記があればここに記載してください)

お問い合わせ / 貢献
------------------
バグ報告や改善提案は issue を作成してください。README の内容や API ドキュメントは随時更新していく予定です。

以上。README に追加したい具体的なコマンド例や .env.example のテンプレートがあれば教えてください。