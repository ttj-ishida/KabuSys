# Changelog

すべての注目すべき変更をここに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、以下の変更内容・設計方針は提供されたコードベースの実装内容から推測して記載しています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初期リリース。日本株向け自動売買・データ基盤・リサーチ・AI評価を扱うモジュール群を実装。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - パッケージ公開モジュール候補として data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数読み込み
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを実装（src/kabusys/config.py）。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）を実装し、配布後も CWD に依存しない自動 .env ロードを実現。
  - .env と .env.local の読み込み順・上書きルールを導入（OS 環境変数は protected として保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加（テスト向け）。
  - 必須環境変数取得時に未設定なら ValueError を出す _require 関数を提供。
  - 各種設定プロパティ（J-Quants、kabu API、Slack、DBパス、監視しきい値、環境・ログレベル判定）を実装。環境値の妥当性チェック（例: KABUSYS_ENV / LOG_LEVEL）を含む。

- AI（自然言語処理）機能
  - ニュースセンチメントスコアリング: score_news を実装（src/kabusys/ai/news_nlp.py）。
    - タイムウィンドウ（JST基準）集約ロジック（前日15:00〜当日08:30 JST を UTC に変換）を実装。
    - news_symbols 経由で銘柄ごとに記事を集約し、1チャンク最大20銘柄で OpenAI（gpt-4o-mini、JSON mode）に投げる設計。
    - レスポンスの厳密なバリデーション（JSON抽出・results 配列・code/score チェック）と ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ（最大試行回数制御）。
    - DuckDB への idempotent 書き込み（DELETE → INSERT）と、部分失敗時に既存スコアを保護する手順。
    - テスト用に _call_openai_api の差し替え（patch）を想定した設計。

  - 市場レジーム判定: score_regime を実装（src/kabusys/ai/regime_detector.py）。
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成してレジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を用いたデータ取得、OpenAI（gpt-4o-mini）呼び出し（JSON mode）を実装。
    - API 失敗時は macro_sentiment を 0.0 とするフェイルセーフ。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実行。
    - OpenAI API 呼び出しは独立関数化してモジュール結合を避ける設計。

- データ基盤（Data）
  - カレンダー管理モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定・次/前営業日取得・期間内営業日リスト取得（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - JPX カレンダーを J-Quants から差分取得して更新する夜間ジョブ calendar_update_job を実装（バックフィルや健全性チェック付き）。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）やバックフィル日数、先読み日数等の定数を定義。

  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（ETL の取得数・保存数・品質問題・エラー情報を集約）。
    - 差分取得、jquants_client を使った冪等保存、品質チェック（quality モジュールでの検出）は設計方針として明記。
    - data.etl で ETLResult を再エクスポートして公開インタフェースを提供。

- リサーチ（Research）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR、ATR 比率、平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 返却や結果形式（リスト of dict）を明確化。
    - DuckDB のウィンドウ関数を有効活用した実装。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）を実装。複数ホライズンの一括取得に対応。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装（同順位は平均ランク扱い）。
    - ランク関数（rank）と統計サマリー（factor_summary）を追加。
    - pandas 等に依存せず標準ライブラリのみで実装する方針。

- 内部設計上の注意点（ライブラリ運用面）
  - どの関数も datetime.today() / date.today() を直接参照しない設計（ルックアヘッドバイアス対策）。
  - DuckDB の挙動に合わせた executemany の空リスト回避など互換性配慮。
  - OpenAI 連携で JSON Mode を使い厳格な JSON レスポンスを期待する設計。
  - テスト容易性のため一部内部呼び出しを差し替え可能にしている（例: _call_openai_api の patch）。

### Changed
- （初期リリースのため「変更」は特になし。将来のリリースで差分を記載予定）

### Fixed
- （初期リリースのため「修正」は特になし）

### Security
- 環境変数の扱いにおいて OS 環境変数を .env の上書きから保護する仕組みを導入。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- OpenAI / Slack / Kabu API 等の機密情報は環境変数経由で取得し、未設定時は明示的にエラーを出す箇所を多数設けている（安全性と早期検出のため）。

### Notes / Public API の一覧（主な関数）
- kabusys.config.settings（Settings インスタンス）
- kabusys.ai.score_news(conn, target_date, api_key=None)
- kabusys.ai.score_regime(conn, target_date, api_key=None)
- kabusys.research.calc_momentum(conn, target_date)
- kabusys.research.calc_volatility(conn, target_date)
- kabusys.research.calc_value(conn, target_date)
- kabusys.research.calc_forward_returns(conn, target_date, horizons=None)
- kabusys.research.calc_ic(...)
- kabusys.research.factor_summary(...)
- kabusys.data.calendar_update_job(conn, lookahead_days=...)
- kabusys.data.is_trading_day / next_trading_day / prev_trading_day / get_trading_days

---

今後のリリースでは、実運用に向けた次のような項目が想定されます（参考）:
- strategy / execution / monitoring の具体実装（現在 __all__ に名称のみ存在）
- 単体テスト・統合テストの追加（OpenAI/外部 API のモック含む）
- ロギング・監視（Slack通知連携等）の強化
- パフォーマンス改善（大規模データセット向けの最適化）