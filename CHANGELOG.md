# CHANGELOG

すべての注目に値する変更は、このファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

最新更新日: 2026-04-09

## [Unreleased]

（現時点では未リリースの変更はありません）

---

## [0.1.0] - 2026-04-09

初版リリース。日本株自動売買システム「KabuSys」のベース機能を実装しました。主な追加点と設計上の方針を以下にまとめます。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py: パッケージ名、バージョン (0.1.0) と公開モジュール一覧（data, strategy, execution, monitoring）の定義。

- 設定・環境変数管理
  - src/kabusys/config.py:
    - .env ファイル/環境変数の自動読み込み機能（プロジェクトルートは .git / pyproject.toml で検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env のパースは export KEY=val 形式、クォート内のエスケープ、インラインコメント処理等に対応。
    - 環境変数必須チェック用の _require() と Settings クラスを提供。
    - 各種設定プロパティ:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知連携用）
      - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - Paper Trading の挙動設定（PAPER_FILL_MODE）と検証（有効値: instant/partial/never/reject）
      - 監視用ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）と監視閾値（CPU/MEM/DISK）
      - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL のバリデーション
      - is_live / is_paper / is_dev のユーティリティプロパティ

- データプラットフォーム（DuckDB ベース ETL / カレンダー）
  - src/kabusys/data/pipeline.py:
    - ETL パイプライン設計に準拠した ETLResult データクラス（取得件数、保存件数、品質問題、エラー集約、ユーティリティメソッド to_dict）。
    - 差分更新・バックフィル・品質チェックの方針が明文化。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult の再エクスポート（公開インターフェース）。
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar）と夜間更新ジョブ calendar_update_job。
    - カレンダー有無に応じたフォールバック（登録済み日は DB 値優先、未登録日は曜日ベース判定）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日ユーティリティを実装。
    - 最大探索範囲の上限 (_MAX_SEARCH_DAYS) と健全性チェック・バックフィル戦略を導入。
    - jquants_client を通じた取得・保存処理（差分取得・冪等保存を想定）。

- AI（ニュース NLP / 市場レジーム判定）
  - src/kabusys/ai/news_nlp.py:
    - raw_news と news_symbols を用いた銘柄別ニュース集約と OpenAI（gpt-4o-mini）を用いたセンチメントスコア算出機能 score_news。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で実装。
    - バッチ処理（1回あたり最大 _BATCH_SIZE=20 銘柄）、1銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を導入。
    - OpenAI 呼び出しの再試行（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフ、レスポンスのバリデーション（JSON 抽出、results 構造、コード検証、数値検証）を実装。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを保護するため DELETE → INSERT で対象コードのみ更新（DuckDB の互換性考慮）。
    - テスト容易性のため _call_openai_api の差し替えを想定。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio の計算（_calc_ma200_ratio）、マクロ記事抽出（_fetch_macro_news）、LLM 呼び出し（_score_macro）を含むフロー。
    - OpenAI API の例外種別別扱い（リトライ条件、5xx 判定等）や全リトライ失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 設計方針としてルックアヘッドバイアス回避のため内部で date.today() を参照せず、データ参照は target_date 未満の排他条件を守る。

- 研究（Research）ユーティリティ
  - src/kabusys/research/factor_research.py:
    - ファクター計算 (Momentum / Volatility / Value / Liquidity) を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None を返す）
      - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（ウィンドウデータ不足は None）
      - calc_value: per / roe（raw_financials の最新レコードを参照）
    - DuckDB でのウィンドウ関数を活用した実装と、営業日スキャンレンジのバッファ戦略。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 複数ホライズンの将来リターンをまとめて取得（ホライズン検証あり）。
    - calc_ic: factor と forward のランク相関（Spearman ρ）を計算し、レコード数不足時は None。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
  - src/kabusys/research/__init__.py: 研究用 API の公開（zscore_normalize 再エクスポート等）。

- その他
  - DuckDB を主要なローカル分析ストアとして利用する設計。
  - OpenAI 呼び出しは gpt-4o-mini を前提に JSON mode（response_format={"type":"json_object"}）での利用を想定。
  - ログ出力と WARN/INFO レベルでの挙動説明やフェイルセーフの明文化。
  - テスト/デバッグを容易にする設計（API 呼び出しのモック差し替えポイントの明示など）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止:
  - 全てのデータ処理関数は内部で datetime.today() / date.today() を参照せず、呼び出し側から target_date を受け取る設計。
  - DB クエリは target_date 未満（排他）などの条件により未来データ参照を防止。
- 冪等性:
  - DB への保存は可能な限り冪等（DELETE → INSERT / ON CONFLICT）を想定し、部分失敗が全体を破壊しない設計。
- フェイルセーフ:
  - 外部 API（OpenAI, J-Quants 等）の一時障害時は再試行やフォールバック（ゼロスコア等）で処理を継続し、致命的障害の抑制を優先。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数は差し替え可能（モック）となっており、単体テストが書きやすい構造。

---

今後の予定（例）
- strategy / execution / monitoring の具体実装（現行はパッケージ公開名のみ定義）。
- 更なる品質検査ロジック（quality モジュールの拡充）。
- CI/ユニットテスト・例示的サンプルデータとドキュメントの追加。

もし CHANGELOG に追記してほしい項目（例えば特定ファイルの細かな変更点やリリース日修正など）があれば指示ください。