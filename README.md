KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）。
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理などを提供します。
研究（research）環境と本番（execution）を明確に分離した設計で、ルックアヘッドバイアス対策や冪等性を重視しています。

主要機能
-------

- データ取得（J-Quants API クライアント）
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務データ取得（四半期 BS/PL）
  - JPX マーケットカレンダー取得
  - レート制限・リトライ・トークン自動リフレッシュ対応

- ETL（差分更新パイプライン）
  - 市場カレンダー、株価、財務データの差分取得・保存
  - backfill による後出し修正吸収
  - 品質チェック呼び出し（quality モジュール）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス定義、テーブル作成の冪等 init_schema()

- 特徴量（feature）計算・正規化
  - モメンタム、ボラティリティ、バリュー（PER/ROE）などの計算
  - クロスセクション Z スコア正規化（外れ値クリップ含む）
  - ユニバースフィルタ（最低株価・流動性）

- シグナル生成
  - features と ai_scores を統合して final_score を計算
  - BUY / SELL の生成ロジック（閾値・Bear レジーム抑制・エグジット判定）
  - 日付単位の置換（冪等）で signals テーブルへ保存

- ニュース収集（RSS）
  - RSS フィード取得・正規化・前処理（URL 除去・空白正規化）
  - 記事ID を正規化 URL の SHA-256 先頭で生成（冪等）
  - SSRF / XML 攻撃対策（スキーム検証、defusedxml、リダイレクト検査）
  - 銘柄コード抽出と news_symbols への紐付け

動作環境 / 前提
---------------

- 推奨 Python バージョン: 3.10 以上（PEP 604 の型記法や union 型を使用）
- 必要な主要パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt がある場合はそれを利用してください）

セットアップ手順
---------------

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - その他必要なパッケージがある場合はプロジェクトの requirements.txt を参照して pip install -r requirements.txt

3. 環境変数を設定
   - プロジェクトルートに .env / .env.local を置くことで自動的に読み込まれます（自動読み込みはデフォルトで有効）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

推奨 .env の例
（.env.example を作る際の参考）

    # J-Quants
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

    # kabuステーション API
    KABU_API_PASSWORD=your_kabu_api_password
    # KABU_API_BASE_URL は省略時に http://localhost:18080/kabusapi を使います

    # Slack（通知などに使用する場合）
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C0123456789

    # DB パス（任意）
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db

    # 環境設定
    KABUSYS_ENV=development   # development / paper_trading / live
    LOG_LEVEL=INFO

使い方（主要 API の例）
---------------------

以下はコードから主要機能を利用する基本例です。必要に応じてログ設定などを行ってください。

- DuckDB スキーマ初期化

    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants から差分取得して保存、品質チェック）

    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)
    print(result.to_dict())

- 特徴量作成（target_date の features を再計算）

    from datetime import date
    from kabusys.strategy import build_features
    cnt = build_features(conn, date(2024, 1, 5))
    print(f"features upserted: {cnt}")

- シグナル生成（features → signals）

    from kabusys.strategy import generate_signals
    from datetime import date
    total = generate_signals(conn, date(2024, 1, 5))
    print(f"signals generated: {total}")

- ニュース収集（RSS を取得して保存・銘柄紐付け）

    from kabusys.data.news_collector import run_news_collection
    results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
    print(results)

- J-Quants データ取得（直接呼び出す）

    from kabusys.data import jquants_client as jq
    rows = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5))
    saved = jq.save_daily_quotes(conn, rows)

環境設定（Settings）
-------------------

kabusys.config.Settings を通してアプリケーション設定を取得します。主なプロパティ:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabu API のパスワード（必須）
- kabu_api_base_url: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token / slack_channel_id: Slack 設定（必須にしている部分あり）
- duckdb_path / sqlite_path: DB ファイルパス（デフォルト値あり）
- env: KABUSYS_ENV（development / paper_trading / live）
- log_level: LOG_LEVEL（DEBUG/INFO/...）

自動で .env と環境変数を読み込みます（プロジェクトルートを .git または pyproject.toml から検出）。

ディレクトリ構成
---------------

主要なファイル・ディレクトリ（リポジトリ内の実際のファイルに合わせて調整してください）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント
    - pipeline.py                   — ETL パイプライン
    - schema.py                     — DuckDB スキーマ定義と init_schema()
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - news_collector.py             — RSS ニュース収集
    - features.py                   — features 便宜関数再エクスポート
    - calendar_management.py        — 市場カレンダー関連ユーティリティ
    - audit.py                      — 監査ログ / トレーサビリティ DDL
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（mom/vol/value）
    - feature_exploration.py        — 研究用解析（forward returns / IC / summary）
  - strategy/
    - __init__.py
    - feature_engineering.py        — features 作成ワークフロー
    - signal_generator.py           — シグナル生成ロジック
  - execution/                      — 発注/約定系モジュール（実装は別ファイル）
  - monitoring/                     — 監視 / モニタリング関連（実装があれば）

設計上の注意点 / ポリシー
-------------------------

- ルックアヘッドバイアス回避: すべての戦略・研究モジュールは target_date 時点で利用可能だったデータのみ参照するよう設計されています。
- 冪等性: DB 保存関数は ON CONFLICT ベースで冪等に動作するように実装されています。
- セキュリティ: news_collector は SSRF / XML 攻撃対策を組み込んでいます。J-Quants クライアントはトークンのリフレッシュを自動化しており、レート制限も尊重します。
- 環境分離: KABUSYS_ENV により開発 / ペーパートレード / 本番を区別できます（コードの挙動やリスク管理は環境に応じて切り替えてください）。

開発にあたって
---------------

- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化できます。
- DuckDB の接続をモックすることで ETL / research / strategy ロジックを単体テストしやすく設計されています（関数は接続オブジェクトを引数に取ります）。
- 大きなネットワーク呼び出しや外部サービス依存がある箇所（jquants_client, news fetch）はテスト用に id_token 注入や HTTP モックをしやすい作りになっています。

ライセンス・貢献
----------------

（ここにプロジェクトのライセンス表記や貢献ルール、連絡先を記載してください）

以上。必要であれば README に具体的なコマンド例、より詳細な環境変数説明、CI / デプロイ手順、既知の制限事項などを追加します。どの情報を優先して追記しますか？