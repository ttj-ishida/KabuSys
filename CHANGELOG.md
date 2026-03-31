# Changelog

すべての注目すべき変更はこのファイルに記録されます。  
このプロジェクトは Keep a Changelog の慣習に従い、セマンティックバージョニングに従います。

なお、この CHANGELOG は与えられたコードベースの内容から推測して作成しています（実装に基づく特徴・設計方針・公開 API の説明を含む）。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開リリース。

### 追加 (Added)
- パッケージの初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / 設定管理
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点に探索）
  - .env / .env.local の読み込み順序を実装（OS 環境変数優先、.env.local は上書き可能）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化対応
  - 高度な .env 行パーサを実装（export 形式、引用符・エスケープ、インラインコメントの扱い）
  - Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等のデフォルト値
    - CPU/MEM/DISK 閾値、PID ファイルパスなどの監視用設定
    - KABUSYS_ENV / LOG_LEVEL の検証（許可値チェック）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール（OpenAI 経由の NLP / レジーム判定）
  - news_nlp.score_news:
    - ニュースのタイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）
    - raw_news と news_symbols から銘柄ごとに記事を集約（記事数・文字数トリム）
    - 銘柄ごと最大 20 件ずつのバッチで OpenAI（gpt-4o-mini）にリクエスト
    - JSON Mode のレスポンス検証・堅牢なパース（余計な前後テキストの復元ロジック含む）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフのリトライ
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）
    - 部分失敗時に既存スコアを保護する設計（書き込むコードを絞る）
  - regime_detector.score_regime:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（ma200_ratio）計算
    - マクロキーワードでフィルタしたニュースタイトルを LLM によりセンチメント化
    - ma200：LLM 比率で重み付け合成（デフォルト: MA 70% / マクロ 30%）
    - レジーム判定ラベル（bull / neutral / bear）出力
    - OpenAI 呼び出しのリトライ／フェイルセーフ（失敗時は macro_sentiment=0.0）
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）

- データプラットフォーム関連
  - data.pipeline.ETLResult クラスを公開（ETL 実行結果の構造化・to_dict 実装）
  - data.calendar_management:
    - JPX カレンダー管理ロジック（market_calendar テーブルの夜間バッチ更新）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック
    - calendar_update_job により J-Quants API からの差分取得・バックフィル・健全性チェックを実装
    - 最大探索日数・バックフィル・ルックアヘッドなどの安全パラメータを実装

- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - calc_value: PER / ROE（raw_financials から最新財務を取得）
    - DuckDB を用いた SQL ベースの実装で外部 API へのアクセスなし
  - research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算
    - calc_ic: スピアマンのランク相関に基づく IC 計算（rank ユーティリティ使用）
    - rank / factor_summary: ランク化、基本統計量の計算（外部依存無し、標準ライブラリのみ）

- パッケージ構成
  - kabusys.__init__ で public サブパッケージ（data, strategy, execution, monitoring）をエクスポート（将来的な統合点）

### 変更 (Changed)
- 設計上の方針明確化（コード内ドキュメンテーション）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を関数内部で直接参照しない実装方針を各所で適用
  - OpenAI 呼び出し（news_nlp / regime_detector）は別実装とし、モジュール間の結合を避ける設計

### 修正 (Fixed)
- LLM レスポンスの実務対応性向上
  - JSON パース失敗に対して余計な前後テキストを除去して復元を試みる耐障害性を追加
  - LLM が整数でコードを返すケースや未知コードを無視するなど、実際の応答のばらつきに対応

### 保守・品質 (Maintenance)
- ロギングを各処理に追加・充実（info / warning / debug）
- データベース書き込みは原則冪等化（DELETE → INSERT / ON CONFLICT と互換性を意識）
- DuckDB の executemany の挙動差異（空リスト不可）に配慮した実装

### セキュリティ (Security)
- 必須トークン / キーは Settings で明示的にチェックし、未設定時は ValueError を送出（fail-fast）
- OS 環境変数は protected として .env ロードで上書きできないよう保護

---

注:
- 本 CHANGELOG はコード内の docstring / 定数 / 関数設計から推測して記載しています。実際のリリースノート作成時はコミット履歴・ PR メッセージ等を参照して適宜補正してください。