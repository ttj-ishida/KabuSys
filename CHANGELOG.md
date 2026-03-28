# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- リリース日付はコードベースから推測した初版（バージョン番号はパッケージ定義 __version__ に基づく）を記載しています。
- 日付: 2026-03-28（コードの最新日を想定して設定）

## [Unreleased]
- （現在のコードベースでは未リリースの変更はありません）

## [0.1.0] - 2026-03-28
初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。

### Added
- パッケージ基盤
  - kabusys パッケージ（__version__ = 0.1.0）を追加。公開 API として data / research / ai 等のサブパッケージを提供。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - .env パーサはコメント行、export プレフィックス、シングル/ダブルクォートやバックスラッシュエスケープを考慮して安全にパース可能。
  - Settings クラスを提供し、J-Quants・kabuステーション・Slack・DBパス・実行環境（development/paper_trading/live）・ログレベル等の設定をプロパティとして取得可能。未設定の必須変数は明確なエラーを返す。
- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を JSON Mode で呼び出してニュースごとのセンチメント（ai_scores）を算出・書き込み。
    - バッチサイズ、1銘柄当たりの最大記事数・文字数制限、JSON レスポンスの厳密検証、スコアの ±1 クリップ等を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。失敗案件はスキップして他銘柄を保護するフェイルセーフ設計。
    - calc_news_window による JST ベースのニュース収集ウィンドウ計算を実装（ルックアヘッド防止のため datetime.today() を使わない設計）。
  - regime_detector.score_regime: ETF（1321）の200日移動平均乖離とマクロニュースの LLM センチメントを重み付け合成し、市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しに対するリトライ・フェイルセーフ、DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）での冪等性を確保。
    - マクロキーワードフィルタやレスポンス JSON 解析、API キー注入（引数または環境変数）をサポート。
  - OpenAI 呼び出しは各モジュール内で独立実装し、テスト時に差し替え可能（unittest.mock.patch でのモックを意識）。
- リサーチ / ファクター関連（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を DuckDB の SQL ウィンドウ関数で計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（真のレンジ）・相対 ATR（atr_pct）・20日平均売買代金・出来高比率を計算。高精度に NULL を扱うロジックを実装。
    - calc_value: raw_financials から直近財務を取得して PER（EPS が有効な場合）と ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが3未満の場合は None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を算出するユーティリティ。
  - 上記機能はすべて DuckDB 接続を受け取り、外部発注やランタイム副作用を発生させない設計。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。market_calendar テーブルが未取得時は曜日ベースのフォールバック（週末除外）を行い、一貫性を保つ。
    - calendar_update_job: J-Quants から JPX カレンダーを差分取得して market_calendar に冪等保存。バックフィル・健全性チェック（未来日付の異常検出）を実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl でも再エクスポート）。ETL 実行の取得件数・保存件数・品質問題・エラー一覧等を保持。品質問題は簡潔な辞書化（to_dict）で出力可能。
    - ETL パイプラインの設計方針（差分更新、backfill、品質チェックの集約、id_token 注入可能）を実装コメントとして明記。
  - jquants_client や quality モジュールへの参照を行い、外部 API 呼び出しによるデータ取得/保存フローに対応する設計。
- 共通実装
  - DuckDB を主要なストレージエンジンとして採用し、SQL ウィンドウ関数・LEAD/LAG/AVG/ROW_NUMBER 等を駆使して高性能な集計処理を実装。
  - ロギングを各モジュールに導入し、重要なイベント・警告・例外時のデバッグ情報を出力。
  - ルックアヘッドバイアス対策として datetime.today()/date.today() の直接参照を避け、外部から target_date を注入する設計を徹底。

### Changed
- （初回リリースのため過去バージョンからの変更はありません）

### Fixed
- （初回リリースのため過去バージョンからの修正はありません）
- 実装上のフェイルセーフやパース堅牢化（.env パース、JSON レスポンス復元処理、API エラー分類）により運用時の耐障害性を向上。

### Security
- OpenAI や外部 API のキーは Settings 経由で取得し、必須キー未設定時は明示的に ValueError を発生させることで秘密鍵の漏れや未設定を検出しやすくしている。
- .env の自動読み込みは環境変数で無効化可能（テスト環境向け）。

---

注記:
- ドキュメントはコードコメント・docstring から推測して作成しています。実際のリリースノートには実運用での重要な変更、セキュリティ修正、既知の破壊的変更などを実際の差分に基づいて追記してください。