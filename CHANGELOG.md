Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」規約に準拠しています。

フォーマット
-----------
- 変更は "Added", "Changed", "Deprecated", "Removed", "Fixed", "Security" の各セクションに分類します。
- バージョンは semver を想定します。

Unreleased
----------
（なし）

0.1.0 - 2026-04-01
------------------

Added
- 初回公開: KabuSys 日本株自動売買システムのコア機能群を追加。
  - パッケージ初期化
    - パッケージバージョン: 0.1.0
    - 公開サブパッケージ: data, research, ai, ...（__all__ に定義）

  - 設定 / 環境変数管理 (kabusys.config)
    - .env ファイルの自動読み込み実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込みの優先順位: OS 環境変数 > .env.local > .env
    - 環境変数の自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント等に対応。
    - 読み込み時の上書き制御 (override/protected) に対応、OS 環境変数を保護。
    - Settings クラスを提供（settings インスタンスで利用）。
      - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite）/監視 PID・閾値など多数のプロパティを提供。
      - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）。
      - 必須環境変数未設定時は ValueError を発生させる _require を実装。

  - AI モジュール (kabusys.ai)
    - ニュース NLP スコアリング (kabusys.ai.news_nlp)
      - raw_news / news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）に送信してセンチメントを算出。
      - バッチ送信（最大 20 銘柄/チャンク）、記事数・文字数トリム (最大記事数・最大文字数)。
      - JSON Mode を想定したレスポンスパースと堅牢なバリデーション（余計な前後テキストの復元処理を含む）。
      - RateLimit/接続エラー/タイムアウト/5xx に対する指数バックオフによるリトライ実装。
      - スコアは ±1.0 にクリップ。部分失敗時に既存データを守るため、書き込みは対象コードのみ削除→挿入。
      - テスト容易性: OpenAI 呼び出し箇所を差し替え可能（unittest.mock.patch でモック化可能）。
      - 時間ウィンドウ計算（JST基準 → UTC 変換）: calc_news_window を提供。

    - 市場レジーム判定 (kabusys.ai.regime_detector)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' 判定。
      - prices_daily と raw_news を用い、ma200_ratio 計算、マクロ記事抽出、OpenAI 評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
      - API エラーやパース失敗時はフォールバック（macro_sentiment = 0.0）して継続するフェイルセーフ設計。
      - OpenAI 呼び出しは専用のラッパーを使用し、モジュール間で内部関数を共有しない設計。

  - データプラットフォーム (kabusys.data)
    - マーケットカレンダー管理 (calendar_management)
      - market_calendar テーブルを基に営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
      - DB にデータがない場合は曜日ベースのフォールバック（土日を非営業日とする）。
      - 夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants API から差分取得して保存、バックフィル日数を考慮）。
      - 安全策: 最大探索日数・健全性チェックの導入（過度に将来の日付がある場合はスキップ）。

    - ETL パイプライン (pipeline, etl)
      - ETLResult データクラスを提供（取得/保存件数、品質問題、エラーの集約）。
      - 差分更新・バックフィル・品質チェックなどの設計方針に基づく骨格の実装。
      - jquants_client（外部モジュール）との連携を想定した記述とエラーハンドリング。

  - 研究 / ファクター群 (kabusys.research)
    - factor_research: ファクター計算（モメンタム / ボラティリティ / バリュー / 流動性）を実装。
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None を返す）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率（データ不足時は None）。
      - calc_value: raw_financials と prices_daily を用いた PER, ROE 計算（最新財務データの取得ロジックを含む）。
      - DuckDB を用いた SQL + Python 実装で外部 API へのアクセスは行わない設計。
    - feature_exploration: 特徴量探索・評価用機能を実装。
      - calc_forward_returns: 指定ホライズンの将来リターン（horizons の検証を含む）。
      - calc_ic: スピアマンランク相関による IC 計算（必要件数未満は None）。
      - rank: 同順位は平均ランクにするランク化ユーティリティ。
      - factor_summary: 各カラムの count/mean/std/min/max/median を計算する統計サマリー。

Other notable design & quality points
- ルックアヘッドバイアス防止: internal ロジックで datetime.today() / date.today() を直接参照しない設計（target_date を必須引数として受ける）。
- DB 書き込みは冪等性を意識（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の使用）。
- エラー時のフェイルセーフ: API 失敗やパースエラーはログ出力してデフォルト値にフォールバックし、処理継続を優先。
- テスト容易性: OpenAI 呼び出しの差し替えポイントや api_key 引数の注入によりユニットテストが可能。
- DuckDB を主要な分析 DB として想定（SQL を多用）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- Settings の必須値が未設定の場合は明示的に ValueError を発生させることで安全性を確保。
- 環境変数の自動ロードは明示的フラグで無効化可能（テストやコンテナ運用時の安全対策）。

Notes / Limitations
- OpenAI モデルと SDK のバージョン依存性が存在（モデル名は gpt-4o-mini を指定）。
- DuckDB のバージョン差異（executemany の空リスト挙動など）を考慮した実装が行われている。
- 実行環境では各種必須環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）の設定が必要。

Contributors
- 初期実装（単一著者想定）により作成。

---