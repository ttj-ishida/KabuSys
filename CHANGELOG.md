# Changelog

すべての注記は「Keep a Changelog」フォーマットに準拠しており、セマンティックバージョニングに従います。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-04-04

初期リリース — 日本株自動売買・データ基盤・リサーチ用ユーティリティの基本機能を提供します。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - モジュール公開設定（__all__）を定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート判定は __file__ を基準に .git / pyproject.toml を探索（CWD 非依存）。
  - .env のパースは以下に対応：
    - 空行・コメント（#）の無視
    - export KEY=val 形式の対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応
    - 行内コメント処理（クォート外、直前がスペース/タブの # をコメントとみなす）
  - .env の読み込み優先順位：OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 環境変数取得ヘルパー（_require）と Settings クラスを実装。J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と便宜プロパティ（is_live/is_paper/is_dev）を実装。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコア（-1.0〜1.0）を取得して ai_scores に保存する処理を実装。
    - 対象ウィンドウは JST 基準で「前日 15:00 ～ 当日 08:30」（DB 用に UTC 変換）。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数上限・文字数トリム）、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密なバリデーション（JSON 抽出・results 欄・既知コード検証・数値検証）とスコアクリップを実装。
    - DuckDB への書き込みは冪等処理（DELETE → INSERT）で、部分失敗時に他銘柄の既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出し関数は差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し market_regime テーブルに保存する処理を実装。
    - prices_daily から ma200_ratio を計算（target_date 未満のデータのみを使用しルックアヘッドを防止）。
    - raw_news からマクロキーワード（日本・米国等の金融ワード）でフィルタしたタイトルを取得し、OpenAI により macro_sentiment を取得（記事がない場合は LLM 呼び出しを行わず macro_sentiment=0.0）。
    - OpenAI 呼び出しはリトライ・バックオフを実装し、API 失敗時はフェイルセーフで 0.0 を使用。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。エラー時は ROLLBACK を試行。
    - 外部設計方針としてルックアヘッドバイアスを避ける実装（datetime.today() 等を参照しない）。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。J-Quants API から差分取得 → 保存（冪等）する流れに対応。
    - 営業日判定・次/前営業日取得・期間内営業日列挙・SQ日判定のユーティリティを実装。
    - DB に登録がない場合は曜日ベース（平日）でフォールバックする整合的な動作。
    - 最大探索範囲やバックフィル、健全性チェック等の安全機能を実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETL 実行結果を表す ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。
    - 差分更新、バックフィル、品質チェック（quality モジュール）等の設計方針に基づく処理基盤を実装（骨格）。DuckDB を前提としたテーブル存在チェック・最大日付取得ユーティリティ等を提供。
    - ETLResult は品質問題を辞書化して to_dict で出力可能。
  - jquants_client（参照/依存）：カレンダー取得・保存等を利用するためのクライアント参照を実装（モジュール読み込み点）。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装。
    - データ不足時は None を返す仕様、結果は (date, code) をキーにした辞書リストで返却。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns、任意 horizon 対応）、IC（Information Coefficient）計算（Spearman ρ）、ランク付けユーティリティ、ファクター統計サマリーを実装。
    - 外部ライブラリ非依存（標準ライブラリのみで実装）で DuckDB を用いる設計。
  - 研究用ユーティリティをパッケージレベルでエクスポート（zscore_normalize の再エクスポート等）。

### Changed
- （該当なし：初回リリースのため変更履歴はありません）

### Fixed
- （該当なし：初回リリースのため修正履歴はありません）

### Security
- .env 自動ロード時、既存の OS 環境変数を保護するため protected set を導入して .env/.env.local による上書きを制御。
- KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを実装（テスト等での環境汚染防止）。
- OpenAI API キー未設定の場合は明確な ValueError を送出し誤操作を防止。

### Notes / Design decisions
- ルックアヘッドバイアス防止: AI / リサーチ関連の各処理は datetime.today() や date.today() を直接参照せず、呼び出し側から target_date を与える設計。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）失敗時は部分的に継続する設計（スコアを 0 にフォールバック、該当チャンクはスキップ等）。
- DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 想定）で実装し、部分失敗時に既存データを守る工夫をしている。
- テスト容易性: OpenAI 呼び出し部分や環境ロードを差し替え可能にして単体テストが行いやすい設計。

---

初期リリース（0.1.0）は上述の機能をコアとして提供します。今後のリリースでは strategy / execution / monitoring に関する発注・モニタリング機能の詳細実装や、より強固な品質チェック、運用向けの CLI / docker 化、ドキュメント拡充を予定しています。