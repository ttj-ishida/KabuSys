Keep a Changelog
=================

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
各項目はコードベース（src/kabusys 以下）の現状から推測して作成しています。

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-28
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報:
    - __version__ = "0.1.0"
    - パブリックサブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ に準拠）

- 環境設定/ローディング機能（kabusys.config）
  - .env の自動読み込み実装（プロジェクトルート検出: .git または pyproject.toml を探索）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能
  - .env パーサ実装（export 構文対応、クォート内のエスケープ処理、インラインコメント処理）
  - _load_env_file による上書き制御（override, protected）で OS 環境変数を保護
  - Settings クラスを提供し、必須環境変数取得で未設定時は ValueError を送出
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値を持つ設定: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV
    - env 値検証 (_VALID_ENVS, _VALID_LOG_LEVELS) とヘルパー is_live / is_paper / is_dev

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成
    - ニュース収集ウィンドウ計算 calc_news_window（JST ベース → UTC naive datetime）
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価 score_news の実装
      - バッチサイズ、記事数・文字数制限、JSON Mode（response_format）での取得
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ
      - レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップ
      - テスト用に _call_openai_api を patch して差し替え可能
    - スコアの DB 反映は部分書換（対象コードのみ DELETE → INSERT）で部分失敗時に既存データを保護
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず target_date に対する閉区間/半開区間で処理

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
    - マクロニュース抽出・LLM 呼び出し・合成ロジックとしきい値で bull/neutral/bear を判定
    - API 呼び出し失敗時は macro_sentiment=0.0（フェイルセーフ）
    - DB 書き込みは冪等的（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK とログ
    - OpenAI クライアントは引数 api_key または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定ロジックの実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録データ優先、未登録日は曜日ベースのフォールバック（週末は非営業日）
    - next/prev トラバーサルは _MAX_SEARCH_DAYS でループ打ち切り（無限ループ防止）
    - calendar_update_job により J-Quants から差分取得 → 保存（バックフィル・健全性チェック付き）
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスの導入（処理統計、品質問題、エラー一覧を保持）
    - 差分更新・保存（jquants_client 経由）・品質チェックの想定フローを実装
    - バックフィル期間を考慮した最終取得日算出、_MIN_DATA_DATE 等の定義
    - _table_exists / _get_max_date 等のユーティリティ
    - data.etl で ETLResult を再エクスポート

- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m/3m/6m と 200 日 MA 乖離（ma200_dev）の計算
    - calc_volatility: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、volume_ratio の計算
    - calc_value: raw_financials から EPS/ROE を取得し PER・ROE を算出（EPS 0/欠損は None）
    - DuckDB SQL を活用し、営業日ベースのラグ/ウィンドウを扱う実装
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 将来リターン（指定ホライズン）を一括で取得する効率的なクエリ
    - calc_ic: Spearman（ランク相関）による IC 計算。データ不足時は None を返す
    - factor_summary: 各ファクターの基本統計量（count, mean, std, min, max, median）
    - rank: 同順位は平均ランクで扱う堅牢なランク化実装
    - pandas 等に依存せず、標準ライブラリと DuckDB を使用

Changed
- （本バージョンは初期リリースのため「変更」は無し）

Fixed
- （初期リリースのため既知の「修正」は無し）

Security
- 環境変数に API キー・トークンを期待する実装のため、実運用時は環境管理（.env の取り扱い・権限管理）に注意
  - 必須環境変数未設定時は Settings や各 score_* 関数で ValueError を送出して明示的に失敗
- OpenAI 呼び出しは外部 API を利用するため、レート制限やエラー時のフォールバック（スコア 0.0 等）を実装済みだが、API 使用量や秘匿情報の管理は利用者側での運用が必要

開発上の注記（実装に基づく設計意図・制約）
- ルックアヘッドバイアス対策: 日付周りの処理はすべて target_date を明示的に受け取り、内部で datetime.today()/date.today() を安易に参照しない設計
- DuckDB のバージョン差異対策: executemany に空リストを渡さない等の注意（コメントで互換性について言及）
- OpenAI 呼び出しのテスト容易性: 各モジュール内の _call_openai_api を unittest.mock.patch で差し替え可能にしている
- DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT 想定）しており、部分失敗時に既存データを不必要に削除しない実装を心がけている

今後のマイルストーン（推奨）
- エンドツーエンドの統合テスト（DuckDB を使ったローカル CI、OpenAI 呼び出しはモック化）
- 発注/実行モジュール（execution）と監視（monitoring）の実装・検証（現状はパッケージ参照のみ）
- ドキュメント整備: API 使用例、ETL 実行手順、運用時の環境設定ガイド（.env の推奨設定例など）

--- 

この CHANGELOG はコード内コメント・関数名・設計方針コメントから推測して作成しています。必要があれば各変更点をより細かく分割（例: ai/news_nlp v0.1.0 のサブリリースノート等）して更新します。