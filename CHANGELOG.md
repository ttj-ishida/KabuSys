# Changelog

すべての注目すべき変更履歴はこのファイルに記録します。
このファイルは「Keep a Changelog」規約に準拠しています。

- フォーマット: YYYY-MM-DD
- バージョン番号はパッケージの __version__ に合わせています。

## [Unreleased]

---

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買プラットフォームの基礎機能を実装しています。
主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。パッケージ公開用の __all__ に data, strategy, execution, monitoring を設定。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env パーサ実装: export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - Settings クラスを導入し、J-Quants / kabu ステーション / LINE / DB / 監視 / システム関連の設定プロパティを提供。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL など）と必須キー取得時の明確なエラーメッセージを実装。

- データ層（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブル操作、営業日判定、next/prev/get_trading_days、SQ判定）。
    - カレンダー取得ジョブ calendar_update_job を実装（J-Quants クライアント経由の差分取得、バックフィル、健全性チェック、冪等保存）。
    - DB 登録がない日や NULL 値に対する曜日ベースのフォールバックを整備。
  - ETL / pipeline:
    - ETLResult データクラス（ETL 実行結果の集約、品質問題とエラーの集約・シリアライズ機能）。
    - 差分更新・バックフィル・品質チェック方針に準拠した ETL 基盤実装（jquants_client / quality モジュールを連携想定）。
  - etl モジュールで ETLResult を再エクスポート（公開インターフェース整備）。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - score_news を実装。raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini の JSON mode）へバッチ送信して銘柄別センチメント（ai_scores）を書き込み。
    - タイムウィンドウ計算（JST ベース → DB は UTC 前提）、バッチサイズ、記事数／文字数トリム、最大リトライ（指数バックオフ）などの実装。
    - レスポンス検証ロジックを実装（JSON 復元、results キー検証、既知コードのみ採用、スコア数値化・クリップ）。
    - 部分失敗時に既存スコアを保護するための部分的な DELETE → INSERT の冪等書き込み実装。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（内部 _call_openai_api を patch 可能）。
  - regime_detector:
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足時は中立扱い）、マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）とリトライ制御、スコア合成と閾値に基づくラベリング、market_regime への冪等書き込みを実装。
    - API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - テストのため OpenAI API キー注入や _call_openai_api の差し替えを想定。

- 研究モジュール（kabusys.research）
  - factor_research:
    - calc_momentum、calc_volatility、calc_value を実装。prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算。
    - MA200、ATR20、出来高・売買代金の移動平均、EPS に基づく PER 等を計算。データ不足時は None を返す挙動に統一。
  - feature_exploration:
    - calc_forward_returns（将来リターンの LEAD を用いた一括取得）、calc_ic（スピアマンランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median の統計量）を実装。
    - pandas 等に依存せず、標準ライブラリ + duckdb SQL で完結する設計。

- ロギング・堅牢性
  - 多くの箇所で詳細な logger.debug/info/warning/exception を配置し、障害時の診断を容易化。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターンを採用し、例外時には ROLLBACK を試みる実装。
  - ルックアヘッドバイアス防止のため、date.today()/datetime.today() をスコア計算ロジック内で直接参照しない設計方針を明記・徹底。

- テスト支援
  - OpenAI API 呼び出しや環境ロードの自動処理を、ユニットテストで差し替え・無効化できる設計（関数レベルでの差し替えや KABUSYS_DISABLE_AUTO_ENV_LOAD が利用可能）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を利用。キー管理は呼び出し側で行う前提（コード内にハードコーディングされたキーはなし）。

---

注記:
- 本 CHANGELOG は提供されたコードベースから仕様・実装意図を推測して作成しています。実際のリリースノートとして配布する際は、実際のリリース日や追加の変更点（ドキュメント、依存関係、マイグレーション手順など）を補足してください。