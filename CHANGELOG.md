# Changelog

すべての注目すべき変更を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 変更はセマンティックバージョニングに従います。
- 日付はリリース日を示します。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-03

最初の公開リリース。日本株自動売買プラットフォームのコア機能を実装しました。主な構成要素は設定管理、データ ETL / カレンダー管理、AI ニュース NLP / 市場レジーム判定、リサーチ用ファクター計算・特徴量解析、および DuckDB を用いたデータアクセスユーティリティ群です。

### Added
- パッケージ基本情報
  - kabusys パッケージ初期化（src/kabusys/__init__.py）とバージョン定義（0.1.0）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS環境 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いに対応。
  - 既存 OS 環境変数を保護する protected set による上書き制御。
  - 必須環境変数チェック用 _require() と Settings クラス:
    - J-Quants、kabuステーション、LINE、データベースパス、監視閾値、ログレベル、実行環境（development/paper_trading/live）などのプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL の値検証を実装。

- データプラットフォーム（src/kabusys/data/*）
  - calendar_management:
    - JPX カレンダー取得 / 夜間バッチ更新（calendar_update_job）。
    - 営業日判定と探索ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 未取得日の曜日ベースフォールバック（週末判定）。
    - 最大探索範囲・バックフィル・健全性チェックの実装。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の集約と to_dict() シリアライズ）。
    - ETL パイプライン方針（差分取得、バックフィル、品質チェックを反映する設計）。
    - _table_exists / _get_max_date 等の内部ユーティリティ。
  - jquants_client を介した差分取得 / 保存の想定（クライアントは別モジュールとして利用）。

- AI モジュール（src/kabusys/ai/*）
  - news_nlp:
    - ニュース記事を銘柄毎に集約し OpenAI（gpt-4o-mini）で一括スコアリング。
    - 時間ウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST を UTC で扱う calc_news_window）。
    - バッチ処理（_BATCH_SIZE=20）、1銘柄あたり記事数・文字数上限（トリム）を実装。
    - API 呼び出しの再試行（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）、レスポンス検証と JSON の頑健なパース。
    - スコア検証・クリップ（±1.0）、部分成功時の DB 書き込み保護（対象コードのみ DELETE → INSERT）。
    - テスト用フック: _call_openai_api を patch で差し替え可能。
  - regime_detector:
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - MA 計算は target_date 未満データのみを使用しルックアヘッドバイアスを排除。
    - マクロニュース抽出（マクロキーワードリスト）→ LLM（gpt-4o-mini）評価 → 合成スコア計算 → market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - テスト用フック: _call_openai_api を差し替え可能。

- Research（src/kabusys/research/*）
  - factor_research:
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200日移動平均乖離）を DuckDB SQL ウィンドウ関数で計算。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金・出来高比率を計算。
    - バリュー: raw_financials からの EPS / ROE を用いた PER / ROE 計算（最新レコード取得ロジック含む）。
    - 各関数は不足データ時に None を返す設計、(date, code) をキーとする辞書リストを返却。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns)：任意ホライズン（デフォルト [1,5,21]）のリターンを効率的に取得。
    - IC（Information Coefficient）計算（スピアマンのランク相関）: calc_ic。
    - ランキングユーティリティ（rank）: 同順位は平均ランクで処理（丸めにより ties 判定安定化）。
    - factor_summary: count/mean/std/min/max/median の統計要約。

- ログ & エラーハンドリング
  - 各モジュールで詳細な logger 出力を追加（INFO/DEBUG/WARNING/EXCEPTION を適宜使用）。
  - DB 書き込みでのトランザクション処理と ROLLBACK の保護処理を実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数ロード時に OS 環境を保護（protected set）し、.env による意図しない上書きを防止。
- OpenAI API キー未設定時は ValueError を投げ、明示的な設定を促す（誤動作の検出容易化）。

### Notes / Implementation details
- データベース: DuckDB を前提に SQL と Python の組合せで実装。期待されるテーブル:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
- ルックアヘッドバイアス対策:
  - score_news / score_regime 等のスコアリング関数は内部で datetime.today() を参照せず、外部から与えた target_date に基づいて厳密に過去データのみを参照する設計。
- API 呼び出し:
  - OpenAI の JSON mode（response_format={"type": "json_object"}）を利用。レスポンスの堅牢なパースと部分的リトライ戦略を導入。
- テスト支援:
  - _call_openai_api などの内部関数は unittest.mock.patch により差し替え可能にしているため、外部 API との統合を伴わない単体テストが容易。
- 互換性 / 制約:
  - DuckDB の executemany の挙動に配慮した実装（空リスト渡し回避）。
  - 一部 SQL 文は DuckDB のウィンドウ関数・ROW_NUMBER 等を利用しており、DuckDB 環境を前提とする。

---

今後の予定（例）
- ai モジュールの追加検証・モデル選択の拡張（別モデルや非同期実行）。
- ETL の実行制御（スケジューラ連携、詳細な品質レポート出力）。
- 監視・実行モジュール（execution / monitoring）と実際の発注連携ロジックの実装・安全性評価。

※ 上記 CHANGELOG はコードベースの内容を基に推測して作成しています。実際のコミット履歴やリリースノートに基づく追補・修正を推奨します。