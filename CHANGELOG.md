CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングに従います。

フォーマットの規約:
- 変更はセクション（Added, Changed, Fixed, Deprecated, Removed, Security）に整理します。
- 日付は YYYY-MM-DD 形式で記載します。

Unreleased
----------

- 今後のリリースで検討している改善点や追加予定機能のメモ。
  - OpenAI モデルやレスポンス形式の切替を設定で柔軟化
  - ETL の並列処理・パフォーマンスチューニング
  - ai_scores / market_regime 等のテーブルスキーマ変更を伴う移行スクリプト
  - より厳密な品質チェックルール追加（quality モジュールの拡張）
  - テストカバレッジ拡大（DuckDB モック、OpenAI API モックの自動化）

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ基盤
  - 初期バージョンとして kabusys パッケージを追加。パッケージバージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定管理
  - 環境変数/ .env 管理モジュールを追加（kabusys.config）。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づき .env / .env.local 自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env パーサは export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、コメント処理に対応。
    - OS 環境変数を上書きしない保護機能（protected set）を実装。
    - 必須変数未設定時は _require で ValueError を投げる。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境・ログレベル判定）とバリデーション。

- データプラットフォーム
  - market カレンダー管理（kabusys.data.calendar_management）。
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装（jquants_client 経由で取得し冪等保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar 未取得時の曜日ベースフォールバック、DB値優先ロジック、最大探索日数制限を実装。
    - 健全性チェック（将来日付の異常検出）・バックフィルの実装。

  - ETL パイプライン（kabusys.data.pipeline / etl）。
    - 差分取得・idempotent 保存（jquants_client. save_* 想定）、品質チェックフレームワーク連携を想定した ETLResult データクラスを提供。
    - ETLResult は品質問題・エラー一覧・取得/保存件数を保持。has_errors / has_quality_errors / to_dict を実装。
    - テーブル存在確認や最大日付取得などのユーティリティを実装（DuckDB を前提）。

  - ETL の公開インターフェースとして ETLResult を再エクスポート（kabusys.data.etl）。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）。
    - raw_news / news_symbols を集約し、銘柄ごとに最大記事数・最大文字数でトリムして OpenAI（gpt-4o-mini）の JSON Mode へバッチ送信。
    - バッチサイズ: 20 銘柄、記事/銘柄上限、チャンク単位のリトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。
    - レスポンスのバリデーション（JSON 抽出、results リストの検証、コード照合、数値化、有限性チェック）を実装。
    - ai_scores テーブルへは取得できた銘柄のみを DELETE→INSERT（部分失敗時に既存データ保護）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。
    - calc_news_window を提供（JST 指定ウィンドウを UTC naive datetime に変換）。

  - 市場レジーム判定（kabusys.ai.regime_detector）。
    - ETF 1321（225連動）200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次でレジーム（bull / neutral / bear）を判定。
    - prices_daily からの MA200 比率計算、raw_news からマクロキーワード抽出、OpenAI（gpt-4o-mini）を用いたセンチメント評価、スコア合成・クリップ、market_regime への冪等書込を実装。
    - API エラーやレスポンスパース失敗時は macro_sentiment=0.0（フェイルセーフ）で継続。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。

- Research（因子計算・特徴量探索）
  - factor_research モジュールを追加（kabusys.research.factor_research）。
    - モメンタム（1m/3m/6m）、MA200 乖離、ボラティリティ（20日 ATR）、流動性（20日平均出来高・出来高比）、Value（PER・ROE の算出）を実装。
    - DuckDB 上の SQL（ウィンドウ関数）で高効率に計算する設計。データ不足時は None を返す。
    - 関数: calc_momentum / calc_volatility / calc_value。

  - feature_exploration モジュールを追加（kabusys.research.feature_exploration）。
    - 将来リターン計算（calc_forward_returns）を実装（デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算（Spearman ランク相関）を実装（calc_ic）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を実装。

- その他
  - research パッケージのエクスポート統一（calc_*、zscore_normalize 等の再エクスポート）。
  - 設計方針として「ルックアヘッドバイアス防止」の徹底（datetime.today()/date.today() を直接参照せず target_date を明示的に受け取る実装を採用）。

Changed
- 初期リリースのため該当なし（新規追加中心）。

Fixed
- フェイルセーフ設計の導入（OpenAI 呼び出し失敗時に例外を投げず中立値で継続する箇所を多数実装）。
- DuckDB の executemany の制約（空リスト不可）に配慮した条件付き実行を実装（ai_scores 書き込み等）。

Security
- OpenAI / J-Quants / kabu station 等の API キーは環境変数経由で扱い、未設定時には明示的な ValueError を発生させる（安全なデフォルトは与えない）。
- .env ファイルの読み込みはプロジェクトルートを探して自動的に行うが、環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Deprecated
- なし（初期リリース）。

Removed
- なし（初期リリース）。

Notes / 実装上の重要ポイント
- OpenAI 呼び出しは gpt-4o-mini / JSON Mode を前提に設計。レスポンスが完全な JSON でないケースに備えて前後の {} 抽出を試行する耐性処理を導入。
- API リトライは指数バックオフを採用し、429・ネットワーク断・タイムアウト・5xx をリトライ対象とする。一方で 4xx（クライアントエラー）等はリトライしない方針の箇所がある。
- DB 書き込みは冪等化（DELETE→INSERT、ON CONFLICT 想定）や BEGIN/COMMIT/ROLLBACK の明示的制御で安全化。ROLLBACK 失敗は警告ログを出力。
- 時間帯・ウィンドウ計算は JST / UTC の取り扱いに注意（calc_news_window は JST のウィンドウを UTC naive datetime に変換する実装）。
- 各モジュールはテスト容易性を考慮し、OpenAI 呼び出し箇所の差し替えや API キー注入を可能にしている。

作者注
- 本 CHANGELOG はコード内容から機能や振る舞いを推測して作成しています。実際のリリースノートは運用方針やリリース日付に合わせて調整してください。