# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」の形式に準拠します。

全般的な方針:
- 重大な設計方針（ルックアヘッドバイアス回避、フェイルセーフ、冪等性など）は各モジュールで一貫して適用されています。
- DuckDB をデータストアとして利用する前提で実装されています。
- OpenAI（gpt-4o-mini）を用いた NLP 処理は JSON Mode を使った堅牢な入出力／リトライ設計です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29

Added
- パッケージ初期リリース。
- パッケージメタ:
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージトップで公開モジュールを定義（data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）:
  - .env / .env.local ファイルと OS 環境変数の自動ロード機構を実装。プロジェクトルート判定は `.git` または `pyproject.toml` を基準に行うため、CWD に依存しない。
  - .env の行パーサ `_parse_env_line` を実装し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなど多様な .env 文法に対応。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト向け）。
  - 既存 OS 環境変数を保護するための保護セット機能を実装（.env と .env.local の読み込み優先度制御）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを安全に取得可能（未設定時は明示的にエラー）。
  - `KABUSYS_ENV` と `LOG_LEVEL` の妥当性検証（許容値セット）を実装。
- AI（自然言語処理）機能:
  - kabusys.ai.news_nlp:
    - ニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを付与して `ai_scores` テーブルに書き込む `score_news` を実装。
    - JST ベースのニュース収集ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を正確に算出する `calc_news_window` を提供。
    - バッチ処理（1回あたり最大 20 銘柄）・記事数/文字数トリム（1銘柄あたり最大 10 件・3000 文字）・JSON Mode の応答バリデーション・スコアの ±1.0 クリップを装備。
    - API の一時エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフのリトライを実装。非リトライエラーや最終失敗はログに出しスキップして継続（フェイルセーフ設計）。
    - レスポンス JSON の前後雑多なテキスト混入に対する復元ロジックや未知コードの無視、数値変換チェックなど堅牢なバリデーションを実装。
    - テスト容易性のため、内部 OpenAI 呼び出し関数を patch で差し替え可能。
  - kabusys.ai.regime_detector:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、市場レジーム（bull / neutral / bear）を日次で判定する `score_regime` を実装。
    - prices_daily / raw_news からデータを取得、ma200_ratio 計算、マクロキーワードでフィルタした記事を LLM で評価してマクロセンチメントを算出、最終的なレジームスコアを合成して `market_regime` テーブルへ冪等書き込みを実施。
    - LLM 呼び出しは最大リトライ・バックオフを備え、API 失敗時はマクロセンチメントを 0.0 にフォールバックして処理継続（フェイルセーフ）。
    - ルックアヘッドバイアス防止のため、target_date 未満のデータのみ使用する設計。
- データ基盤（kabusys.data）:
  - calendar_management:
    - JPX カレンダー（market_calendar）に基づく営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得のケースでは曜日ベース（土日除外）でフォールバックするロジックを提供。
    - カレンダーの夜間差分更新処理 `calendar_update_job` を実装（J-Quants クライアント経由での差分取得・バックフィル・健全性チェック・冪等保存）。
    - 探索範囲の最大日数やバックフィル日数、健全性チェック等の安全策を実装。
  - pipeline / ETL:
    - ETL の公開インターフェース `ETLResult`（dataclass）を実装して再エクスポート（kabusys.data.etl）。
    - ETL 処理方針に基づき差分取得、保存（冪等）と品質チェックのための結果収集構造を提供。
    - DuckDB のテーブル存在確認・最大日付取得ユーティリティ等を実装。
- 研究用機能（kabusys.research）:
  - factor_research:
    - モメンタム（1M / 3M / 6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高変化率）、バリュー（PER / ROE）等を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 入出力は (date, code) をキーとする dict のリスト形式で統一。
    - データ不足時は None を返す挙動など堅牢性に配慮。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意のホライズン対応）、IC 計算（calc_ic: Spearman の ρ）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDB で完結する実装。
  - research パッケージの __all__ で主要関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- パッケージの公開 API 整備:
  - kabusys.ai.__init__ から score_news を再エクスポート。

Changed
- （初回リリースのため変更履歴はありません）

Fixed
- （初回リリースのため修正履歴はありません）

Removed
- （初回リリースのため削除履歴はありません）

Security
- OpenAI API キーは API 呼び出し引数または環境変数 `OPENAI_API_KEY` から解決。未設定時は明示的に ValueError を送出して安全に失敗する設計。

Notes / 設計上の重要点
- ルックアヘッドバイアス回避: 日付判定やウィンドウの設計で datetime.today()/date.today() を直接参照せず、target_date を明示的に渡す設計になっています（テストとバックテストの再現性確保）。
- 冪等保存: DB 書き込みは DELETE → INSERT のパターンやトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等性を担保。
- フェイルセーフ: 外部 API（OpenAI, J-Quants 等）失敗時は基本的に処理をスキップまたはデフォルト値にフォールバックし、例外は必要に応じて上位へ伝播する（DB 書き込み失敗等は例外伝播）。
- テスト支援: 内部 API 呼び出し点（OpenAI 呼び出し等）は patch 可能な関数として切り出し、ユニットテストで差し替え可能。

今後の予定（例示）
- strategy / execution / monitoring パッケージの実装と外部ブローカー連携（kabuステーション実行パス）の追加。
- ETL の orchestrator / スケジューリング周りの強化、品質チェックルールの追加。
- 追加のファクター・研究用可視化ユーティリティの提供。

---
本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートと差異がある場合は、必要に応じて差し替えてください。