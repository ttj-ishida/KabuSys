# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトの最初の公開バージョンを以下に示します。

## [0.1.0] - 2026-04-04

### Added
- パッケージ初期リリース。
  - パッケージメタ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
    - パッケージの公開サブモジュールとして data/strategy/execution/monitoring を __all__ に定義（実装は一部モジュールに依存）。

- 環境設定管理:
  - src/kabusys/config.py
    - .env ファイル（.env / .env.local）またはOS環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索して行う（CWD に依存しない）。
    - .env の行パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 環境変数を保護する protected 機能（OS 環境変数の上書き回避）。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DBパス / 監視閾値 / システム環境（env, log_level）等のプロパティを定義。値検証（有効な env 値やログレベル）を行う。

- AI ニュース NLP:
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元に銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使ってセンチメント（-1.0〜1.0）を算出。
    - 処理ウィンドウ（JST 前日15:00〜当日08:30 を UTC に変換して使用）を calc_news_window で明示的に計算。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄当たり最大記事数・文字数でトリムする仕組みを実装。
    - リトライ/バックオフ（429、ネットワーク断、タイムアウト、5xx を対象）、API 応答のバリデーション（JSON 抽出、results リスト・型・既知コード・数値チェック）、スコアの ±1.0 クリップ。
    - DuckDB への書き込みは idempotent に DELETE → INSERT（部分失敗時に他レコードを保護）する実装。
    - テスト容易性を考慮し、OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。

  - src/kabusys/ai/__init__.py
    - score_news を公開。

- 市場レジーム判定:
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを回避。
    - マクロニュース取得は news_nlp.calc_news_window を利用し、該当タイトルを OpenAI（gpt-4o-mini）で評価。記事がない場合や API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成・クリップ処理および market_regime テーブルへの冪等的書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI API 呼び出し時のリトライ（指数バックオフ）や API エラーの扱いを実装。

- データプラットフォーム（Data）:
  - src/kabusys/data/calendar_management.py
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB 登録データ優先、未登録日は曜日ベース（週末除外）でフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API からの差分取得・保存（バックフィル・先読み・健全性チェックを含む）を実装。jquants_client との連携を想定。
    - 最大探索日数やバックフィル期間、健全性チェック等の安全措置を実装。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの土台と設計方針を実装（差分取得、保存、品質チェックの流れ）。jquants_client / quality モジュールとの連携を想定。
    - ETLResult dataclass を実装（取得数・保存数・品質問題・エラーの集計、to_dict メソッド等）。
    - テーブル存在チェックや最大日付取得などのユーティリティを実装。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

- リサーチ（研究用）モジュール:
  - src/kabusys/research/factor_research.py
    - ファクター計算関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離率）
      - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率
      - calc_value: PER（EPS に基づく）・ROE（raw_financials から最新値を取得）
    - DuckDB の SQL ウィンドウ関数を活用し、営業日ベースの窓や欠損値処理に配慮。
    - ルックアヘッドバイアスを防ぐ設計（target_date の扱いに注意）。

  - src/kabusys/research/feature_exploration.py
    - 研究向けユーティリティを実装:
      - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を使用）。
      - calc_ic: Spearman（ランク相関）に基づく IC 計算（rank 関数を内部実装）。
      - factor_summary: 各ファクターの count/mean/std/min/max/median を算出。
      - rank: 同順位は平均ランクを返すランク実装（丸めによる ties 判定対策あり）。
    - pandas 等に依存せず標準ライブラリのみで実装。

  - src/kabusys/research/__init__.py
    - 主要関数群（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Security
- （初版のため該当なし）

Notes / 設計上の重要点:
- ルックアヘッドバイアス防止のため、各種処理は date / target_date を明示的に受け取り、datetime.today()/date.today() を内部参照しない設計方針を一貫して採用しています。
- OpenAI API 呼び出しは JSON Mode を想定し、API レスポンスのパース失敗や一時エラー時にはフェイルセーフ（スコア 0.0 あるいは該当銘柄スキップ）で継続します。
- DuckDB への書き込みは冪等性を意識した実装（DELETE→INSERT、executemany の空リスト回避等）としています。
- テスト容易性のため、OpenAI 呼び出しや一部内部関数はモック差し替え可能に設計されています（ユニットテストでの patch を想定）。

もしリリースノートの粒度（モジュール別の詳細リストや既知の制限事項）をさらに細かくしてほしい場合は、その旨を教えてください。