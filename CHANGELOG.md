# CHANGELOG

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

リリース方針:
- バージョン番号は semver を意識して管理します（現在初版: 0.1.0）。
- 各項目は可能な限り変更の意図・影響・設計方針を明記します。

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買／データ基盤のコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期公開。パブリック API を整備し、data / research / ai / monitoring / execution 等のサブモジュールを想定した構成を用意。
  - パッケージバージョン: `0.1.0`

- 環境設定・設定管理（kabusys.config）
  - .env ファイルおよび環境変数の読み込み機能を実装。プロジェクトルート（.git または pyproject.toml）を基準に .env を自動ロードする仕組みを提供。
  - .env パーサー（_parse_env_line）を実装。以下をサポート・考慮:
    - 空行 / コメント行（#）の無視
    - export KEY=val 形式の対応
    - シングル/ダブルクォートの文字列、バックスラッシュエスケープ対応
    - クォートなしの場合のインラインコメント判定（直前がスペース/タブの # をコメントとみなす）
  - 自動ロードの無効化環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - Settings クラスを実装し、以下の設定プロパティを提供:
    - J-Quants / kabuステーション / LINE API 関連（トークン・パス等）
    - DB パス（duckdb / sqlite）
    - 監視設定（PID ファイル / kill flag / しきい値）
    - システム環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジック
  - 必須環境変数を要求する `_require` 実装（未設定時は ValueError を送出）

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を使った銘柄ごとのニュース集約・OpenAI（gpt-4o-mini）によるバッチセンチメント評価機能を実装。
  - 時間ウィンドウ: JST 前日 15:00 ～ 当日 08:30 を想定し、UTC に変換して DB と比較する calc_news_window 実装。
  - バッチ処理（1回あたり最大 20 銘柄）および銘柄ごとの記事トリム（最大記事数・最大文字数）に対応。
  - OpenAI への再試行（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで実装。
  - JSON Mode による厳密な JSON レスポンスを期待しつつ、パース時に前後余計テキストが混入したケースの復元ロジックを実装。
  - レスポンス検証ルール（results リスト / code が要求された銘柄集合に含まれる / score が数値かつ有限）を実装。
  - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時にも既存スコアを保護）。
  - エラー発生時は例外を投げずに該当チャンクをスキップし、フェイルセーフに継続する設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（TOPIX 日経225連動型想定）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - マクロニュースはニュースタイトルからマクロキーワードでフィルタし、OpenAI（gpt-4o-mini）で JSON レスポンス形式により macro_sentiment を取得。
  - API 呼び出しのリトライ / バックオフ・フェイルセーフ（API 失敗時は macro_sentiment = 0.0）を実装。
  - DuckDB を用いたデータ取得（prices_daily / raw_news）と、market_regime テーブルへの冪等書き込みを実装（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
  - ルックアヘッドバイアス防止のため、内部処理で datetime.today() / date.today() を参照しない設計。

- 研究用ファクター計算（kabusys.research.*）
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - calc_value: PER（EPS が 0 または欠損なら None）、ROE（raw_financials から取得）
  - 実装方針: DuckDB の SQL と Python の組合せで実装し、prices_daily / raw_financials のみ参照して本番資金には影響しない。
  - research パッケージのエクスポート: calc_momentum, calc_volatility, calc_value と zscore_normalize（kabusys.data.stats から）および特徴量探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）。

- 特徴量探索・統計（kabusys.research.feature_exploration）
  - 将来リターン計算（calc_forward_returns）: 複数ホライズンを一度に取得する効率的 SQL 実装、引数検証（horizons は 1..252 の正整数）。
  - IC（Information Coefficient）計算（calc_ic）: Spearman（ランク相関）を実装。データ不足（有効レコード < 3）時は None を返す。
  - ランク変換ユーティリティ（rank）: 同順位は平均ランク（ties）で処理、丸め誤差軽減のため round(v, 12) を利用。
  - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。None 値を除外して計算。

- データ基盤（kabusys.data.*）
  - カレンダー管理（calendar_management）:
    - market_calendar テーブルを基に営業日判定（is_trading_day）、翌営業日/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 判定（is_sq_day）を実装。
    - DB にデータがない場合は曜日ベース（平日を営業日）でフォールバックする一貫した振る舞いを提供。
    - カレンダー夜間バッチ（calendar_update_job）: J-Quants クライアントから差分取得し、バックフィルと健全性チェック（未来日付の異常検出）を行って market_calendar を更新。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを公開し、ETL 実行結果（取得数・保存数・品質問題・エラー要約）を構造化して返す機能を実装。
    - 差分取得・バックフィル方針・品質チェック方針をコード・コメントとして明記。
  - data.etl モジュールで ETLResult を再エクスポート。

- DuckDB をメインの分析用組み込み DB として採用
  - 各モジュールは DuckDB 接続を引数に取り、SQL とウィンドウ関数等を活用して計算を実行する設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / 設計上の重要事項
- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定・ファクター計算はすべて target_date を明示的に受け取り、内部で date.today() を参照しません。
- フェイルセーフ性:
  - 外部 API（OpenAI / J-Quants）呼び出しはリトライとバックオフを実装し、最終的に失敗してもシステム全体を停止させずに部分的にスキップする挙動を採用しています。
- DB 書き込みは冪等性を重視:
  - ai_scores / market_regime / market_calendar などは既存レコードを削除して挿入する・ON CONFLICT を使用する等で上書き可能な設計。
- テスト容易性:
  - OpenAI 呼び出し等は内部関数（_call_openai_api）を経由しており、ユニットテスト時にモック差し替えが可能。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装拡充（発注ロジック・監視デーモン等）。
- パフォーマンス改善（大規模データを扱う際のクエリ最適化）。
- より多様なファクター・アルファ探索機能の追加。
- ドキュメント・例（Usage）の充実。

もしリリースノートに追加したい点（特に実際の変更履歴や貢献者情報など）があれば、該当情報を提供してください。必要に応じて日付や項目を更新します。