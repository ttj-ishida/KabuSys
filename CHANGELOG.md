# Changelog

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
日付はリポジトリ内のコード内容から推測した最終更新日を使用しています。

フォーマットの説明:
- Added: 新機能
- Changed: 既存機能の変更・改善
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当事項があれば記載

## [Unreleased]
- ドキュメントやテスト向けの軽微な改善・リファクタ予定（実装はコードから推測のため未確定）。

## [0.1.0] - 2026-03-31
初回公開リリース。日本株の自動売買・データプラットフォームのコア機能一式を実装。

### Added
- パッケージ基礎
  - kabusys パッケージの初期バージョンを追加。__version__ = "0.1.0" を定義。
  - パッケージ公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - .env パーサは export プレフィックス、クォート文字列、インラインコメント、バックスラッシュエスケープに対応。
    - 既存 OS 環境変数を保護する protected 機能と override フラグを実装。
  - Settings クラスを提供（J-Quants / kabu / Slack / データベースパス / 環境判定 / ログレベル等）。
    - 必須環境変数取得時に未設定なら ValueError を送出する _require を実装。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェックとユーティリティプロパティ（is_live/is_paper/is_dev）。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp)
    - raw_news / news_symbols を集約して各銘柄のニュースを LLM（gpt-4o-mini）へ送信しセンチメント（-1.0〜1.0）を算出・ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC へ変換）を採用。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - OpenAI 呼び出しの JSON mode を使用し、レスポンスバリデーション（構造・型・未知コード無視・数値チェック）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - テスト容易性のため _call_openai_api を patch 可能にしている。
    - DuckDB 0.10 の executemany 空リスト制約に対応するガード（空の場合は executemany を呼ばない）。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からキーワードフィルタで抽出（最大 20 件）。
    - OpenAI 呼び出しは専用実装で、失敗時は macro_sentiment=0 にフォールバック（フェイルセーフ）。
    - 計算結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。
    - Look-ahead バイアス防止のため date 未満のデータのみを参照し、datetime.today() を直接参照しない設計。

- データプラットフォーム (kabusys.data)
  - ETL インターフェース
    - pipeline.ETLResult を公開し、ETL の取得/保存件数・品質問題・エラー情報を集約する dataclass を提供。
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルの夜間バッチ更新（calendar_update_job）を実装。J-Quants API から差分取得して保存（バックフィル・健全性チェック含む）。
    - 営業日判定ユーティリティ: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB データが不足する場合の曜日ベースのフォールバックを実装。検索上限を設けて無限ループを防止。
  - ETL パイプライン基礎 (pipeline)
    - 差分更新・バックフィル・品質チェックの設計に基づくユーティリティ関数群を実装。
    - DuckDB 上での最大日付取得やテーブル存在チェックなどのヘルパーを提供。

- リサーチ関連 (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20 日 ATR（atr_20）・相対 ATR（atr_pct）・20 日平均売買代金（avg_turnover）・出来高比率（volume_ratio）。
    - Value: PER（EPS が有効な場合）・ROE（raw_financials から最新レポートを参照）。
    - DuckDB を用いた SQL ベース実装、データ不足時は None を返すロバスト設計。
  - 特徴量探索 (feature_exploration)
    - 将来リターン計算（calc_forward_returns）：複数ホライズンに対応、horizons の妥当性チェック。
    - IC 計算（calc_ic）：スピアマンの順位相関を手計算で算出（同順位は平均ランク）。
    - ランク変換ユーティリティ（rank）およびファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。

### Changed
- （初版のため主に設計決定の明示）
  - Look-ahead バイアス対策として、日付参照はすべて関数引数の target_date ベースで実行する設計を明記。
  - DuckDB 互換性や外部 API の障害に対するフォールバック処理を積極的に採用（例: OpenAI API 失敗時の安全デフォルト値）。

### Fixed
- N/A（初期リリース: 実装上の注意点やフォールバックを盛り込んで堅牢性を確保）

### Security
- OpenAI API キーや各種トークンを環境変数経由で扱う設計。Settings は未設定時に例外を投げて明示的な設定を促す。
- .env の読み込みはデフォルトで自動だが、KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト等で無効化可能。

---

注記（実装上の重要な設計方針）
- Look-ahead バイアス防止: datetime.today() / date.today() を不適切に参照しないよう設計（target_date を明示的に渡す）。
- DB 書き込みは冪等性を重視（DELETE→INSERT / ON CONFLICT など）し、部分失敗時に既存データを不必要に破壊しない。
- OpenAI 呼び出しは JSON mode を期待するが、実運用での余分なテキスト混入に備え JSON 抽出ロジックを実装。
- テスト容易性のため API 呼び出し部分（_call_openai_api など）を patch 可能にしている。

この CHANGELOG はコードベースの内容から推測して作成しています。将来的な正式リリースやコミット履歴に基づく正確な変更履歴が必要な場合は、実際の git 履歴を参照して更新してください。