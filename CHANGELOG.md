# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-09

初期リリース。日本株自動売買／リサーチプラットフォーム「KabuSys」の基本機能を実装しました。主な追加点は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージ情報（src/kabusys/__init__.py）およびバージョン番号 (0.1.0) を追加。

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env パーサ：コメント行、export 形式、シングル/ダブルクォート、エスケープ処理、インラインコメント処理へ対応。
  - .env ロード時の上書き制御（override）と OS 環境変数の保護（protected set）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数チェック関数 _require。
  - Settings クラスを提供（プロパティ経由で設定値取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須項目。
    - KABU_API_BASE_URL、LINE 関連トークン、データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）等のデフォルト値。
    - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）とデフォルト。
    - 監視用ファイルパス（PID/KILL flag）やリソース閾値（CPU/MEM/DISK）。
    - 環境モード（KABUSYS_ENV）の検証（development / paper_trading / live）および log_level 検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI モジュール（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメント分析を行い ai_scores テーブルへ保存する処理を実装。
    - ニュース収集ウィンドウ（JST: 前日15:00〜当日08:30）を calc_news_window で UTC naive datetime として計算。
    - バッチ処理（1リクエストあたり最大 20 銘柄）、1銘柄あたりの記事上限・文字数上限（記事数/文字数トリム）対応。
    - API 呼び出しに対する再試行（429 / ネットワーク / タイムアウト / 5xx の指数バックオフ）とフェイルセーフ（失敗時はスキップし続行）。
    - レスポンスの厳密なバリデーション（JSON パース、results フィールド、既知コードのみ採用、数値型検証、±1.0 でクリップ）。
    - 部分失敗に備えた冪等的 DB 書き込み（該当コードのみ DELETE→INSERT、DuckDB executemany の空リスト対応を考慮）。
    - 外部呼び出し点（_call_openai_api）をテスト差し替え可能に実装。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を決定。
    - マクロニュース抽出（マクロキーワードによるフィルタ）→ OpenAI によるセンチメント評価（gpt-4o-mini、JSON Mode）→ スコア合成→ market_regime テーブルへ冪等書き込み。
    - API 再試行・エラー時のフォールバック（macro_sentiment = 0.0）やロジックのフェイルセーフ設計。
    - ルックアヘッドバイアス防止（date 未満のデータのみ参照、datetime.today を参照しない）。

- Data（src/kabusys/data/*）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを使った営業日判定 utilities:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録ありの場合は DB 優先、未登録日は曜日ベースでフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に更新、バックフィルや健全性チェック（未来日付の異常検出）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー一覧などを保持）。
    - ETLResult を etl モジュール経由で再エクスポート。
    - 差分更新・バックフィル・品質チェック方針（品質問題は収集して継続）を実装方針として明示。

- Research（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS 0/欠損時は None）。
    - DuckDB SQL を用いた営業日ベースの計算。lookback のバッファ設計などを考慮。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を使用）。
    - calc_ic: ランク相関（Spearman の ρ）を計算するユーティリティ（None / 非有限値の除外、最小レコードチェック）。
    - rank: 同順位は平均ランクを採用する実装（丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。

- その他
  - src/kabusys/ai/__init__.py, src/kabusys/research/__init__.py などで公開 API を整備。
  - OpenAI クライアント呼び出しは gpt-4o-mini をデフォルトモデルとして使用する設計。

### Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で提供する必要があります。未設定時は ValueError を送出することで誤動作を防止します。
- 環境変数の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。重要な OS 環境変数は自動読み込み時に保護されます（.env の上書きを抑止）。

### Notes / Migration
- デフォルトのデータベースパス:
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可能）
  - Monitoring SQLite: data/monitoring.db（SQLITE_PATH）
  - Paper trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- PAPER_FILL_MODE の許容値は "instant" / "partial" / "never" / "reject"。不正な値は例外となります。
- AI 機能（score_news, score_regime）は OPENAI_API_KEY が必要です。
- DuckDB を前提に SQL 実装しているため、DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が未整備だと関数は動作しません。
- 全ての時刻処理はルックアヘッドバイアスを防ぐ実装方針（datetime.today 等を直接参照しない）になっています。研究やバッチ処理の再現性を優先しています。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

---

開発/運用者向けの追加情報や既知の制約が必要であれば、目的別（AI/ETL/Research/Data/Settings）に詳しいリリースノートを追記できます。必要ならお知らせください。