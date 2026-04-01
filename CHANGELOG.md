# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトの初期リリースをコードベースから推測して作成しています。

フォーマット:
- Added: 新機能
- Changed: 変更点（後方互換性に影響する可能性のある変更）
- Fixed: 修正
- Removed / Security / Deprecated: 必要に応じて記載

---

## [Unreleased]
（なし）

---

## [0.1.0] - 2026-04-01

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能を実装。

### Added
- パッケージ初期化
  - kabusys パッケージおよび __version__ = "0.1.0" を導入。
  - 公開サブパッケージ: data, strategy, execution, monitoring をエクスポート。

- 環境設定 / config
  - .env/.env.local 自動読み込み機構（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env パーサの実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 上書き制御（override フラグ）と OS 環境変数保護（protected set）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリ設定を環境変数から取得:
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite） / 監視閾値 / ログレベル / 環境（development / paper_trading / live）等。
  - 必須環境変数未設定時は ValueError を発生させる _require 実装。
  - ログレベル・環境値のバリデーション。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news → OpenAI（gpt-4o-mini）でニュースのセンチメントを算出し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window 実装。
    - 記事の銘柄ごと集約、記事数・文字数トリム、チャンクバッチ（最大20銘柄）で API 呼び出し。
    - JSON Mode を想定したレスポンス検証（JSON 抽出、results 配列、code/score 検証、±1.0 クリップ）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフのリトライロジック。
    - DB への書込みは部分失敗に備え、対象コードのみ DELETE → INSERT（冪等保存）。
    - テスト容易性のため _call_openai_api を分離してモック可能に。
  - regime_detector:
    - ETF 1321（日経225連動ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成して日次の市場レジーム判定（bull/neutral/bear）を実装。
    - マクロニュースは raw_news からマクロキーワードで抽出（最大 20 件）。
    - OpenAI を用いたマクロセンチメント評価（JSON 出力期待）。API エラー時はフォールバック値 macro_sentiment=0.0。
    - レジームスコア合成、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアスを避ける設計（date 引数ベース、datetime.today() を参照しない）。

- Data モジュール（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar テーブルの読み書き、祝日・半日取引・SQ 判定）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の実装。
    - DB 未登録日は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得・バックフィル・健全性チェック・冪等保存を行う夜間バッチ処理。jquants_client 経由で fetch/save を呼び出す。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラーの集約、辞書化ユーティリティ）。
    - ETL パイプラインの骨格実装（差分取得・保存・品質チェックの方針とユーティリティ）。
    - DuckDB テーブル有無の判定ユーティリティ等を追加。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（欠損時は None）。
    - calc_volatility: 20 日 ATR、ATR 比、20 日平均売買代金、出来高比等の計算。true_range の NULL 伝播制御。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0 または欠損時は None）。
    - DuckDB のウィンドウ関数を活用して効率的に計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを連続 LEAD により計算。
    - calc_ic: スピアマンのランク相関（IC）を計算する実装。十分なデータがない場合は None を返す。
    - rank: 同順位は平均ランクを返すランク関数（丸め処理付き）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。

- 共通設計方針（全体）
  - DuckDB を主要な解析 DB として使用。
  - ルックアヘッドバイアスを避けるため、date/target_date を明示的に渡す設計。
  - 外部 API（OpenAI, J-Quants 等）の失敗に対するフェイルセーフ（デフォルト値・スキップ・再試行）を多用。
  - DB 書き込みは冪等性を意識（DELETE → INSERT、ON CONFLICT 方針等）。
  - テスト容易性のため外部呼び出し箇所を分離（プライベート関数をモック可能に）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Known limitations / 注意事項
- OpenAI API を用いる機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を要求し、未設定時は ValueError を送出する。
- 自動 .env ロードはプロジェクトルート検出に .git または pyproject.toml を使うため、配布後の環境や特殊なレイアウトでは手動で環境変数を設定する必要がある。
- ETL / calendar_update_job などは jquants_client 実装に依存。テスト時はクライアントの差し替えが必要。
- DuckDB の executemany に対する互換性（空リスト不可など）に配慮した実装を行っているが、将来の DuckDB バージョン差異に注意が必要。
- news_nlp / regime_detector の OpenAI 呼び出しは JSON Mode を前提としたレスポンス形式検証を行うが、LLM の挙動変更によりパース失敗が発生する可能性がある（その場合は該当チャンクをスキップして継続）。

### Security
- .env 読み込み時に OS 環境変数を保護する protected 機能を導入。override=False が既定で OS 環境を上書きしない。
- KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを明示的に無効化可能（テストや CI 用）。

---

今後の予定（想定）
- strategy / execution / monitoring サブパッケージの具体的な取引ロジック・注文実行・監視アラートの実装。
- テストカバレッジの拡充（ユニットテスト・統合テスト、API 呼び出しのモック）。
- ドキュメント（API 参照、運用手順、環境構築）整備。