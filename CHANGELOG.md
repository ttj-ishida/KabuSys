# Changelog

全ての（互換性のある）重大な変更をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-03-28

初回リリース。以下の主要機能および実装を含みます。

### Added
- パッケージ基礎
  - パッケージ名 kabusys を追加。バージョン __version__ = 0.1.0 を設定。
  - __all__ に data, strategy, execution, monitoring を公開（将来のモジュール構成を想定）。

- 環境設定（kabusys.config）
  - .env または .env.local から設定を自動読み込みする仕組みを実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - 一行パーサーの実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - .env.local を .env より優先して上書きする動作、OS 環境変数を保護する protected 機構。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / データベースパス / 環境（development/paper_trading/live）/ログレベル 等のプロパティを提供。
  - 必須環境変数取得時に未設定なら ValueError を送出する _require。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar に基づく営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB が未取得の際の曜日ベースフォールバック（週末除外）を実装。
    - JPX カレンダーを J-Quants から差分取得する夜間バッチ calendar_update_job を実装（バックフィル・健全性チェック付き）。
  - pipeline / ETL:
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー一覧を格納）。
    - ETL パイプライン用のユーティリティ（最終日チェック、差分取得・バックフィル方針、DuckDB 互換処理）を実装。
  - etl モジュールで ETLResult を再エクスポート。

- AI（kabusys.ai）
  - news_nlp モジュール:
    - raw_news / news_symbols を集約して銘柄別のニュースを作成し、OpenAI（gpt-4o-mini）の JSON モードでバッチ（最大 20 銘柄/リクエスト）センチメント解析を実行。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - 結果のバリデーション（JSON 抽出、results リスト、code/score 検証、スコアのクリップ）を実装。
    - ネットワーク断・429・タイムアウト・5xx に対する指数バックオフリトライを実装。失敗時は当該チャンクをスキップし他銘柄の処理を継続（フェイルセーフ）。
    - DuckDB への書き込みは idempotent に DELETE → INSERT を行い、部分失敗時に既存スコアを保護（コードを絞って削除）。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - マクロ記事抽出（キーワードベース）、OpenAI 呼び出し、スコア合成、冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 失敗やパース失敗時は macro_sentiment を 0.0 にフォールバックして処理継続（堅牢性確保）。
  - OpenAI 呼び出しはテスト容易性を考慮して内部 _call_openai_api を抽象化（ユニットテストで差し替え可能）。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタムファクター（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリューファクター（PER, ROE）を DuckDB SQL ベースで実装。
    - データ不足時の None 戻しやロジックの堅牢性に配慮。
  - feature_exploration:
    - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリーを実装。
    - pandas 等外部依存を避け、標準ライブラリ＋DuckDB のみで実現。
  - 研究向けユーティリティ（zscore_normalize の re-export 等）。

### Changed
- （初回リリースにつき該当なし）

### Fixed / Robustness
- OpenAI の JSON mode でも余分なテキストが混入するケースに対して前後の {} を抽出して復元する処理を追加。
- DuckDB バインド互換性のため executemany における空リスト回避（条件分岐）を追加。
- DB 書き込み中の例外で ROLLBACK が失敗した場合の警告ログを追加（rollback 失敗を再送出前に警告）。

### Security
- 環境変数の取り扱いで OS 環境変数を保護する protected 機構を導入（.env による上書きを制御）。
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を使用。未設定時は明確にエラーを送出。

### Notes / Implementation decisions
- ルックアヘッドバイアス対策として datetime.today() / date.today() を多くの AI/研究関数内部で直接参照しない設計を採用。target_date を呼び出し元で渡す方針。
- OpenAI モデルは gpt-4o-mini を使用する想定。レスポンスの堅牢な検証とリトライ戦略を導入。
- DuckDB を主要なストレージに想定し、日付取り扱いや型変換処理（_to_date 等）を実装。
- J-Quants クライアント（jquants_client）は別モジュールとして想定され、calendar/pipeline 等で利用。

---

参照:
- 本 CHANGELOG はソースコード（src/kabusys 以下）の実装内容から推測して作成しています。実際のリリースノートはプロジェクトのリリースポリシーに従って調整してください。