# CHANGELOG

すべての変更は Keep a Changelog の仕様に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

（現時点のブランチに未リリースの変更はありません）

## [0.1.0] - 2026-03-29

### Added
- 初回リリース。日本株自動売買システム "KabuSys" のコアライブラリを追加。
  - パッケージ公開メタ:
    - src/kabusys/__init__.py: パッケージバージョン (0.1.0) と公開サブパッケージ指定。
  - 設定・環境変数管理:
    - src/kabusys/config.py:
      - .env/.env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml で探索）。
      - export KEY=val 形式やクォート・エスケープ、インラインコメントの扱いに対応するパーサ実装。
      - OS 環境変数を保護する仕組み（.env.local は既存 OS 環境変数を上書きしない）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
      - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル 等のプロパティとバリデーション。
      - _require による必須環境変数チェック（未設定時は ValueError を送出）。
  - AI（NLP）モジュール:
    - src/kabusys/ai/news_nlp.py:
      - raw_news / news_symbols から対象ウィンドウ（前日15:00 JST 〜 当日08:30 JST）を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini / JSON Mode）へバッチ送信してセンチメントスコアを計算。
      - チャンクバッチ（デフォルト最大20銘柄）・記事数／文字数トリム（最大記事数/文字数制限）を実装。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、コード照合、数値チェック、スコア ±1.0 クリップ）。
      - DuckDB へ冪等的に（DELETE → INSERT）ai_scores を書き込むロジック。部分失敗時に他コードの既存スコアを保護する挙動。
      - API キー未設定時は ValueError を送出。
    - src/kabusys/ai/regime_detector.py:
      - ETF 1321（日経225連動型）の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み付け（70% / 30%）して日次の市場レジーム（bull/neutral/bear）を判定。
      - ma200 の算出（target_date 未満のデータのみ使用）・マクロキーワードでの raw_news 抽出。
      - OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得、API エラー時はフェイルセーフとして 0.0 を採用。
      - レジームスコア合成と閾値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
      - LLM 呼び出しは別実装でモジュール結合を避け、テスト時に差し替え可能な設計。
  - データプラットフォーム（Data）:
    - src/kabusys/data/calendar_management.py:
      - market_calendar を起点とした営業日判定ユーティリティ群: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
      - market_calendar が未取得の場合は曜日ベース（週末を除く）でフォールバックする動作。
      - next/prev_trading_day での最大探索範囲制限（_MAX_SEARCH_DAYS）や健全性チェック。
      - calendar_update_job: J-Quants クライアント経由で差分取得し market_calendar を冪等更新（バックフィル・健全性チェック含む）。
    - src/kabusys/data/pipeline.py:
      - ETL パイプライン基盤（差分取得・保存・品質チェック方針の実装方針をコードに反映）。
      - ETLResult dataclass（target_date / fetched/saved counts / quality issues / errors）を実装。to_dict によるシリアライズ。
      - DuckDB 上のテーブル存在チェックや最大日付取得ユーティリティを実装。
    - src/kabusys/data/etl.py:
      - ETLResult の再エクスポートを提供。
  - リサーチ（Research）:
    - src/kabusys/research/factor_research.py:
      - ファクター計算群を SQL（DuckDB）で実装:
        - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
        - calc_volatility: 20 日 ATR（atr_20/atr_pct）、20 日平均売買代金、出来高比率。
        - calc_value: raw_financials から最新の EPS/ROE を取得して PER/ROE を計算（EPS が 0/欠損の際は None）。
      - 設計上、prices_daily / raw_financials のみ参照し外部 API 呼び出しは行わない。
    - src/kabusys/research/feature_exploration.py:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD により一括取得。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算、データ不足時は None を返す。
      - rank: 同順位は平均ランクとするランク化ユーティリティ（浮動小数点丸め対策あり）。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
    - src/kabusys/research/__init__.py:
      - 主要関数の再エクスポート（calc_momentum/calc_value/calc_volatility/zscore_normalize/calc_forward_returns/calc_ic/factor_summary/rank）。
  - パッケージインターフェース:
    - ai/__init__.py, research/__init__.py, data/etl のエクスポート整理により主要 API を簡単にインポート可能に。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- .env 自動読み込み時に OS 環境変数を保護（既存の環境変数を上書きしない設計）。
- 必須のシークレット（OpenAI / Slack / Kabu API 等）は Settings のプロパティで明示的にチェックし、不足時は例外を返す。

### Notes / Design decisions
- ルックアヘッドバイアス防止: 各モジュール（news_nlp, regime_detector, research 等）は datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計。
- LLM や外部 API 呼び出しは堅牢に設計（リトライ、フェイルセーフ 0.0、ログ出力）されており、API 失敗で処理全体が即座に停止しないようになっている。
- DuckDB を前提とした SQL 実装。使用するテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）のスキーマ依存あり。
- テスト容易性: OpenAI 呼び出し部分はモジュール内プライベート関数を差し替え可能にしてある（unittest.mock.patch 等で置換可能）。

### Breaking Changes
- 初回リリースのため該当なし。

---

今後のリリースでは、モジュールの追加（execution/monitoring）や API クライアント実装（kabu / jquants の詳細実装）、ユニットテスト・型チェックの拡充、CLI / バッチジョブの提供などを予定しています。