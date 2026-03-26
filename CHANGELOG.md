# CHANGELOG

すべての重要な変更点は Keep a Changelog の形式に従って記載します。  
本ファイルはコードベース（src/kabusys 以下）の内容から推測して作成した初期リリースの変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-26
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。

### Added
- パッケージ基盤
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - kabase の公開モジュール一覧を定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート探索: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
  - 高度な .env パーサ実装:
    - export KEY=val 形式サポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理を実装。
    - 無効行・コメント行をスキップ。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - OS 環境変数を保護する protected キーセットを利用した上書き制御（.env と .env.local の優先度処理）。
  - 設定ラッパー Settings を提供し、主要設定値をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / データベースパス / 環境（development/paper_trading/live）/ログレベル 等
    - 未設定の必須環境変数では ValueError を発生させる _require() を採用。
    - env/log_level のバリデーション実装。
    - is_live / is_paper / is_dev のユーティリティプロパティを追加。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）:
    - raw_news と news_symbols を集約して銘柄ごとの全文テキストを作成。
    - OpenAI (gpt-4o-mini) の JSON mode を使ってバッチ処理（最大 20 銘柄/チャンク）でセンチメントスコアを取得。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実施。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、results フォーマット検証、コード照合、数値性チェック）。
    - スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計。
    - テスト容易性のため _call_openai_api を差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を判定。
    - マクロニュース抽出はキーワードベース（複数キーワードリスト）で raw_news からタイトルを取得。
    - OpenAI 呼び出しは独立実装、リトライ・フェイルセーフ（API失敗時 macro_sentiment=0.0）を実装。
    - 計算結果を冪等に market_regime テーブルへ書き込む（トランザクション: BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止に配慮した SQL 条件（date < target_date 等）。

- データ基盤・ETL（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）:
    - market_calendar を用いた営業日判定ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得の場合は曜日ベース（平日）でのフォールバックを提供。
    - JPX カレンダー差分取得バッチ（calendar_update_job）を実装。J-Quants クライアント経由で差分を取得し冪等保存、バックフィルと健全性チェックを実施。
    - 最大探索範囲やバックフィル日数等の安全パラメータを導入。
  - ETL パイプライン（kabusys.data.pipeline）:
    - ETL 実行結果を表現する dataclass ETLResult を追加（フェッチ数・保存数・品質問題・エラー一覧を保持）。
    - 差分更新、IDempotent 保存（jquants_client の save_* を利用）、品質チェック（quality モジュール）を想定した設計。
    - テーブル存在チェックや最大日付取得等のユーティリティ実装。
  - ETL API の再エクスポート（kabusys.data.etl: ETLResult）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - Value: PER（EPS に基づき計算、EPS が 0 または欠損時は None）、ROE（raw_financials から取得）。
    - DuckDB SQL ウィンドウ関数を活用し、データ不足時の None 返却やログを出す設計。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns）: LEAD を用いて任意ホライズンの将来リターンを一度に取得。
    - IC（Information Coefficient）計算（calc_ic）: コードで結合し Spearman（ランク相関）を算出、3 銘柄未満は None。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。
    - 独自のランク関数（rank）を実装し、同順位は平均ランクに対応。
  - research パッケージの公開 API を整理（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- 初回リリースのため該当なし（新規追加のみ）。

### Fixed
- 初回リリースのため該当なし。

### Notes / Implementation details（設計上の重要ポイント）
- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定・リサーチ系関数は内部で現在日時を参照しない。target_date パラメータに基づく設計。
  - DB クエリは date < target_date や半開区間 [start, end) を活用して将来データの混入を禁止。
- OpenAI API 取り扱い:
  - JSON mode を前提とした厳格なレスポンスパースを実装。パース失敗時はフェイルセーフとしてスコア 0.0 または該当銘柄スキップ。
  - リトライは 429 / ネットワーク断 / タイムアウト / 5xx に限定。非再試行のエラーは即スキップ。
  - テスト容易性のため _call_openai_api をモジュール内で差し替え可能。
- DuckDB 側への書き込みは可能な限り冪等に（DELETE→INSERT、ON CONFLICT 想定）し、部分失敗時に既存データを保護する実装方針。
- .env パーサは一般的なシェル形式をかなり忠実に再現（クォート内エスケープ、export プレフィックス、インラインコメントの取り扱い）。
- 安全対策:
  - calendar_update_job 等で過度に未来の日付が検出された場合はスキップする健全性チェックを実装。
  - DuckDB の executemany 空リスト制約を回避するためのガード条件を追加。

---

注: 本 CHANGELOG は公開されているソースコードの構造・実装から推測して作成したものであり、実際のコミット履歴やリリースノートとは差異がある場合があります。必要であれば、各モジュールの docstring やログ記述を元にさらに詳細なセクション（例: Breaking Changes, Security fix 等）を追加します。